"""THE WHATSAPP BRIDGE, FROM HAPPY'S SIDE: STARTING IT, ASKING IT, PUTTING IT DOWN."""

import atexit
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

import httpx
import psutil

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
tried = None
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
    """START THE BRIDGE IF IT IS WANTED AND NOT ALREADY THERE, ANSWERING TO NOBODY."""
    threading.Thread(target=waking, daemon=True, name="whatsapp").start()


def waking():
    """THE BRIDGE UP, AND THEN ONE QUESTION: IS AN ACCOUNT ACTUALLY LINKED?"""
    if not ensure():
        return

    for _ in range(COMING_TRIES):
        if answering():
            resume()

            return

        time.sleep(1)


def resume():
    """AN ACCOUNT THAT WAS ALREADY LINKED, BACK ON THE WIRE WITHOUT THE PHONE."""
    if progress() == "connected":
        return

    if not configured():
        return

    try:
        httpx.post(f"{BASE}/default/start", headers=HEADERS, timeout=10, trust_env=False)
    except Exception:
        return

    watch()


def configured():
    """TRUE WHEN THE BRIDGE STILL HOLDS WHAT A PAST SCAN LEFT IT."""
    try:
        answer = httpx.get(f"{BASE}/default/status", headers=HEADERS, timeout=3, trust_env=False)

        return bool(answer.json().get("configured"))
    except Exception:
        return False


def linked():
    """TRUE WHEN THE BRIDGE LAST SAID A REAL ACCOUNT IS ON THE END OF IT."""
    return seen == "connected"


def progress():
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
    wanted = bool(row and row["tools"])

    with lock:
        # ONE WE STARTED AND STILL HOLD IS ALREADY THE ONE WE WANT.
        if alive():
            return True

        # NEVER TRIED IS NOT THE SAME AS TRIED AT THE MOMENT THE MACHINE CAME UP.
        if tried is not None and time.monotonic() - tried < AGAIN_SECONDS:
            return False

        # ANYTHING ELSE ON THE PORT OUTLIVED THE HAPPY THAT STARTED IT, AND SINCE
        # ONLY ONE HAPPY EVER RUNS IT IS A LEFTOVER RATHER THAN SOMEBODY'S. IT GOES
        # WHETHER OR NOT WE WANT ONE OF OUR OWN IN ITS PLACE.
        clear()

        if not wanted:
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


def holding():
    """WHOEVER IS LISTENING ON OUR PORT, WHICH ON THIS MACHINE ONLY A BRIDGE EVER IS."""
    mine = os.getpid()
    found = []

    for proc in psutil.process_iter():
        # THE PORT TABLE ITSELF WANTS ROOT, BUT A PROCESS OF OURS WILL SAY ITS OWN.
        try:
            if proc.pid == mine:
                continue
            for conn in proc.net_connections(kind="inet"):
                if conn.status == psutil.CONN_LISTEN and conn.laddr and conn.laddr.port == PORT:
                    found.append(proc)
                    break
        except Exception:
            continue

    return found


def clear():
    """PUT DOWN WHATEVER HOLDS THE PORT, SO A FRESH BRIDGE CAN HAVE IT."""
    held = holding()

    if not held:
        return

    # ASKED, NOT SHOT: THE BRIDGE WRITES ITS CHATS OUT ON THE WAY DOWN.
    for proc in held:
        try:
            proc.terminate()
        except Exception:
            continue

    for proc in psutil.wait_procs(held, timeout=GOODBYE_SECONDS)[1]:
        try:
            proc.kill()
        except Exception:
            continue


def stop():
    """PUT THE BRIDGE DOWN: THE ONE WE HOLD, AND ANYTHING LEFT SITTING ON THE PORT."""
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

        # A BRIDGE THAT OUTLIVED THE HANDLE WE HAD ON IT STILL HAS TO GO, OR THE
        # NEXT HAPPY INHERITS IT AND NOBODY EVER OWNS IT AGAIN.
        clear()

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
    """THE BRIDGE UP, AND THE SCAN PAGE IN FRONT OF WHOEVER PRESSED CONNECT."""
    if not ensure():
        return False

    for _ in range(COMING_TRIES):
        if answering():
            break

        time.sleep(1)

    if not answering():
        return False

    progress()
    watch()

    return show(f"{BASE}/default/scan")


def watch():
    """KEEP LOOKING UNTIL THE SCAN LANDS, THEN TELL WHOEVER IS DRAWING THE PANEL."""
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

            if progress() == "connected":
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
