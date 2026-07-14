import sys
from agent.models import AgentSession
from agent.classifier import classify_prompt
from agent.questioner import generate_questions
from agent.rewriter import rewrite_prompt
from agent.metrics import metrics

# Optional inline prompt: create `prompt_text.py` with a `PROMPT` variable
try:
    from prompt_text import PROMPT as INLINE_PROMPT
except Exception:
    INLINE_PROMPT = None

# ── Terminal styling (no external deps) ──────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
CYAN   = "\033[96m"
YELLOW = "\033[93m"
GREEN  = "\033[92m"
GRAY   = "\033[90m"
WHITE  = "\033[97m"

def c(color: str, text: str) -> str:
    return f"{color}{text}{RESET}"

def divider(char="─", width=60):
    print(c(GRAY, char * width))

def header():
    print()
    divider("━")
    print(c(BOLD + CYAN, "  ⬡  Prompt Agent"))
    print(c(DIM, "     Clarify → Improve → Send"))
    divider("━")
    print()


# ── Input helpers ─────────────────────────────────────────────────────────────
def get_prompt() -> str:
    print(c(WHITE, "  Enter your prompt:"))
    print(c(GRAY,  "  (Type and press Enter)"))
    print()
    try:
        prompt = input(c(CYAN, "  › ")).strip()
    except (KeyboardInterrupt, EOFError):
        print("\n\n  Bye.\n")
        sys.exit(0)
    return prompt


def ask_question(q) -> str:
    """
    Displays one MCQ question and collects a valid A/B/C/D answer.
    Loops until valid input is given.
    """
    valid_letters = [opt.letter for opt in q.options]

    print()
    print(c(BOLD + YELLOW, f"  Q{q.id}. {q.text}"))
    print()
    for opt in q.options:
        print(f"    {c(CYAN, opt.letter)}.  {opt.text}")
    print()

    while True:
        try:
            raw = input(c(CYAN, "  Your answer (A/B/C/D): ")).strip().upper()
        except (KeyboardInterrupt, EOFError):
            print("\n\n  Bye.\n")
            sys.exit(0)

        if raw in valid_letters:
            # Echo back the chosen option
            chosen = next(opt for opt in q.options if opt.letter == raw)
            print(c(GRAY, f"  ✓ {raw} — {chosen.text}"))
            return raw
        else:
            print(c(GRAY, f"  Please enter one of: {', '.join(valid_letters)}"))


# ── Main flow ─────────────────────────────────────────────────────────────────
def run():
    header()

    # Ensure metrics are clear for this run
    metrics.reset()

    # 1. Get prompt (prefer inline `PROMPT` from prompt_text.py)
    prompt = INLINE_PROMPT if INLINE_PROMPT else get_prompt()
    if not prompt:
        print(c(GRAY, "\n  No prompt entered. Exiting.\n"))
        return

    print()
    print(c(GRAY, "  Thinking..."))

    # 2. Classify
    classification = classify_prompt(prompt)
    session = AgentSession(original_prompt=prompt, classification=classification)

    # 3. Branch: simple → pass through; complex → ask questions
    if not classification.is_complex:
        print()
        divider()
        print(c(GREEN, "  ✓ Simple prompt — no clarification needed."))
        divider()
        print()
        print(c(BOLD, "  Your prompt (unchanged):"))
        print()
        print(f"  {c(WHITE, prompt)}")
        print()
        print(c(GRAY,  "  Paste this directly into your LLM."))
        print()
        # Show run metrics
        metrics.print_summary()
        metrics.reset()
        return

    # 4. Generate questions
    print(c(GRAY, "  Complex prompt detected — generating questions..."))
    questions = generate_questions(prompt)
    session.questions = questions

    if not questions:
        print()
        print(c(GRAY, "  No questions generated. Passing prompt through as-is."))
        print()
        print(f"  {c(WHITE, prompt)}")
        print()
        # Show run metrics
        metrics.print_summary()
        metrics.reset()
        return

    # 5. Ask questions in CLI
    print()
    divider()
    print(c(BOLD + YELLOW, f"  Agent has {len(questions)} quick question(s) to improve your prompt:"))
    divider()

    for q in questions:
        answer = ask_question(q)
        q.chosen_letter = answer

    # 6. Rewrite
    print()
    print(c(GRAY, "  Rewriting your prompt..."))
    improved = rewrite_prompt(session)
    session.improved_prompt = improved

    # 7. Show result
    print()
    divider("━")
    print(c(BOLD + GREEN, "  ✓ Improved Prompt Ready"))
    divider("━")
    print()
    print(c(DIM, "  Original:"))
    print(c(GRAY, f"  {prompt}"))
    print()
    print(c(BOLD, "  Improved:"))
    print()

    # Word-wrap the improved prompt at ~70 chars for readability
    words = improved.split()
    line, lines = [], []
    for word in words:
        if sum(len(w) + 1 for w in line) + len(word) > 70:
            lines.append(" ".join(line))
            line = [word]
        else:
            line.append(word)
    if line:
        lines.append(" ".join(line))

    for l in lines:
        print(f"  {c(WHITE, l)}")

    print()
    divider("━")
    print(c(GRAY, "  Copy the improved prompt above and paste it into your LLM."))
    print()
    # Show run metrics
    metrics.print_summary()
    metrics.reset()


if __name__ == "__main__":
    run()