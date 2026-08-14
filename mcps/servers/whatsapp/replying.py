"""SAYING IT BACK INTO THE CHAT, AND NEVER HEARING IT AGAIN."""

from collections import deque
from pathlib import Path

import voice
from mcps.servers.whatsapp import talking

REPLIES = Path(__file__).resolve().parents[3] / "data" / "replies"

REMEMBERED = 50

ours = deque(maxlen=REMEMBERED)
echoes = deque(maxlen=REMEMBERED)


def back(chat, entry, said, pictures, spoken, since):
    """WHAT HAPPY MADE OF THE TURN, INTO THE CHAT IT CAME FROM."""
    # ASKED BEFORE WE SEND A THING, OR THE PICTURES BELOW ARE THE SEND IT FINDS.
    already = talking.pushed(chat, since)

    # AHEAD OF THE WORDS, SO THE ANSWER READS AS A CAPTION UNDER WHAT IT IS ABOUT.
    for where in pictures:
        kept(talking.shown(chat, where))

    if not said or already:
        return

    # A VOICE NOTE THAT COULD NOT BE MADE OR SENT FALLS BACK TO WRITING.
    sent = aloud(chat, entry, said) if spoken else None

    kept(sent or talking.say(chat, said))
    echoes.append(said)


def mine(what):
    """WHETHER THAT MESSAGE IS ONE OF HIS OWN ANSWERS COMING BACK ROUND."""
    return what in ours


def again(text):
    """WHETHER HE HAS JUST SAID THAT."""
    return text in echoes


def kept(sent):
    """AN ANSWER OF OURS, BY ITS ID, SO THE NEXT LOOK KNOWS IT WAS NOT A QUESTION."""
    if sent:
        ours.append(sent)


def aloud(chat, entry, said):
    """A SPOKEN QUESTION ANSWERED THE SAME WAY, IF THERE IS A VOICE TO DO IT."""
    try:
        path = voice.wav(said, REPLIES / f"{entry['id']}.wav")
    except Exception:
        return None

    if not path:
        return None

    sent = talking.note(chat, path)
    path.unlink(missing_ok=True)

    return sent  # THE ID, OR None IF THE BRIDGE WOULD NOT TAKE IT.
