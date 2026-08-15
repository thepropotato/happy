"""EVERY SERVER THAT IS SWITCHED ON, AND THE ONE PLACE THAT HOLDS THEM."""

import sys
import threading

from mcps import loop, registry, store
from mcps.session import Session, local
from memory import settings

held = {}
lock = threading.Lock()


def patience():
    return settings.get("mcps.timeout", 20)


def session(row):
    """THE SERVER FOR ONE ROW, STARTED THE FIRST TIME ANYBODY WANTS IT."""
    with lock:
        here = held.get(row["name"])

        if here is None:
            here = Session(registry.label(row["name"]), opening(row), timeout=patience())
            held[row["name"]] = here

        here.timeout = patience()

        return here


def opening(row):
    """HOW THIS SERVER IS STARTED, WHICH IS THE PYTHON HAPPY IS ALREADY RUNNING ON SO IT
    INHERITS THE VIRTUALENV WITHOUT BEING TOLD WHERE IT IS."""
    return local(sys.executable, [str(registry.server(row["name"]))])


def live():
    """EVERY SERVICE THAT IS CONNECTED, WHICH IS EVERY ONE REMEMBERING TOOLS."""
    return [row for row in store.every() if row["tools"]]


def warm():
    """START WHAT IS SWITCHED ON, IN THE BACKGROUND, ANSWERING TO NOBODY."""
    for row in live():
        loop.submit(waking(row))


async def waking(row):
    here = session(row)

    try:
        offered = await here.listing()
    except Exception as error:
        store.mark(row["name"], complaint(row, error))

        return False

    refreshed(row, [tool.model_dump() for tool in offered])
    store.mark(row["name"], None)

    return True


def refreshed(row, offered):
    """WHAT THE SERVER REALLY OFFERS, AND THE GRAPH TOLD WHEN THAT IS NEWS."""
    if offered == row["tools"]:
        return

    from mcps.joining import stir

    store.remember(row["name"], offered)
    stir()


def refresh(row):
    """START A SERVER, ASK WHAT IT OFFERS, AND WAIT FOR THE ANSWER."""
    try:
        return loop.run(waking(row), patience() + 5)
    except Exception as error:
        store.mark(row["name"], complaint(row, error))

        return False


def complaint(row, error):
    """WHAT WENT WRONG, AS SOMETHING A ROW CAN SAY."""
    return str(error)[:200] or f"{registry.label(row['name'])} did not answer in time"


def drop(name):
    """STOP ONE SERVER AND FORGET WE EVER HELD IT."""
    with lock:
        here = held.pop(name, None)

    if here is not None:
        try:
            loop.run(here.close(), 5)
        except Exception:
            pass


def shut():
    """STOP EVERY SERVER, FOR A HAPPY THAT IS GOING AWAY."""
    for name in list(held):
        drop(name)
