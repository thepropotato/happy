"""ONE EXCHANGE, AND A STOPWATCH ON EACH PART OF IT."""

import time

BAR = "│"
DOT = "·"

MODEL = "model"

# REPORTED ON THE WAY IN: IT CARRIES NO TIME YET.
STARTED = "tool.started"

# ONE ROUND'S TOKENS, REPORTED THE MOMENT THE MODEL COMES BACK.
SPENT = "spent"

THOUSAND = 1000


class Turn:
    def __init__(self):
        self.started = time.perf_counter()
        self.heard = None
        self.first = None
        self.thought = None
        self.tools = []
        self.speaking = False

        # ADDED UP OVER EVERY ROUND, BECAUSE A TURN IS NEVER ONE REQUEST.
        self.read = 0
        self.wrote = 0
        self.prefill = 0.0

    def seconds(self):
        return time.perf_counter() - self.started

    def add(self, name, taken):
        self.tools.append((name, taken))

    def paid(self, spent):
        """ONE MORE ROUND'S TOKENS ONTO THIS TURN'S BILL."""
        self.read += (spent or {}).get("read") or 0
        self.wrote += (spent or {}).get("wrote") or 0
        self.prefill += (spent or {}).get("prefill") or 0.0

    def spent(self):
        return sum(taken for _, taken in self.tools)


def stats(this):
    """ONE OR TWO LINES ON WHERE THE TIME WENT."""
    parts = []

    if this.heard is not None:
        parts.append(f"heard {clock(this.heard)}")

    if this.thought is not None:
        # WAITING ON TOOLS TAKEN BACK OUT, OR THE TWO NUMBERS DOUBLE COUNT.
        parts.append(f"thought {clock(max(0.0, this.thought - this.spent()))}")

    if this.tools:
        parts.append(f"tools {clock(this.spent())}")

    if this.first is not None:
        parts.append(f"first word {clock(this.first)}")

    parts.append(f"total {clock(this.seconds())}")

    # RE-READING THE PROMPT, WHICH IS NOT THINKING AND NOT A TOOL, AND ON A MISSED PREFIX
    # IS MOST OF THE TURN.
    if this.prefill:
        parts.append(f"prefill {clock(this.prefill)}")

    # LAST, AND ITS OWN PART: IT IS THE ONLY NUMBER HERE THAT IS NOT A CLOCK.
    if this.read or this.wrote:
        parts.append(f"tokens {count(this.read)} read {DOT} {count(this.wrote)} wrote")

    lines = [f" {BAR} ".join(parts)]

    if this.tools:
        each = f" {DOT} ".join(f"{name} {clock(taken)}" for name, taken in this.tools)
        lines.append(f"{DOT} {each}")

    return lines


def clock(seconds):
    return f"{seconds * 1000:.0f}ms" if seconds < 1 else f"{seconds:.2f}s"


def count(tokens):
    """A TOKEN COUNT SHORT ENOUGH TO SIT BESIDE A CLOCK. 12664 IS 12.7k."""
    if tokens < THOUSAND:
        return str(tokens)

    return f"{tokens / THOUSAND:.1f}k"
