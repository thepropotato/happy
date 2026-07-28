"""BACKGROUND JOB STATE AND PERSISTENCE."""

import atexit
from datetime import datetime
import json
import subprocess
import threading
import time

import memory.storage as storage

from hands.coder import registry

# TABLE PLUS INDEX, SAME SHAPE AS STORAGE.
SCHEMA = """
CREATE TABLE IF NOT EXISTS coder_jobs (
    id         INTEGER PRIMARY KEY,
    at         TEXT    NOT NULL,
    epoch      REAL    NOT NULL,
    coder_name TEXT    NOT NULL,
    task       TEXT    NOT NULL,
    session_id TEXT,
    result     TEXT,
    failed     TEXT
);

CREATE INDEX IF NOT EXISTS coder_jobs_epoch ON coder_jobs(epoch);
"""

TIMEOUT_SECONDS = 900

current = None
running_processes = set()
lock = threading.Lock()
built = False


def setup():
    global built

    if built:
        return

    handle = storage.connect()

    with handle:
        handle.executescript(SCHEMA)
        # KEEP OLD DATABASES WORKING AFTER THE NEW COLUMN WAS ADDED.
        try:
            handle.execute("ALTER TABLE coder_jobs ADD COLUMN session_id TEXT")
        except Exception:
            pass

    built = True


class Job:
    """ONE ERRAND, ONE PROCESS, ONE WATCHER THREAD."""

    def __init__(self, coder_name, task, session_id=None):
        self.coder_name = coder_name
        self.task = task
        self.session_id = session_id
        self.answer = None
        self.failed = None
        self.id = remember_start(coder_name, task, self.session_id)
        self.thread = threading.Thread(target=self.work, daemon=True)
        self.thread.start()

    def running(self):
        return self.thread.is_alive()

    def work(self):
        try:
            result = run(self.coder_name, self.task, self.session_id)
        except Exception as error:  # CHILD FAILURES STAY HERE.
            result = {"failed": f"{error.__class__.__name__}: {error}"}

        self.failed = result.get("failed")
        self.answer = result.get("answer")
        self.session_id = result.get("session_id")

        remember_finish(self.id, self.answer, self.failed, self.session_id)

    def report(self):
        if self.failed:
            return f"That build job did not work out. {self.failed}"

        if not self.answer:
            return f"Finished {self.task}, but it came back with nothing to tell you."

        return f"About {self.task}. {self.answer}"


def run(coder_name, task, session_id=None):
    if session_id and coder_name == "Claude Code":
        command = registry.claude_code_resume(session_id, task)
    else:
        command = registry.CODERS[coder_name](task)

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    running_processes.add(process)

    try:
        try:
            stdout, stderr = process.communicate(timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()

            return {"failed": f"It gave up after {TIMEOUT_SECONDS // 60} minutes."}
    finally:
        running_processes.discard(process)

    said = (stdout or "").strip()

    if process.returncode != 0:
        complaint = (stderr or "").strip() or said or f"exit code {process.returncode}"

        return {"failed": complaint[:500]}

    if coder_name == "Claude Code":
        if not said:
            return {"answer": None, "session_id": None}

        try:
            payload = json.loads(said)
        except json.JSONDecodeError:
            return {"failed": "Claude Code returned invalid JSON."}

        answer = payload.get("result")
        session_id = payload.get("session_id")

        return {"answer": answer[:2000] if answer else None, "session_id": session_id}

    return {"answer": said[:2000] if said else None}


def remember_start(coder_name, task, session_id):
    now = time.time()
    at = datetime.now().astimezone().isoformat(timespec="seconds")

    return storage.write(
        """
        INSERT INTO coder_jobs (at, epoch, coder_name, task, session_id, result, failed)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (at, now, coder_name, task, session_id, None, None),
    )


def remember_finish(row_id, result, failed, session_id):
    storage.write(
        "UPDATE coder_jobs SET result = ?, failed = ?, session_id = ? WHERE id = ?",
        (result, failed, session_id, row_id),
    )


def busy():
    return current is not None and current.running()


def cleanup():
    for process in list(running_processes):
        if process.poll() is None:
            process.terminate()


atexit.register(cleanup)
