"""ONE EXCHANGE, AND A STOPWATCH ON EACH PART OF IT."""

import time

BAR = "│"
DOT = "·"

MODEL = "model"


class Turn:
    def __init__(self):
        self.started = time.perf_counter()
        self.heard = None
        self.first = None
        self.thought = None
        self.tools = []
        self.speaking = False

    def seconds(self):
        return time.perf_counter() - self.started

    def add(self, name, taken):
        self.tools.append((name, taken))

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

    lines = [f" {BAR} ".join(parts)]

    if this.tools:
        each = f" {DOT} ".join(f"{name} {clock(taken)}" for name, taken in this.tools)
        lines.append(f"{DOT} {each}")

    return lines


def clock(seconds):
    return f"{seconds * 1000:.0f}ms" if seconds < 1 else f"{seconds:.2f}s"
