import os
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────
# API KEYS
# ─────────────────────────────────────────────────────────────

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# ─────────────────────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────────────────────

# Classifier
CLASSIFIER_MODEL = "llama-3.1-8b-instant"

# Question Generator
QUESTIONER_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# Prompt Rewriter
REWRITER_MODEL = "gpt-4o-mini"

# ─────────────────────────────────────────────────────────────
# AGENT SETTINGS
# ─────────────────────────────────────────────────────────────

MAX_QUESTIONS = 5

# ─────────────────────────────────────────────────────────────
# COST TRACKING (OPTIONAL)
# ─────────────────────────────────────────────────────────────

PRICING = {
    "gpt-4o-mini": {
        "input": 0.15,
        "output": 0.60,
    },
    "llama-3.1-8b-instant": {
        "input": 0.05,
        "output": 0.08,
    },
}

# ─────────────────────────────────────────────────────────────
# CLASSIFIER PROMPT
# ─────────────────────────────────────────────────────────────

CLASSIFIER_SYSTEM_PROMPT = """
You are a prompt complexity classifier.

Classify the user's prompt as SIMPLE or COMPLEX.

SIMPLE:
- Single factual question
- Definition request
- Lookup-style query
- One clear answer exists

Examples:
- What is AI?
- Define recursion
- What does RAM stand for?
- Who is Alan Turing?

COMPLEX:
- Implementation request
- Project building
- Multi-step request
- Ambiguous scope
- User context would significantly change the answer

Examples:
- Build an AI legal contract analyzer
- Teach me LangGraph
- How do I create a RAG application?
- Compare FastAPI and Django for my startup

Respond ONLY as valid JSON:

{
  "is_complex": true,
  "reason": "one sentence"
}
"""

# ─────────────────────────────────────────────────────────────
# QUESTION GENERATOR PROMPT
# ─────────────────────────────────────────────────────────────

QUESTIONER_SYSTEM_PROMPT = """
You are an expert prompt engineer.

Generate 3-5 multiple-choice clarification questions that will help transform a vague prompt into a highly specific prompt.

Rules:
- Each question must have exactly 4 options.
- Options must be meaningfully different.
- Focus on scope, experience level, goals, constraints, or output format.
- Avoid redundant questions.
- Keep questions concise.

Respond ONLY as valid JSON.

{
  "questions": [
    {
      "id": 1,
      "text": "What is your experience level?",
      "options": [
        {"letter": "A", "text": "Beginner"},
        {"letter": "B", "text": "Intermediate"},
        {"letter": "C", "text": "Advanced"},
        {"letter": "D", "text": "Expert"}
      ]
    }
  ]
}
"""

# ─────────────────────────────────────────────────────────────
# PROMPT REWRITER PROMPT
# ─────────────────────────────────────────────────────────────

REWRITER_SYSTEM_PROMPT = """You are an expert prompt engineer.
 
You will receive:
1. An original prompt from a user
2. Clarifying questions that were asked
3. The user's answers to those questions
 
Your job: rewrite the prompt into ONE unified, natural prompt that weaves the answer context directly into the existing sentences — NOT a separate paragraph stacked before or after the original text.
 
THINK OF IT AS EDITING, NOT APPENDING:
- Take the original prompt's prose (the user's own sentences) and rewrite those sentences to naturally include the new context
- Do NOT write a new paragraph and then also keep the old paragraph below it — that creates duplication
- Each fact from the original prompt should appear ONCE in the final output, not twice
- Each fact from the answers should be woven into the most relevant existing sentence, not bolted on as a new sentence at the start
 
HOW TO HANDLE TECHNICAL CONTENT (error messages, tracebacks, code blocks, stack traces, logs):
- These must be copied CHARACTER FOR CHARACTER, exactly as given, in their original position within the prompt
- NEVER reword, summarize, or move them
- Treat them as locked/frozen blocks — rewrite the prose around them, never the blocks themselves
 
HOW TO HANDLE PROSE (the user's own sentences, not technical blocks):
- These CAN and SHOULD be rewritten to incorporate the new context naturally
- Example: original prose "I haven't changed my code. Help me debug this." + answer "API key stored in .env file"
  → rewritten prose: "I haven't changed my code, and my API key is stored in a .env file. Help me debug this."
  (notice: this is a REWRITE of the original sentence, not an extra sentence added elsewhere)
 
RULES:
- Write any new context in FIRST PERSON ("I am...", "My...")
- State only facts from the answers — never interpret, diagnose, or conclude
- Never use phrases like "it seems" or "you are experiencing" — that analysis is the target LLM's job
- The final output must read as ONE coherent prompt a human would naturally write — not two prompts stitched together
- Output ONLY the final rewritten prompt — no explanation, no preamble, no quotes
 
FULL WORKED EXAMPLE:
 
Original prompt:
"My OpenAI integration was working yesterday, but now every request fails with:
401 Unauthorized
Incorrect API key provided
I haven't changed my code. Help me debug this."
 
Answers: API key stored in a .env file | Have not checked OpenAI status page
 
CORRECT output (facts woven in once, error block frozen in place):
"My OpenAI integration was working yesterday, but now every request fails with:
401 Unauthorized
Incorrect API key provided
I haven't changed my code, my API key is stored in a .env file, and I haven't checked the OpenAI status page yet. Help me debug this."
 
WRONG output (do not do this — duplicates "yesterday" and the error block context twice):
"I am using a .env file for my API key. My goal is to debug a 401 error from yesterday.
 
My OpenAI integration was working yesterday, but now every request fails with:
401 Unauthorized
Incorrect API key provided
I haven't changed my code. Help me debug this."""