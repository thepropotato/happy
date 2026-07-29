"""CODER TOOLS THE MODEL CAN CALL."""

from langchain_core.tools import tool

from hands.coder import job
from hands.coder.registry import available

STARTED = "Started. Carry on, I will say when it is done."
BUSY = "Already working on something in the coder: "
NOTHING = "Nothing running, and nothing finished since you last asked."
MISSING = "No coding tools are installed."
NO_CONTINUE = "There is nothing to continue right now."
NO_FOLLOWUPS = "This coder does not support answering follow-ups."


@tool
def build(task: str) -> str:
    """Hand off substantial coding work to Claude Code or Codex.

    Use this for new projects, multi-file features, or bug fixes that need
    investigation, code changes, and iteration. Prefer this over run_command
    for anything beyond a trivial one-file script."""
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


@tool
def build_answer(response: str) -> str:
    """Use when build_status says the coder asked a question or needs approval.

    Send your reply here to continue that same session; chat replies alone do not
    reach the coding tool."""
    if job.current is None or not job.current.session_id:
        return NO_CONTINUE

    if job.current.coder_name != "Claude Code":
        return NO_FOLLOWUPS

    with job.lock:
        if job.busy():
            return BUSY + job.current.task  # ONE CODER, ONE ERRAND AT A TIME.

        job.current = job.Job(
            job.current.coder_name,
            response,
            session_id=job.current.session_id,
        )

    return STARTED


TOOLS = [build, build_status, build_answer]
