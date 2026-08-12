"""SAYING IT BACK INTO THE CHAT, AND NEVER HEARING IT AGAIN.

HIS ANSWERS GO OUT ON THE SAME ACCOUNT THE OWNER WRITES FROM AND COME BACK
LOOKING LIKE ANYBODY'S. IN HIS OWN GROUP NOTHING HAS TO BE TAGGED EITHER, SO AN
ANSWER OF HIS READS EXACTLY LIKE A QUESTION: UNLESS EVERY ONE IS REMEMBERED HE
ANSWERS HIMSELF UNTIL SOMEBODY PULLS THE PLUG.

THE ID IS THE GUARD THAT MATTERS. THE WORDS ARE THE ONE UNDERNEATH IT, FOR AN
ANSWER THE BRIDGE TOOK AND NEVER GAVE A NAME.
"""

from collections import deque
from pathlib import Path

import voice
from mcps.servers.whatsapp import talking

REPLIES = Path(__file__).resolve().parents[3] / "data" / "replies"

REMEMBERED = 50

ours = deque(maxlen=REMEMBERED)
echoes = deque(maxlen=REMEMBERED)


def back(chat, entry, said, pictures, spoken, since):
    """WHAT HAPPY MADE OF THE TURN, INTO THE CHAT IT CAME FROM.

    UNLESS HE HAS ALREADY WRITTEN IN THERE HIMSELF. ASKED IN SOMEBODY'S CHAT TO
    TELL THEM SOMETHING, HIS ANSWER *IS* THE MESSAGE AND HE IS TOLD SO — BUT HE
    IS ALSO HOLDING A TOOL THAT SENDS MESSAGES, AND SOMETIMES HE REACHES FOR IT.
    THEN THE ERRAND IS DONE AND WHAT HE SAYS AFTERWARDS IS A REPORT MEANT FOR THE
    OWNER: SENT ON, IT LANDS IN FRONT OF THE PERSON IT WAS ABOUT, UNDERNEATH THE
    MESSAGE IT IS DESCRIBING. NO WORDING SURVIVES EVERY TURN, SO THIS IS NOT LEFT
    TO WORDING: WHAT WENT BY TOOL WENT, AND NOTHING IS SAID ON TOP OF IT.
    """
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
    """WHETHER HE HAS JUST SAID THAT. A VOICE NOTE OF HIS, HEARD BACK, IS CLOSE
    ENOUGH TO WHAT HE SAID FOR THE ID TO BE THE ONLY OTHER THING HOLDING IT."""
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
