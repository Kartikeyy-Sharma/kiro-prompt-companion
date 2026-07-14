"""
metrics.py — tracks token usage, cost, and latency per component per run.

Usage:
    from agent.metrics import metrics

    # wrap any LLM call:
    with metrics.track("Classifier"):
        result = call_llm(...)

    # at the end of a run:
    metrics.print_summary()
    metrics.reset()          # clear for next run
"""

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from config import PRICING

# ── Terminal colours ──────────────────────────────────────────────────────────
RESET  = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
CYAN   = "\033[96m"; GREEN = "\033[92m"; YELLOW = "\033[93m"
GRAY   = "\033[90m"; WHITE = "\033[97m"

def c(col, txt): return f"{col}{txt}{RESET}"


@dataclass
class ComponentMetrics:
    name:          str
    model:         str   = ""
    input_tokens:  int   = 0
    output_tokens: int   = 0
    latency_ms:    float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def cost_usd(self) -> float:
        pricing = PRICING.get(self.model, {"input": 0, "output": 0})
        return (
            self.input_tokens  * pricing["input"]  / 1_000_000 +
            self.output_tokens * pricing["output"] / 1_000_000
        )


class MetricsTracker:
    def __init__(self):
        self._components: list[ComponentMetrics] = []
        self._current: ComponentMetrics | None = None
        self._start_time: float = 0.0

    def reset(self):
        self._components = []
        self._current = None

    @contextmanager
    def track(self, name: str, model: str = ""):
        """Context manager — wraps an LLM call and measures latency."""
        cm = ComponentMetrics(name=name, model=model)
        self._current = cm
        self._start_time = time.perf_counter()
        try:
            yield cm
        finally:
            cm.latency_ms = (time.perf_counter() - self._start_time) * 1000
            self._components.append(cm)
            self._current = None

    def record_usage(self, input_tokens: int, output_tokens: int):
        """Call this inside a track() block after getting API response."""
        if self._current:
            self._current.input_tokens  = input_tokens
            self._current.output_tokens = output_tokens

    def print_summary(self):
        if not self._components:
            return

        total_tokens  = sum(c.total_tokens for c in self._components)
        total_cost    = sum(c.cost_usd     for c in self._components)
        total_latency = sum(c.latency_ms   for c in self._components)

        # ── Column widths ──
        col = [18, 8, 10, 10, 12, 12, 14]
        def row(*cells):
            parts = [str(cells[i]).ljust(col[i]) for i in range(len(cells))]
            return "  " + "  ".join(parts)

        header = row("Component", "Model", "In tok", "Out tok",
                     "Total tok", "Cost", "Latency")
        divider = "  " + "─" * (sum(col) + len(col) * 2)

        print()
        print(c(BOLD + CYAN, "  ┌─ Run Metrics " + "─" * 44))
        print()
        print(c(DIM, header))
        print(c(GRAY, divider))

        for cm in self._components:
            model_short = cm.model.split("/")[-1] if "/" in cm.model else cm.model
            cost_str    = f"${cm.cost_usd:.6f}"
            lat_str     = f"{cm.latency_ms:.0f}ms"
            line = row(
                cm.name,
                model_short,
                str(cm.input_tokens),
                str(cm.output_tokens),
                str(cm.total_tokens),
                cost_str,
                lat_str,
            )
            print(f"  {c(WHITE, line.strip())}")

        print(c(GRAY, divider))

        # Totals row
        total_row = row(
            "TOTAL", "",
            str(sum(c.input_tokens  for c in self._components)),
            str(sum(c.output_tokens for c in self._components)),
            str(total_tokens),
            f"${total_cost:.6f}",
            f"{total_latency:.0f}ms",
        )
        print(c(BOLD + GREEN, f"  {total_row.strip()}"))
        print()
        print(c(CYAN,  f"  └─ Total cost: ${total_cost:.6f}  │  "
                       f"Tokens: {total_tokens}  │  "
                       f"Latency: {total_latency:.0f}ms"))
        print()


# ── Singleton — import this everywhere ───────────────────────────────────────
metrics = MetricsTracker()