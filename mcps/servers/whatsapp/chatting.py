"""BEING SPOKEN TO IN THE CHAT ON THE LINKED ACCOUNT.

THE BRIDGE ALREADY HEARS EVERY MESSAGE THE MOMENT IT LANDS AND TELLS NOBODY, SO
THIS ASKS IT. A CHAT IS NOT A MICROPHONE: NEARLY EVERYTHING IN ONE WAS NEVER
MEANT FOR HAPPY, SO A MESSAGE IS ONLY A TURN WHEN IT SAYS HIS NAME.

A PERSON'S OWN CHAT IS THE ONE PLACE ONLY THEIR OWN DEVICES CAN WRITE INTO,
WHICH IS THE WHOLE REASON IT IS THE CHAT WE WATCH.

WHERE WE GOT TO IS HELD FOR AS LONG AS HAPPY IS UP AND NO LONGER. A QUESTION
ASKED WHILE HE WAS OFF IS NOT ANSWERED SIX HOURS LATE; THE FIRST LOOK OF A RUN
ONLY MARKS WHERE WE CAME IN.

client.py NEXT DOOR IS THE WHOLE BRIDGE'S API AND IT IS ASYNC, BECAUSE THE MCP
SERVER THAT USES IT IS. THE BOTTOM OF THIS FILE IS THE HANDFUL OF IT HAPPY
HIMSELF NEEDS, ASKED FROM A PLAIN THREAD.
"""

import asyncio
import re
import threading
import time
from pathlib import Path

import voice
from ears import engines
from face import show
from mcps.servers.whatsapp.client import WhatsAppClient
from memory import settings

# HIS NAME, WRITTEN AND SAID. A CHAT NEEDS THE @ TO LOOK ADDRESSED; A VOICE NOTE
# CANNOT CARRY ONE, SO THE SPOKEN FORM IS THE ONE PEOPLE ACTUALLY SAY.
WRITTEN = re.compile(r"@happy\b", re.IGNORECASE)

SPOKEN = re.compile(r"\bhey[\s,]*happy\b", re.IGNORECASE)

EVERY_SECONDS = 2

WINDOW = 25  # MESSAGES PER LOOK. MORE THAN ANYBODY SENDS INSIDE ONE GAP.

SETTING = "mcps.answering"

AUDIO = "audio"

DIRECT = "s.whatsapp.net"

REPLIES = Path(__file__).resolve().parents[3] / "data" / "replies"

# HIS OWN ANSWERS GO INTO THE SAME CHAT AND COME BACK LOOKING LIKE ANYBODY'S.
# ONE THAT QUOTED THE TAG WOULD BE ANSWERED AGAIN, AND AGAIN AFTER THAT.
REMEMBERED = 50

reaching = None
ours = set()


def listen(turn):
    """START WATCHING.

    turn TAKES WHAT WAS ASKED AND GIVES BACK WHAT TO SAY, PLUS ANY PICTURES THAT
    GO WITH IT. A CHAT IS THE ONE PLACE HAPPY CAN BE ASKED TO *SHOW* SOMETHING.
    """
    threading.Thread(target=watching, args=(turn,), daemon=True, name="messages").start()


def watching(turn):
    chat = None
    seen = None
    moaned = None

    while True:
        time.sleep(EVERY_SECONDS)

        if not settings.get(SETTING):
            continue

        try:
            if not settled():
                continue

            chat = chat or mine()

            if chat:
                seen = sweep(turn, chat, seen)

            moaned = None
        except Exception as error:
            # ONCE PER REASON. A BRIDGE THAT IS DOWN IS DOWN EVERY TWO SECONDS.
            if str(error) != moaned:
                moaned = str(error)
                show.trouble(f"Messages: {moaned}")


def sweep(turn, chat, seen):
    """EVERY MESSAGE SINCE THE LAST ONE, ANSWERED. GIVES BACK THE NEW MARK."""
    found = look(chat, WINDOW)

    if seen is None:
        return mark(found[-1]) if found else None

    for entry in behind(found, seen):
        # MARKED BEFORE IT IS ANSWERED. ONE MESSAGE THAT THROWS MUST NOT BE
        # PICKED UP AGAIN ON EVERY LOOP FOREVER.
        seen = mark(entry)

        if entry.get("id") not in ours:
            answer(turn, chat, entry)

    return seen


def answer(turn, chat, entry):
    asked, spoken = heard(chat, entry)

    if not asked:
        return

    said, pictures = turn(asked)

    # AHEAD OF THE WORDS, SO THE ANSWER READS AS A CAPTION UNDER WHAT IT IS ABOUT.
    for where in pictures:
        kept(shown(chat, where))

    if not said:
        return

    # A VOICE NOTE THAT COULD NOT BE MADE OR SENT FALLS BACK TO WRITING.
    sent = aloud(chat, entry, said) if spoken else None

    kept(sent or say(chat, said))


