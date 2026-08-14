"""BEING SPOKEN TO IN A CHAT ON THE LINKED ACCOUNT."""

import re
import threading
import time

from ears import engines
from face import show
from mcps.servers.whatsapp import grouping, placing, replying, talking
from memory import settings

# HIS NAME, WRITTEN AND SAID.
WRITTEN = re.compile(r"@happy\b", re.IGNORECASE)

SPOKEN = re.compile(r"\bhey[\s,]*happy\b", re.IGNORECASE)

EVERY_SECONDS = 2

WINDOW = 25  # MESSAGES PER LOOK. MORE THAN ANYBODY SENDS INSIDE ONE GAP.

SETTING = "mcps.answering"

AUDIO = "audio"


def listen(turn):
    """START WATCHING."""
    threading.Thread(target=watching, args=(turn,), daemon=True, name="messages").start()


def watching(turn):
    home = None
    seen = None
    noted = None
    moaned = None

    while True:
        time.sleep(EVERY_SECONDS)

        answering = settings.get(SETTING)

        # THE GROUP IS MADE AS SOON AS THE ACCOUNT IS ON, WHETHER OR NOT ANYBODY HAS TURNED
        # ANSWERING ON YET.
        if home and not answering:
            continue

        try:
            if not talking.settled():
                continue

            home = home or grouping.his()

            if not answering:
                continue

            if home:
                seen = sweep(turn, home, seen)

            noted = elsewhere(turn, home, noted)

            moaned = None
        except Exception as error:
            # ONCE PER REASON. A BRIDGE THAT IS DOWN IS DOWN EVERY TWO SECONDS.
            if str(error) != moaned:
                moaned = str(error)
                show.trouble(f"Messages: {moaned}")


def sweep(turn, chat, seen):
    """EVERY MESSAGE IN HIS GROUP SINCE THE LAST ONE. GIVES BACK THE NEW MARK."""
    listed = talking.look(chat, WINDOW)

    if seen is None:
        return mark(listed[-1]) if listed else blank()

    for entry in behind(listed, seen):
        # MARKED BEFORE IT IS ANSWERED.
        seen = mark(entry)

        if not replying.mine(entry.get("id")):
            answer(turn, chat, entry, False)

    return seen


def elsewhere(turn, home, noted):
    """THE OWNER'S OWN MESSAGES IN EVERY OTHER CHAT, ANSWERED WHERE THEY NAME HIM."""
    listed = talking.own(WINDOW)

    if noted is None:
        return mark(listed[-1]) if listed else blank()

    for entry in behind(listed, noted):
        noted = mark(entry)

        chat = entry.get("chatJid")

        if chat and chat != home and not replying.mine(entry.get("id")):
            answer(turn, chat, entry, True)

    return noted


def answer(turn, chat, entry, named):
    asked, spoken = heard(chat, entry, named)

    if not asked or replying.again(asked):
        return

    # NAMED IS ALSO WHERE HE IS: HIS NAME ONLY HAS TO BE SAID SOMEWHERE THAT IS
    # NOT HIS OWN GROUP, AND ONLY THERE IS THERE SOMEBODY ELSE READING.
    since = time.time()
    said, pictures = turn(asked, placing.about(chat, entry, not named))

    replying.back(chat, entry, said, pictures, spoken, since)


def heard(chat, entry, named):
    """WHAT WAS ASKED OF HAPPY HERE, AND WHETHER IT WAS SAID RATHER THAN TYPED."""
    if not (entry.get("hasMedia") and entry.get("mediaType") == AUDIO):
        return wanted((entry.get("body") or "").strip(), WRITTEN, named), False

    where = talking.recording(chat, entry)

    if not where:
        return None, True

    return wanted(engines.transcribe(where), SPOKEN, named), True


def wanted(text, name, named):
    """WHAT WAS ASKED OF HIM, OR None IF IT WAS NOT ASKED OF HIM."""
    text = (text or "").strip()

    if not text:
        return None

    if not name.search(text):
        return None if named else text

    return name.sub(" ", text, count=1).strip(" ,.!?") or None


def mark(entry):
    return {"id": entry.get("id", ""), "at": entry.get("timestamp", 0)}


def blank():
    """WHERE WE CAME IN WHEN THERE WAS NOTHING THERE TO COME IN AFTER."""
    return {"id": "", "at": int(time.time())}


def behind(listed, seen):
    """THE PART OF THE LIST THAT COMES AFTER THE MARK."""
    for spot, each in enumerate(listed):
        if each.get("id") == seen["id"]:
            return listed[spot + 1:]

    # THE MARK HAS FALLEN OFF THE END OF THE WINDOW, SO THE CLOCK IS ALL WE HAVE.
    return [each for each in listed if each.get("timestamp", 0) > seen["at"]]
