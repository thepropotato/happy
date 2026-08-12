"""THE ONE CHAT THAT IS HIS: FOUND IF IT IS THERE, MADE IF IT IS NOT.

A GROUP CALLED AFTER HIM IS THE WHOLE SETUP. THERE IS NOTHING TO PASTE AND
NOTHING TO PICK IN A SETTING, AND IT IS PLAIN FROM THE PHONE WHICH CHAT HE IS
IN — AND NOBODY SHOULD HAVE TO BE TOLD TO GO AND MAKE IT FIRST, SO ONCE THE
ACCOUNT IS ON HE OPENS ONE HIMSELF AND IT IS SITTING THERE WAITING.

HIS NAME AND NOTHING ELSE COUNTS AS HIS, BECAUSE EVERYTHING SAID IN HERE IS
ANSWERED. A GROUP THAT MERELY MENTIONS HIM IS SOMEBODY'S HAPPY BIRTHDAY THREAD,
AND GUESSING WRONG WOULD HAVE HIM TALKING OVER SEVEN OF THEIR FRIENDS.
"""

import re
import time

from face import show
from mcps.servers.whatsapp import talking

# WHAT THE GROUP IS CALLED WHEN HAPPY MAKES IT, AND THE ONLY NAME HE ANSWERS TO.
NAME = "Happy"

# WHAT A NAME IS ONCE THE EMOJI AND THE PUNCTUATION ARE OFF IT.
WORDS = re.compile(r"[^\W_]+", re.UNICODE)

# A GROUP WHATSAPP WOULD NOT MAKE IS NOT MADE THIRTY TIMES A MINUTE EITHER.
AGAIN_SECONDS = 60

tried = 0.0


def his():
    """HIS GROUP, MADE IF THERE ISN'T ONE, SAID ONCE SO NOBODY WONDERS WHICH.

    THE ACCOUNT IS ON AND SYNCED BEFORE THIS IS ASKED, SO A GROUP THAT IS NOT IN
    THE LIST IS ONE THAT DOES NOT EXIST RATHER THAN ONE NOT LOADED YET. MAKING
    IT OFF A HALF SYNCED LIST WOULD LEAVE THE OWNER WITH TWO.
    """
    global tried

    where, name = found()

    if not where:
        if time.monotonic() - tried < AGAIN_SECONDS:
            return None

        tried = time.monotonic()
        where, name = made()

    show.note(f'Answering in "{name}"')

    return where


def found():
    """THE GROUP OF HIS THAT IS ALREADY THERE, OR None, None.

    A LIST THAT COULD NOT BE READ THROWS RATHER THAN COMING BACK EMPTY: NOTHING
    HERE IS ALLOWED TO LOOK LIKE HAVING NO GROUP, WHICH IS WHAT MAKES A SECOND.
    """
    listed = talking.asked(talking.client().get("/groups"))

    if not isinstance(listed, list):
        raise RuntimeError((listed or {}).get("error") or "the group list could not be read")

    for group in listed:
        if group.get("id") and called(group.get("name")):
            return group["id"], str(group.get("name") or NAME).strip()

    return None, None


def made():
    """THE GROUP, STARTED. THERE IS NOBODY IN IT BUT THE OWNER."""
    fresh = talking.asked(talking.client().create_group(NAME))

    if not isinstance(fresh, dict) or not fresh.get("id"):
        raise RuntimeError((fresh or {}).get("error") or "the group could not be made")

    return fresh["id"], fresh.get("name") or NAME


def called(name):
    """WHETHER THAT NAME IS HIS. EMOJI AND PUNCTUATION ARE DECORATION, NOT WORDS."""
    return " ".join(WORDS.findall(str(name or "").lower())) == NAME.lower()
