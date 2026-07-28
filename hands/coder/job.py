"""BACKGROUND JOB STATE AND PERSISTENCE."""

from datetime import datetime
import subprocess
import threading
import time

import memory.storage as storage

from hands.coder.registry import CODERS

# TABLE PLUS INDEX, SAME SHAPE AS STORAGE.
SCHEMA = """
CREATE TABLE IF NOT EXISTS coder_jobs (
    id         INTEGER PRIMARY KEY,
    at         TEXT    NOT NULL,
    epoch      REAL    NOT NULL,
    coder_name TEXT    NOT NULL,
    task       TEXT    NOT NULL,
    result     TEXT,
    failed     TEXT
);

CREATE INDEX IF NOT EXISTS coder_jobs_epoch ON coder_jobs(epoch);
"""

TIMEOUT_SECONDS = 900

current = None
lock = threading.Lock()
built = False


def setup():
    global built

    if built:
        return

    handle = storage.connect()

    with handle:
        handle.executescript(SCHEMA)

    built = True


class Job:
    """ONE ERRAND, ONE PROCESS, ONE WATCHER THREAD."""

    def __init__(self, coder_name, task):
        self.coder_name = coder_name
        self.task = task
        self.answer = None
        self.failed = None
        self.id = remember_start(coder_name, task)
        self.thread = threading.Thread(target=self.work, daemon=True)
        self.thread.start()

    def running(self):
        return self.thread.is_alive()

    def work(self):
        try:
            result = run(self.coder_name, self.task)
        except Exception as error:  # CHILD FAILURES STAY HERE.
            result = {"failed": f"{error.__class__.__name__}: {error}"}

        self.failed = result.get("failed")
        self.answer = result.get("answer")

        remember_finish(self.id, self.answer, self.failed)

    def report(self):
        if self.failed:
            return f"That build job did not work out. {self.failed}"

        if not self.answer:
            return f"Finished {self.task}, but it came back with nothing to tell you."

        return f"About {self.task}. {self.answer}"


def run(coder_name, task):
    command = CODERS[coder_name](task)

    try:
        done = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return {"failed": f"It gave up after {TIMEOUT_SECONDS // 60} minutes."}

    said = (done.stdout or "").strip()

    if done.returncode != 0:
        complaint = (done.stderr or "").strip() or said or f"exit code {done.returncode}"

        return {"failed": complaint[:500]}

    return {"answer": said[:2000] if said else None}


def remember_start(coder_name, task):
    now = time.time()
    at = datetime.now().astimezone().isoformat(timespec="seconds")

    return storage.write(
        """
        INSERT INTO coder_jobs (at, epoch, coder_name, task, result, failed)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (at, now, coder_name, task, None, None),
    )


def remember_finish(row_id, result, failed):
    storage.write(
        "UPDATE coder_jobs SET result = ?, failed = ? WHERE id = ?",
        (result, failed, row_id),
    )


def busy():
    return current is not None and current.running()
