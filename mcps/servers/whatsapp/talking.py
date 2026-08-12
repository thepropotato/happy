"""THE HANDFUL OF THE BRIDGE HAPPY HIMSELF NEEDS, ASKED FROM A PLAIN THREAD.

client.py NEXT DOOR IS THE WHOLE BRIDGE'S API AND IT IS ASYNC, BECAUSE THE MCP
SERVER THAT USES IT IS. NOTHING ON THIS SIDE IS: chatting.py IS A LOOP ON A
THREAD, SO EVERY ANSWER IS WAITED FOR HERE AND HANDED BACK AS A PLAIN VALUE.
"""

import asyncio
import re
from pathlib import Path

from mcps.servers.whatsapp.client import WhatsAppClient

MINE = "happy"

# WHAT A NAME IS ONCE THE EMOJI AND THE PUNCTUATION ARE OFF IT.
WORDS = re.compile(r"[^\W_]+", re.UNICODE)

reaching = None


def home():
    """THE GROUP THAT IS THE CHAT WITH HAPPY, OR None UNTIL SOMEBODY MAKES ONE.

    A GROUP CALLED AFTER HIM IS THE WHOLE SETUP: NOTHING TO PASTE, NOTHING TO
    PICK IN A SETTING, AND IT IS PLAIN FROM THE PHONE WHICH CHAT HE IS IN.

    HIS NAME AND NOTHING ELSE, BECAUSE EVERYTHING SAID IN HERE IS ANSWERED. A
    GROUP THAT MERELY MENTIONS HIM IS SOMEBODY'S HAPPY BIRTHDAY THREAD, AND
    GUESSING WRONG WOULD HAVE HIM TALKING OVER SEVEN OF THEIR FRIENDS.
    """
    found = asked(client().get_groups())

    if not isinstance(found, list):
        return None, None

    for group in found:
        if group.get("id") and called(group.get("name")):
            return group["id"], str(group.get("name") or MINE).strip()

    return None, None


def called(name):
    """WHETHER THAT NAME IS HIS. EMOJI AND PUNCTUATION ARE DECORATION, NOT WORDS."""
    return " ".join(WORDS.findall(str(name or "").lower())) == MINE


def settled():
    """UP, LINKED, AND DONE WITH ITS OPENING SYNC.

    EVERY CONNECT PUTS THE BRIDGE BACK INTO ONE, AND WHAT IT KNOWS DURING A SYNC
    IS WHATEVER IT HAD BEFORE. ASKING THEN WOULD MARK MESSAGES NOBODY HAS SEEN.
    """
    if not (asked(client().get_status()) or {}).get("connected"):
        return False

    return not (asked(client().get("/sync-status")) or {}).get("syncing")


def look(chat, limit):
    """THE TAIL OF ONE CHAT, OLDEST FIRST."""
    found = asked(client().get_messages(chat, limit=limit))

    return found if isinstance(found, list) else []


def own(limit):
    """THE OWNER'S OWN LAST FEW MESSAGES ACROSS EVERY CHAT, OLDEST FIRST.

    THE BRIDGE KEEPS THESE AS THEY LAND, SO ASKING EVERY TWO SECONDS COSTS
    NOTHING. READING EVERY CHAT'S TAIL INSTEAD WOULD BE A FULL SCAN A SECOND.
    """
    found = asked(client().get_recent_sent(limit=limit))

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
