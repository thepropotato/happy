"""CODER TOOLS THE MODEL CAN CALL."""

from langchain_core.tools import tool

from hands.coder import job
from hands.coder.registry import available

STARTED = "Started. Carry on, I will say when it is done."
BUSY = "Already working on something in the coder: "
NOTHING = "Nothing running, and nothing finished since you last asked."
MISSING = "No coding tools are installed."


@tool
def build(task: str) -> str:
    """Run a coding errand in the background and return right away."""
    job.setup()
    names = available()

    if not names:
        return MISSING

    with job.lock:
        if job.busy():
            return BUSY + job.current.task  # ONE CODER, ONE ERRAND AT A TIME.

        job.current = job.Job(names[0], task)

    return STARTED


@tool
def build_status() -> str:
    """Say whether the background build is still going, and what came back."""
    if job.current is None:
        return NOTHING

    return f"Still working on: {job.current.task}" if job.current.running() else job.current.report()


TOOLS = [build, build_status]
