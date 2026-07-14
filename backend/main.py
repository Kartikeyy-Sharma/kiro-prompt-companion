from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
import json

from agent.classifier import classify_prompt
from agent.questioner import generate_questions
from config import OPENAI_API_KEY, REWRITER_MODEL, REWRITER_SYSTEM_PROMPT
from openai import OpenAI

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=OPENAI_API_KEY)


# ── Request models ────────────────────────────────────────────────────────────

class PromptRequest(BaseModel):
    prompt: str


class AnsweredOption(BaseModel):
    letter: str
    text: str


class AnsweredQuestion(BaseModel):
    id: int
    text: str
    chosen_letter: str
    chosen_text: str


class RewriteRequest(BaseModel):
    prompt: str
    answers: List[AnsweredQuestion]


# ── /classify ─────────────────────────────────────────────────────────────────

@app.post("/classify")
async def classify(request: PromptRequest):
    result = classify_prompt(request.prompt)
    return {
        "is_complex": result.is_complex,
        "reason": result.reason
    }


# ── /questioner ───────────────────────────────────────────────────────────────

@app.post("/questioner")
async def questioner(request: PromptRequest):
    questions = generate_questions(request.prompt)
    return {
        "questions": [
            {
                "id": q.id,
                "text": q.text,
                "options": [
                    {"letter": opt.letter, "text": opt.text}
                    for opt in q.options
                ]
            }
            for q in questions
        ]
    }


# ── /rewriter (SSE streaming) ─────────────────────────────────────────────────

def build_rewrite_context(prompt: str, answers: List[AnsweredQuestion]) -> str:
    """Build the user message sent to the rewriter LLM."""
    lines = [f"Original prompt: {prompt}", "", "User's answers:"]
    for a in answers:
        lines.append(f"  Q: {a.text}")
        lines.append(f"  A: {a.chosen_letter} — {a.chosen_text}")
        lines.append("")
    return "\n".join(lines)


def stream_rewrite(prompt: str, answers: List[AnsweredQuestion]):
    """
    Generator that yields SSE-formatted chunks from the OpenAI streaming API.
    Each chunk: data: {"chunk": "word "}\n\n
    Final chunk: data: {"done": true}\n\n
    Error:       data: {"error": "message"}\n\n
    """
    context = build_rewrite_context(prompt, answers)

    try:
        stream = client.chat.completions.create(
            model=REWRITER_MODEL,
            messages=[
                {"role": "system", "content": REWRITER_SYSTEM_PROMPT},
                {"role": "user",   "content": context}
            ],
            temperature=0.4,
            max_tokens=400,
            stream=True,   # ← key difference from the CLI version
        )

        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                # Encode each token as an SSE event
                payload = json.dumps({"chunk": delta.content})
                yield f"data: {payload}\n\n"

        # Signal completion to the frontend
        yield f"data: {json.dumps({'done': True})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@app.post("/rewriter")
async def rewriter(request: RewriteRequest):
    return StreamingResponse(
        stream_rewrite(request.prompt, request.answers),
        media_type="text/event-stream",
        headers={
            # Prevent any proxy/browser from buffering the SSE stream
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


# ── health check ──────────────────────────────────────────────────────────────

@app.get("/")
def home():
    return {"status": "running"}