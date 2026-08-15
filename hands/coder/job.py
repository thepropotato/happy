"""BACKGROUND JOB STATE AND PERSISTENCE."""

import atexit
from datetime import datetime
import subprocess
import threading
import time

import memory.storage as storage

from face import show
from hands.coder import coders, following

SCHEMA = """
CREATE TABLE IF NOT EXISTS coder_jobs (
    id         INTEGER PRIMARY KEY,
    at         TEXT    NOT NULL,
    epoch      REAL    NOT NULL,
    coder_name TEXT    NOT NULL,
    task       TEXT    NOT NULL,
    session_id TEXT,
    folder     TEXT,
    result     TEXT,
    failed     TEXT
);

CREATE INDEX IF NOT EXISTS coder_jobs_epoch ON coder_jobs(epoch);
"""

# ADDED SINCE THE TABLE WAS FIRST WRITTEN, SO AN OLD DATABASE HAS TO CATCH UP.
LATER = ["session_id TEXT", "folder TEXT"]

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

        # KEEP OLD DATABASES WORKING AFTER THE NEW COLUMNS.
        for column in LATER:
            try:
                handle.execute(f"ALTER TABLE coder_jobs ADD COLUMN {column}")
            except Exception:
                pass

    built = True


class Job:
    """ONE ERRAND, ONE PROCESS, ONE WATCHER THREAD."""

    def __init__(self, coder_name, task, folder, session_id=None):
        self.coder_name = coder_name
        self.task = task
        self.folder = str(folder)
        self.session_id = session_id
        self.answer = None
        self.failed = None
        self.doing = None  # THE LAST THING THE CODER SAID IT WAS DOING.
        self.id = remember_start(coder_name, task, self.session_id, self.folder)
        self.thread = threading.Thread(target=self.work, daemon=True)
        self.thread.start()

    def running(self):
        return self.thread.is_alive()

    def work(self):
        try:
            result = run(
                self.coder_name, self.task, self.folder, self.session_id, self.watching
            )
        except Exception as error:
            result = {"failed": f"{error.__class__.__name__}: {error}"}

        self.failed = result.get("failed")
        self.answer = result.get("answer")

        # KEPT WHEN THE RUN THAT JUST ENDED HAS NONE TO GIVE, OR ONE BAD GO WOULD
        # THROW AWAY THE THREAD OF EVERY GOOD ONE BEFORE IT.
        self.session_id = result.get("session_id") or self.session_id

        remember_finish(self.id, self.answer, self.failed, self.session_id)

        # NOBODY ASKED, AND WAITING TO BE ASKED IS HOW A FINISHED JOB GOES UNNOTICED.
        show.unprompted(self.report())

    def watching(self, said):
        """WHAT THE CODER IS DOING, ON THE FACE WHILE IT IS STILL DOING IT."""
        self.doing = said

        show.working(said)

    def progress(self):
        doing = f" Right now: {self.doing}" if self.doing else ""

        return f"Still working on: {trimmed(self.task)}.{doing}"

    def report(self):
        if self.failed:
            return f"That build job did not work out. {self.failed}"

        if not self.answer:
            return f"Finished {trimmed(self.task)}, but it came back with nothing to tell you."

        return f"About {trimmed(self.task)}. {self.answer}"


def run(coder_name, task, folder, session_id=None, watching=None):
    if session_id and coder_name == "Claude Code":
        command = coders.claude_code_resume(session_id, task)
    else:
        command = coders.CODERS[coder_name](task)

    # THE ONE THING THAT DECIDES WHICH PROJECT GETS WRITTEN INTO. WITHOUT IT THE
    # CODER INHERITS WHEREVER HAPPY WAS STARTED FROM, WHICH IS HAPPY'S OWN CODE.
    process = subprocess.Popen(
        command,
        cwd=folder,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    running_processes.add(process)

    # THE OUTPUT IS READ A LINE AT A TIME NOW, SO THE DEADLINE CANNOT RIDE ALONG
    # ON A communicate() CALL AND HAS TO KEEP ITS OWN CLOCK.
    overdue = threading.Event()
    alarm = threading.Timer(TIMEOUT_SECONDS, expire, args=(process, overdue))
    alarm.start()

    # DRAINED ON ITS OWN THREAD, OR A CODER THAT COMPLAINS ENOUGH TO FILL THE PIPE
    # SITS THERE WAITING FOR SOMEBODY TO READ IT.
    complaints = []
    grumbling = threading.Thread(target=complaints.extend, args=(process.stderr,), daemon=True)
    grumbling.start()

    try:
        found = watched(coder_name, process, watching)
        process.wait()
    finally:
        alarm.cancel()
        grumbling.join(timeout=1)
        running_processes.discard(process)

    return outcome(found, process.returncode, complaints, overdue.is_set())


def watched(coder_name, process, watching):
    """WHAT CAME OUT OF THE CODER, SAID OUT LOUD AS IT CAME IF IT SPEAKS JSON."""
    if coder_name not in coders.STREAMING:
        return {"answer": process.stdout.read()}

    return following.follow(process.stdout, watching or (lambda said: None))


def expire(process, overdue):
    """THE DEADLINE CAME ROUND AND THE CODER IS STILL GOING."""
    if process.poll() is not None:
        return

    overdue.set()
    process.kill()


def outcome(found, code, complaints, overdue):
    """WHAT THE RUN CAME TO, WITH THE SESSION KEPT WHICHEVER WAY IT WENT."""
    session = {"session_id": found.get("session_id")}

    if overdue:
        return {**session, "failed": f"It gave up after {TIMEOUT_SECONDS // 60} minutes."}

    if code != 0:
        complaint = "".join(complaints).strip() or f"exit code {code}"

        return {**session, "failed": complaint[:500]}

    if found.get("failed"):
        return {**session, "failed": str(found["failed"])[:500]}

    answer = (found.get("answer") or "").strip()

    return {**session, "answer": answer[:2000] or None}


def trimmed(task):
    """A TASK WITH ITS OWN FULL STOP OFF, SO IT CAN SIT INSIDE A SENTENCE."""
    return " ".join(str(task).split()).rstrip(".")


def remember_start(coder_name, task, session_id, folder):
    now = time.time()
    at = datetime.now().astimezone().isoformat(timespec="seconds")

    return storage.write(
        """
        INSERT INTO coder_jobs (at, epoch, coder_name, task, session_id, folder, result, failed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (at, now, coder_name, task, session_id, folder, None, None),
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
