import json
from groq import Groq

from config import (
    GROQ_API_KEY,
    QUESTIONER_MODEL,
    QUESTIONER_SYSTEM_PROMPT,
    MAX_QUESTIONS
)
from agent.models import Question, MCQOption
from agent.metrics import metrics

client = Groq(api_key=GROQ_API_KEY)


def generate_questions(prompt: str) -> list[Question]:
    try:
        with metrics.track("Questioner", model=QUESTIONER_MODEL):
            response = client.chat.completions.create(
                model=QUESTIONER_MODEL,
                messages=[
                    {"role": "system", "content": QUESTIONER_SYSTEM_PROMPT},
                    {"role": "user",   "content": f"Generate clarifying questions for: {prompt}"}
                ],
                temperature=0.3,
                max_tokens=600,
                response_format={"type": "json_object"},
            )
            metrics.record_usage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            )

        raw  = response.choices[0].message.content
        data = json.loads(raw)

        questions = []
        for q in data.get("questions", [])[:MAX_QUESTIONS]:
            options = [
                MCQOption(letter=opt["letter"], text=opt["text"])
                for opt in q.get("options", [])
            ]
            questions.append(Question(id=q["id"], text=q["text"], options=options))

        return questions

    except Exception as e:
        print(f"\n  [Agent] Couldn't generate questions ({e}). Proceeding without.\n")
        return []