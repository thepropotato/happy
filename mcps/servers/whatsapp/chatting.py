"""BEING SPOKEN TO IN A CHAT ON THE LINKED ACCOUNT.

THE BRIDGE ALREADY HEARS EVERY MESSAGE THE MOMENT IT LANDS AND TELLS NOBODY, SO
THIS ASKS IT. ONE CHAT IS HIS AND EVERY OTHER ONE IS NOT.

A GROUP WITH HIS NAME ON IT IS THE CHAT WITH HAPPY. NOTHING IN THERE WAS MEANT
FOR ANYBODY ELSE, SO EVERYTHING SAID IN IT IS SAID TO HIM AND NOTHING HAS TO BE
TAGGED. ANYWHERE ELSE A CHAT IS NOT A MICROPHONE: A MESSAGE IS ONLY A TURN WHEN
THE OWNER HIMSELF SAYS HAPPY'S NAME IN IT. ANYBODY IN ANY GROUP CAN TYPE @happy,
AND NONE OF THEM IS WHO HAPPY ANSWERS TO.

WHERE WE GOT TO IS HELD FOR AS LONG AS HAPPY IS UP AND NO LONGER. A QUESTION
ASKED WHILE HE WAS OFF IS NOT ANSWERED SIX HOURS LATE; THE FIRST LOOK OF A RUN
ONLY MARKS WHERE WE CAME IN.

talking.py IS EVERYTHING THIS ASKS OF THE BRIDGE, replying.py EVERYTHING IT SAYS.
"""

import re
import threading
import time

from ears import engines
from face import show
from mcps.servers.whatsapp import replying, talking
from memory import settings

# HIS NAME, WRITTEN AND SAID. A CHAT NEEDS THE @ TO LOOK ADDRESSED; A VOICE NOTE
# CANNOT CARRY ONE, SO THE SPOKEN FORM IS THE ONE PEOPLE ACTUALLY SAY.
WRITTEN = re.compile(r"@happy\b", re.IGNORECASE)

SPOKEN = re.compile(r"\bhey[\s,]*happy\b", re.IGNORECASE)

EVERY_SECONDS = 2

WINDOW = 25  # MESSAGES PER LOOK. MORE THAN ANYBODY SENDS INSIDE ONE GAP.

SETTING = "mcps.answering"

AUDIO = "audio"


def listen(turn):
    """START WATCHING.

    turn TAKES WHAT WAS ASKED AND GIVES BACK WHAT TO SAY, PLUS ANY PICTURES THAT
    GO WITH IT. A CHAT IS THE ONE PLACE HAPPY CAN BE ASKED TO *SHOW* SOMETHING.
    """
    threading.Thread(target=watching, args=(turn,), daemon=True, name="messages").start()


def watching(turn):
    home = None
    seen = None
    noted = None
    moaned = None

    while True:
        time.sleep(EVERY_SECONDS)

        if not settings.get(SETTING):
            continue

        try:
            if not talking.settled():
                continue

            home = home or found()

            if home:
                seen = sweep(turn, home, seen)

            noted = elsewhere(turn, home, noted)

            moaned = None
        except Exception as error:
            # ONCE PER REASON. A BRIDGE THAT IS DOWN IS DOWN EVERY TWO SECONDS.
            if str(error) != moaned:
                moaned = str(error)
                show.trouble(f"Messages: {moaned}")


def found():
    """HIS GROUP, SAID ONCE WHEN IT TURNS UP SO NOBODY WONDERS WHICH ONE IT IS."""
    where, name = talking.home()

    if where:
        show.note(f'Answering in "{name}"')

    return where


def sweep(turn, chat, seen):
    """EVERY MESSAGE IN HIS GROUP SINCE THE LAST ONE. GIVES BACK THE NEW MARK."""
    listed = talking.look(chat, WINDOW)

    if seen is None:
        return mark(listed[-1]) if listed else None

    for entry in behind(listed, seen):
        # MARKED BEFORE IT IS ANSWERED. ONE MESSAGE THAT THROWS MUST NOT BE
        # PICKED UP AGAIN ON EVERY LOOP FOREVER.
        seen = mark(entry)

        if not replying.mine(entry.get("id")):
            answer(turn, chat, entry, False)

    return seen


def elsewhere(turn, home, noted):
    """THE OWNER'S OWN MESSAGES IN EVERY OTHER CHAT, ANSWERED WHERE THEY NAME HIM.

    HIS OWN GROUP IS SKIPPED BECAUSE THE SWEEP ABOVE HAS ALREADY HAD IT, TAG OR
    NO TAG. NOTHING SPECIAL IS LEFT OF THE OWNER'S OWN CHAT EITHER: IT IS ONE
    MORE CHAT WHERE SAYING HIS NAME REACHES HIM.
    """
    listed = talking.own(WINDOW)

    if noted is None:
        return mark(listed[-1]) if listed else None

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

    said, pictures = turn(asked)

    replying.back(chat, entry, said, pictures, spoken)


def heard(chat, entry, named):
    """WHAT WAS ASKED OF HAPPY HERE, AND WHETHER IT WAS SAID RATHER THAN TYPED."""
    if not (entry.get("hasMedia") and entry.get("mediaType") == AUDIO):
        return wanted((entry.get("body") or "").strip(), WRITTEN, named), False

    where = talking.recording(chat, entry)

    if not where:
        return None, True

    return wanted(engines.transcribe(where), SPOKEN, named), True


def wanted(text, name, named):
    """WHAT WAS ASKED OF HIM, OR None IF IT WAS NOT ASKED OF HIM.

    HIS NAME COMES OUT EITHER WAY. IN HIS OWN GROUP NOBODY HAS TO WRITE IT AND
    PLENTY STILL WILL; ANYWHERE ELSE IT IS THE WHOLE REASON WE ARE READING.
    """
    text = (text or "").strip()

    if not text:
        return None

    if not name.search(text):
        return None if named else text

    return name.sub(" ", text, count=1).strip(" ,.!?") or None


def mark(entry):
    return {"id": entry.get("id", ""), "at": entry.get("timestamp", 0)}


def behind(listed, seen):
    """THE PART OF THE LIST THAT COMES AFTER THE MARK.

    THE MARK IS A MESSAGE, NOT A TIME. TWO OF THEM CAN SHARE A SECOND AND ONLY
    ONE WOULD SURVIVE BEING CUT BY THE CLOCK.
    """
    for spot, each in enumerate(listed):
        if each.get("id") == seen["id"]:
            return listed[spot + 1:]

    # THE MARK HAS FALLEN OFF THE END OF THE WINDOW, SO THE CLOCK IS ALL WE HAVE.
    return [each for each in listed if each.get("timestamp", 0) > seen["at"]]
