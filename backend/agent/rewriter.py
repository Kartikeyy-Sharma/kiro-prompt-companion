from openai import OpenAI
from config import OPENAI_API_KEY, REWRITER_MODEL, REWRITER_SYSTEM_PROMPT
from agent.models import AgentSession
from agent.metrics import metrics

client = OpenAI(api_key=OPENAI_API_KEY)


def build_context_block(session: AgentSession) -> str:
    lines = [f"Original prompt: {session.original_prompt}", "", "User's answers:"]
    for q in session.questions:
        chosen = next((opt for opt in q.options if opt.letter == q.chosen_letter), None)
        answer_text = chosen.text if chosen else q.chosen_letter
        lines.append(f"  Q: {q.text}")
        lines.append(f"  A: {q.chosen_letter} — {answer_text}")
        lines.append("")
    return "\n".join(lines)


def rewrite_prompt(session: AgentSession) -> str:
    context = build_context_block(session)
    try:
        with metrics.track("Rewriter", model=REWRITER_MODEL):
            response = client.chat.completions.create(
                model=REWRITER_MODEL,
                messages=[
                    {"role": "system", "content": REWRITER_SYSTEM_PROMPT},
                    {"role": "user",   "content": context}
                ],
                temperature=0.4,
                max_tokens=400,
            )
            metrics.record_usage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"\n  [Agent] Rewriter failed ({e}). Returning original prompt.\n")
        return session.original_prompt