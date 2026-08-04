"""THE WHATSAPP BRIDGE, FROM HAPPY'S SIDE: STARTING IT, ASKING IT, PUTTING IT DOWN.

THE BRIDGE IS A FLASK SERVER RUNNING NEONIZE AND IT IS THE ONLY THING ANYWHERE
THAT TOUCHES WHATSAPP. IT USED TO BE SOMETHING A PERSON RAN IN A SECOND TERMINAL,
WHICH IS THE WORST SHAPE IT COULD HAVE HAD: FORGET IT AND NOTHING ERRORS, THE
TOOLS JUST GO ON ANSWERING OUT OF WHATEVER THEY LAST SAW. HAPPY STARTS IT NOW.

IT IS A CHILD PROCESS AND NOT A THREAD ON PURPOSE. FLASK WANTS SIGNALS AND
NEONIZE HOLDS A LINKED SESSION, AND EITHER OF THEM FALLING OVER INSIDE HAPPY
WOULD TAKE THE ASSISTANT WITH IT.

ITS OUTPUT GOES TO A FILE AND NEVER TO OURS. IN --serve MODE HAPPY'S STDOUT *IS*
THE PROTOCOL THE WINDOW READS, SO ONE FLASK REQUEST LOG ON IT IS A PANEL THAT
STOPS UPDATING.
"""

import atexit
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

import httpx

OURS = Path(__file__).resolve().parents[1]

BRIDGE = OURS / "mcps" / "servers" / "whatsapp" / "bridge.py"

LOG = OURS / "data" / "whatsapp.log"

NAME = "whatsapp"

PORT = int(os.environ.get("WHATSAPP_BRIDGE_PORT") or 3001)

BASE = f"http://127.0.0.1:{PORT}"

HEADERS = {"X-Bridge-Key": os.environ.get("INTERNAL_API_SECRET", "")}

GOODBYE_SECONDS = 5

# A BRIDGE THAT CANNOT START IS ONE DEAD PROCESS PER PRESS, NOT A STREAM OF THEM.
AGAIN_SECONDS = 30

# HOW LONG A BRIDGE WE JUST STARTED GETS BEFORE WE ASK IT ANYTHING.
COMING_TRIES = 20

# LONGER THAN ANYBODY TAKES TO FIND THEIR PHONE. IT STOPS THE MOMENT THE SCAN LANDS.
WATCH_SECONDS = 3
WATCH_TRIES = 100

ours = None
noted = None
tried = 0.0
started = False
seen = None
told = None
watching = False
lock = threading.Lock()


def whenever(callback):
    """WHO TO TELL WHEN THE LINK FINALLY LANDS, SO THE PANEL CAN REDRAW ITSELF."""
    global told

    told = callback


def start():
    """START THE BRIDGE IF IT IS WANTED AND NOT ALREADY THERE, ANSWERING TO NOBODY.

    ON A THREAD BECAUSE ASKING WHETHER IT IS THERE IS A ROUND TRIP, AND THIS IS
    CALLED WHILE THE SPEECH MODEL IS STILL LOADING.
    """
    threading.Thread(target=waking, daemon=True, name="whatsapp").start()


def waking():
    """THE BRIDGE UP, AND THEN ONE QUESTION: IS AN ACCOUNT ACTUALLY LINKED?

    THE PANEL NEEDS THAT ANSWER WHETHER OR NOT ANYBODY HAS OPENED THE WHATSAPP
    ROW, BECAUSE IT IS THE DIFFERENCE BETWEEN CONNECTED AND WAITING FOR A SCAN.
    """
    if not ensure():
        return

    for _ in range(COMING_TRIES):
        if answering():
            resume()

            return

        time.sleep(1)


def resume():
    """AN ACCOUNT THAT WAS ALREADY LINKED, BACK ON THE WIRE WITHOUT THE PHONE.

    THE PAIRING OUTLIVES BOTH PROCESSES: IT IS IN THE BRIDGE'S OWN DATABASE AND
    STILL THERE ON THE NEXT RUN. NOTHING PUT IT BACK ON THOUGH. ASKING FOR THE QR
    ONLY READS HOW FAR A SESSION HAS GOT AND NEVER STARTS ONE, SO A RESTART LEFT A
    LINKED ACCOUNT LOOKING EXACTLY LIKE ONE NOBODY HAD EVER SCANNED, AND THE WAY
    BACK WAS THE QR AGAIN. STARTING IT IS THE MISSING ASK, AND THE ANSWER IS THE
    SAME WATCH AS A SCAN: IT LANDS IN A FEW SECONDS AND THE PANEL REDRAWS ITSELF.
    """
    if look() == "connected":
        return

    if not configured():
        return

    try:
        httpx.post(f"{BASE}/default/start", headers=HEADERS, timeout=10, trust_env=False)
    except Exception:
        return

    watch()


def configured():
    """TRUE WHEN THE BRIDGE STILL HOLDS WHAT A PAST SCAN LEFT IT. NOT THE SAME AS
    LINKED: THIS IS AN ACCOUNT ON DISK, NOT ONE CURRENTLY ON THE WIRE."""
    try:
        answer = httpx.get(f"{BASE}/default/status", headers=HEADERS, timeout=3, trust_env=False)

        return bool(answer.json().get("configured"))
    except Exception:
        return False


