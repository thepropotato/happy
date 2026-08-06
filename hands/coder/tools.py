"""CODER TOOLS THE MODEL CAN CALL."""

from langchain_core.tools import tool
import memory.storage as storage

from hands import asking
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
        return asking.no(MISSING)

    with job.lock:
        if job.busy():
            return BUSY + job.current.task

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
    if job.current is None:
        job.setup()
        rows = storage.read(
            """
            SELECT coder_name, session_id
            FROM coder_jobs
            WHERE session_id IS NOT NULL AND coder_name = 'Claude Code'
            ORDER BY epoch DESC
            LIMIT 1
            """
        )

        if not rows:
            return asking.no(NO_CONTINUE)

        latest = rows[0]

        with job.lock:
            if job.busy():
                return BUSY + job.current.task  # ONE CODER, ONE ERRAND AT A TIME.

            job.current = job.Job(
                latest["coder_name"],
                response,
                session_id=latest["session_id"],
            )

        return STARTED

    if not job.current.session_id:
        return asking.no(NO_CONTINUE)

    if job.current.coder_name != "Claude Code":
        return asking.no(NO_FOLLOWUPS)

    with job.lock:
        if job.busy():
            return BUSY + job.current.task

        job.current = job.Job(
            job.current.coder_name,
            response,
            session_id=job.current.session_id,
        )

    return STARTED


TOOLS = [build, build_status, build_answer]
