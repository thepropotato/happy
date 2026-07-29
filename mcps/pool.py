"""EVERY CONNECTION THAT IS SWITCHED ON, AND THE ONE PLACE THAT HOLDS THEM.

NOTHING IN HERE IS ALLOWED TO BLOCK STARTING UP. THE TOOLS ARE BOUND OUT OF WHAT
THE STORE REMEMBERS, AND THE CONNECTIONS THEMSELVES COME UP ON THE LOOP WHILE THE
SPEECH MODEL IS STILL LOADING. A SERVICE THAT IS DOWN COSTS A SENTENCE, NOT A
SLOWER START.
"""

import os
import shlex
import threading

from mcps import directory, loop, store
from mcps.session import Session, local, remote
from memory import settings

held = {}
lock = threading.Lock()


def patience():
    return settings.get("mcps.timeout", 20)


def session(row):
    """THE CONNECTION FOR ONE ROW, MADE THE FIRST TIME ANYBODY WANTS IT."""
    with lock:
        here = held.get(row["name"])

        if here is None:
            here = Session(row["label"], opening(row), timeout=patience())
            held[row["name"]] = here

        here.timeout = patience()

        return here


def opening(row):
    """HOW THIS PARTICULAR CONNECTION IS REACHED, KIND BY KIND."""
    if row["kind"] == directory.LOCAL:
        words = [expanded(each) for each in shlex.split(row["address"])]

        return local(words[0], words[1:])

    return remote(row["address"], headers=headers(row), auth=proving(row))


def expanded(word):
    """A COMMAND SOMEBODY TYPED CAN SAY ~, AND A PIPE WILL NOT UNDERSTAND IT."""
    return os.path.expanduser(word)


def headers(row):
    """A PASTED TOKEN IS JUST A HEADER. NOTHING TO DISCOVER, NOTHING TO REFRESH."""
    if row["kind"] != directory.TOKEN:
        return None

    from mcps import tokens

    kept = (tokens.kept(row["name"]) or {}).get("tokens") or {}
    token = kept.get("access_token")

    return {"Authorization": f"Bearer {token}"} if token else None


def proving(row):
    """THE OAUTH SIGN IN FOR THIS ROW, WHEN IT HAS ONE. REFRESH ONLY, NO BROWSER."""
    if not directory.signs_in(row["kind"]):
        return None

    from mcps import signing

    return signing.quietly(row)


def live():
    """EVERY CONNECTION THE PERSON HAS SWITCHED ON."""
    return [row for row in store.every() if row["enabled"]]


def warm():
    """OPEN WHAT IS SWITCHED ON, IN THE BACKGROUND, ANSWERING TO NOBODY."""
    for row in live():
        loop.submit(waking(row))


async def waking(row):
    here = session(row)

    try:
        offered = await here.listing()
    except Exception as error:
        store.mark(row["name"], str(error)[:200] or "could not connect")

        return False

    store.remember(row["name"], [tool.model_dump() for tool in offered])
    store.mark(row["name"], None)

    return True


def refresh(row):
    """ASK A SERVER WHAT IT OFFERS NOW, AND WAIT FOR THE ANSWER."""
    try:
        return loop.run(waking(row), patience() + 5)
    except Exception as error:
        store.mark(row["name"], str(error)[:200])

        return False


def drop(name):
    """CLOSE ONE CONNECTION AND FORGET WE EVER HELD IT."""
    with lock:
        here = held.pop(name, None)

    if here is not None:
        try:
            loop.run(here.close(), 5)
        except Exception:  # A CONNECTION THAT WILL NOT SHUT IS STILL A CLOSED ONE.
            pass
