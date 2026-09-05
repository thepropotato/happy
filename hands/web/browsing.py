"""HAPPY'S OWN BROWSER, FOR A PAGE THAT ONLY EXISTS ONCE ITS SCRIPTS HAVE RUN. NEVER THE PERSON'S."""

import queue
import threading
from concurrent.futures import Future
from pathlib import Path

from memory import storage

# ITS OWN PROFILE, BESIDE THE DATABASE, SO COOKIES AND CONSENT CLICKS SURVIVE A RESTART.
PROFILE = Path(storage.path()).parent / "browser"

# HOW LONG A PAGE GETS TO ARRIVE, AND HOW LONG AFTER THAT FOR ITS SCRIPTS TO GO QUIET.
PATIENCE_MS = 15000
SETTLE_MS = 4000

# WHAT THE PAGE IS NEVER ALLOWED TO FETCH: THE WORDS ARE WANTED, NOT THE PICTURES.
HEAVY = ("image", "media", "font")

TEXT = "document.body ? document.body.innerText : ''"

NO_BROWSER = "no browser is installed to render it"

asks = queue.Queue()

started = threading.Lock()

worker = None


def text(address):
    """THE WORDS ON THE PAGE ONCE IT HAS DRAWN ITSELF, AND ITS TITLE."""
    begin()
    answer = Future()
    asks.put((address, answer))

    return answer.result(timeout=(PATIENCE_MS + SETTLE_MS) / 1000 + 10)


def begin():
    """ONE BROWSER, ON ONE THREAD OF ITS OWN, STARTED THE FIRST TIME ANYBODY ASKS."""
    global worker

    with started:
        if worker is None or not worker.is_alive():
            worker = threading.Thread(target=serve, daemon=True, name="browser")
            worker.start()


def serve():
    """THE THREAD: OPEN THE BROWSER ONCE, THEN ANSWER EVERY ASK IN TURN.

    PLAYWRIGHT'S SYNC API MUST STAY ON THE THREAD THAT MADE IT, AND MUST NOT SHARE ONE WITH
    AN EVENT LOOP, WHICH IS WHY THE BROWSER LIVES HERE AND NOT IN THE TOOL."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        drain(RuntimeError(NO_BROWSER))
        return

    try:
        with sync_playwright() as play:
            context = opened(play)

            while True:
                address, answer = asks.get()

                try:
                    answer.set_result(read(context, address))
                except Exception as error:
                    answer.set_exception(error)
    except Exception as error:
        drain(error)


def opened(play):
    PROFILE.mkdir(parents=True, exist_ok=True)

    context = play.chromium.launch_persistent_context(
        str(PROFILE),
        headless=True,
        channel="chromium",
        args=["--disable-blink-features=AutomationControlled"],
        viewport={"width": 1280, "height": 900},
    )
    context.route("**/*", lambda route: route.abort() if route.request.resource_type in HEAVY else route.continue_())

    return context


def read(context, address):
    page = context.new_page()

    try:
        page.goto(address, wait_until="domcontentloaded", timeout=PATIENCE_MS)

        try:
            page.wait_for_load_state("networkidle", timeout=SETTLE_MS)
        except Exception:
            pass  # A PAGE THAT NEVER GOES QUIET HAS STILL DRAWN ITSELF.

        return page.title(), page.evaluate(TEXT)
    finally:
        page.close()


def drain(error):
    """THE BROWSER IS GONE, SO EVERY ASK WAITING ON IT IS TOLD RATHER THAN LEFT HANGING."""
    global worker

    worker = None

    while True:
        try:
            _, answer = asks.get_nowait()
        except queue.Empty:
            return

        answer.set_exception(error)