def kept(sent):
    """AN ANSWER OF OURS, BY ITS ID, SO THE NEXT LOOK KNOWS IT WAS NOT A QUESTION."""
    if not sent:
        return

    if len(ours) >= REMEMBERED:
        ours.clear()

    ours.add(sent)


def aloud(chat, entry, said):
    """A SPOKEN QUESTION ANSWERED THE SAME WAY, IF THERE IS A VOICE TO DO IT."""
    try:
        path = voice.wav(said, REPLIES / f"{entry['id']}.wav")
    except Exception:
        return False

    if not path:
        return False

    sent = note(chat, path)
    path.unlink(missing_ok=True)

    return sent  # THE ID, OR None IF THE BRIDGE WOULD NOT TAKE IT.


def heard(chat, entry):
    """WHAT WAS ASKED OF HAPPY HERE, AND WHETHER IT WAS SAID RATHER THAN TYPED."""
    if not (entry.get("hasMedia") and entry.get("mediaType") == AUDIO):
        return addressed((entry.get("body") or "").strip(), WRITTEN), False

    where = recording(chat, entry)

    if not where:
        return None, True

    return addressed(engines.transcribe(where), SPOKEN), True


def addressed(text, name):
    """WHAT IS LEFT ONCE HIS NAME IS TAKEN OUT, OR None IF IT WAS NEVER THERE."""
    if not text or not name.search(text):
        return None

    return name.sub(" ", text, count=1).strip(" ,.!?")


def mark(entry):
    return {"id": entry.get("id", ""), "at": entry.get("timestamp", 0)}


def behind(found, seen):
    """THE PART OF THE LIST THAT COMES AFTER THE MARK.

    THE MARK IS A MESSAGE, NOT A TIME. TWO OF THEM CAN SHARE A SECOND AND ONLY
    ONE WOULD SURVIVE BEING CUT BY THE CLOCK.
    """
    for spot, each in enumerate(found):
        if each.get("id") == seen["id"]:
            return found[spot + 1:]

    # THE MARK HAS FALLEN OFF THE END OF THE WINDOW, SO THE CLOCK IS ALL WE HAVE.
    return [each for each in found if each.get("timestamp", 0) > seen["at"]]


def mine():
    """THE LINKED ACCOUNT'S OWN CHAT, OR None WHEN NOTHING IS LINKED."""
    phone = (asked(client().get_status()) or {}).get("phone")

    return f"{phone}@{DIRECT}" if phone else None


def settled():
    """UP, LINKED, AND DONE WITH ITS OPENING SYNC.

    EVERY CONNECT PUTS THE BRIDGE BACK INTO ONE, AND WHAT IT KNOWS DURING A SYNC
    IS WHATEVER IT HAD BEFORE. ASKING THEN WOULD MARK MESSAGES NOBODY HAS SEEN.
    """
    if not (asked(client().get_status()) or {}).get("connected"):
        return False

    return not (asked(client().get("/sync-status")) or {}).get("syncing")


def look(chat, limit):
    """THE TAIL OF THE CHAT, OLDEST FIRST."""
    found = asked(client().get_messages(chat, limit=limit))

    return found if isinstance(found, list) else []


def recording(chat, entry):
    """A VOICE NOTE PUT ON DISK, OR None IF IT COULD NOT BE FETCHED."""
    got = asked(client().download_media_from_message(entry["id"], chat=chat))

    return (got or {}).get("local_path")


def say(chat, text):
    """WRITTEN INTO THE CHAT. RETURNS THE ID IT WAS GIVEN, SO WE KNOW IT WAS US."""
    return (asked(client().send_message(chat, text)) or {}).get("messageId")


def note(chat, path):
    """A .wav IS AUDIO TO THE BRIDGE, SO WHAT LANDS IS A VOICE NOTE."""
    return (asked(client().send_media_message(chat, str(path))) or {}).get("messageId")


def shown(chat, where):
    """A PICTURE INTO THE CHAT, AND OFF THIS DISK AFTERWARDS.

    THE BRIDGE GOES BY THE SUFFIX, SO A .png LANDS AS A PHOTO AND NOT AS A FILE.
    THROWN AWAY EITHER WAY: A SHOT NOBODY COULD BE SENT IS STILL A SHOT OF THEIR
    SCREEN SAT IN A FOLDER.
    """
    try:
        return note(chat, where)
    finally:
        Path(where).unlink(missing_ok=True)


def client():
    global reaching

    if reaching is None:
        reaching = WhatsAppClient()

    return reaching


def asked(coro):
    """THE CLIENT IS ASYNC BECAUSE THE MCP SERVER IS. NOTHING ON THIS SIDE IS."""
    return asyncio.run(coro)
