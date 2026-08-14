"""CODER TOOLS THE MODEL CAN CALL."""

from langchain_core.tools import tool
import memory.storage as storage

from hands import asking
from hands.coder import job, where
from hands.coder.registry import available

STARTED = "Started in {folder}. Carry on, I will say when it is done."
BUSY = "Already working on something in the coder: "
NOTHING = "Nothing running, and nothing finished since you last asked."
MISSING = "No coding tools are installed."
NO_CONTINUE = "There is nothing to continue right now."
NO_FOLLOWUPS = "This coder does not support answering follow-ups."


@tool
def build(task: str, project: str) -> str:
    """Hand off substantial coding work to Claude Code or Codex.

    Use this for new projects, multi-file features, or bug fixes that need
    investigation, code changes, and iteration. Prefer this over run_command
    for anything beyond a trivial one-file script.

    project says which folder the work happens in. For work on something that
    already exists, give its name and I will find it. For work that has no folder
    yet, ask the user where it should go first, then pass the whole path they
    said. Never make a path up and never leave this out."""
    job.setup()
    names = available()

    if not names:
        return asking.no(MISSING)

    folder, complaint = where.settle(project)

    if folder is None:
        return asking.no(complaint)

    with job.lock:
        if job.busy():
            return BUSY + job.current.task

        job.current = job.Job(names[0], task, folder)

    return STARTED.format(folder=folder)


@tool
def build_status() -> str:
    """Say whether the background build is still going, and what came back."""
    if job.current is None:
        return NOTHING

    return job.current.progress() if job.current.running() else job.current.report()


@tool
def build_answer(response: str) -> str:
    """Send a follow-up to the coder that just finished, in its own session.

    Use this when the user wants a change to work the coder already did, or has
    answered something it asked. It carries on in the same folder and keeps
    everything that session already knows, so prefer it over build for anything
    that follows on from the last job."""
    if job.current is None:
        job.setup()
        rows = storage.read(
            """
            SELECT coder_name, session_id, folder
            FROM coder_jobs
            WHERE session_id IS NOT NULL AND folder IS NOT NULL AND coder_name = 'Claude Code'
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
                latest["folder"],
                session_id=latest["session_id"],
            )

        return STARTED.format(folder=latest["folder"])

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
            job.current.folder,
            session_id=job.current.session_id,
        )

    return STARTED.format(folder=job.current.folder)


TOOLS = [build, build_status, build_answer]