def linked():
    """TRUE WHEN THE BRIDGE LAST SAID A REAL ACCOUNT IS ON THE END OF IT."""
    return seen == "connected"


def look():
    """WHERE THE BRIDGE IS UP TO, REMEMBERED SO THE PANEL NEED NOT ASK EVERY DRAW."""
    global seen

    try:
        answer = httpx.get(f"{BASE}/default/qr", headers=HEADERS, timeout=3, trust_env=False)
        seen = answer.json().get("status")
    except Exception:
        seen = None

    return seen


def ensure():
    """THE BRIDGE UP, OR A GOOD REASON NOT TO HAVE STARTED IT."""
    from mcps import store

    row = store.one(NAME)

    # NOBODY CONNECTED WHATSAPP, SO NOTHING OF OURS LINKS TO THEIR ACCOUNT.
    if not row or not row["tools"]:
        return False

    with lock:
        if alive():
            return True

        # ONE SOMEBODY ELSE IS ALREADY RUNNING IS THEIRS, NOT OURS TO DOUBLE UP ON.
        if answering():
            return True

        if time.monotonic() - tried < AGAIN_SECONDS:
            return False

        return spawn()


def spawn():
    global ours, noted, tried, started

    if not BRIDGE.exists():
        return False

    LOG.parent.mkdir(parents=True, exist_ok=True)
    closed()

    tried = time.monotonic()

    try:
        # THE FIRST START OF A RUN GETS A FRESH LOG; A RETRY ADDS TO IT, SO THE
        # REASON THE LAST ONE DIED IS STILL THERE TO READ.
        noted = open(LOG, "a" if started else "w")
        started = True
        ours = subprocess.Popen(
            [sys.executable, str(BRIDGE)],
            stdout=noted,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            cwd=str(OURS),
            # WITHOUT THIS WINDOWS FLASHES A CONSOLE WINDOW IN SOMEBODY'S FACE.
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        return False

    return True


def alive():
    return ours is not None and ours.poll() is None


def answering():
    """TRUE WHEN SOMETHING IS SERVING THE BRIDGE'S PORT. /health WANTS NO KEY."""
    try:
        return httpx.get(f"{BASE}/health", timeout=2, trust_env=False).status_code == 200
    except Exception:
        return False


def stop():
    """PUT DOWN ONLY A BRIDGE WE STARTED. ONE SOMEBODY ELSE IS RUNNING IS THEIRS."""
    global ours, seen

    seen = None

    with lock:
        here, ours = ours, None

        if here is not None and here.poll() is None:
            here.terminate()

            try:
                here.wait(GOODBYE_SECONDS)
            except Exception:
                here.kill()

        closed()


def closed():
    """LET GO OF THE LOG. CALLED HOLDING THE LOCK, BY WHOEVER IS DONE WITH IT."""
    global noted

    if noted is not None:
        try:
            noted.close()
        except Exception:
            pass

        noted = None


def scan():
    """THE BRIDGE UP, AND THE SCAN PAGE IN FRONT OF WHOEVER PRESSED CONNECT.

    THE QR USED TO BE DRAWN IN THE PANEL, WHICH MEANT POLLING FOR IT EVERY THREE
    SECONDS AND A ROW THAT OFFERED A WAY IN AND A WAY OUT AT THE SAME TIME. A
    BROWSER IS WHERE SIGNING INTO GOOGLE ALREADY HAPPENS, SO NOW BOTH ARE THE
    SAME SHAPE: PRESS THE BUTTON, FINISH IN A TAB, COME BACK.
    """
    if not ensure():
        return False

    for _ in range(COMING_TRIES):
        if answering():
            break

        time.sleep(1)

    if not answering():
        return False

    look()
    watch()

    return show(f"{BASE}/default/scan")


def watch():
    """KEEP LOOKING UNTIL THE SCAN LANDS, THEN TELL WHOEVER IS DRAWING THE PANEL.

    THE QR IS SCANNED IN A BROWSER NOW, SO NOTHING ON THIS SIDE WOULD EVER NOTICE
    ON ITS OWN. THE WINDOW ASKS FOR ITS SETTINGS ONCE, WHEN IT STARTS, AND WOULD
    OTHERWISE GO ON SAYING WAITING FOR THE QR UNTIL SOMEBODY RESTARTED HAPPY.
    """
    global watching

    with lock:
        if watching:
            return

        watching = True

    threading.Thread(target=watched, daemon=True, name="whatsapp-scan").start()


def watched():
    global watching

    try:
        for _ in range(WATCH_TRIES):
            if not answering():
                return

            if look() == "connected":
                if told:
                    told()

                return

            time.sleep(WATCH_SECONDS)
    finally:
        watching = False


def show(where):
    """THE PAGE, OR THE ADDRESS PRINTED WHERE SOMEBODY CAN COPY IT."""
    if not webbrowser.open(where):
        print(f"\n  Open this to link WhatsApp:\n    {where}\n")

    return True


def disconnect(name):
    """UNLINK THE ACCOUNT, THEN PUT THE BRIDGE DOWN. IT HAS NOTHING LEFT TO HOLD."""
    if name != NAME:
        return {"success": False}

    try:
        answer = httpx.post(
            f"{BASE}/default/disconnect", headers=HEADERS, timeout=10, trust_env=False
        )
        said = answer.json()
    except Exception as error:
        said = {"success": False, "error": str(error)[:200]}

    stop()

    return said


atexit.register(stop)
