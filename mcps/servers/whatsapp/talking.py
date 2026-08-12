"""THE HANDFUL OF THE BRIDGE HAPPY HIMSELF NEEDS, ASKED FROM A PLAIN THREAD.

client.py NEXT DOOR IS THE WHOLE BRIDGE'S API AND IT IS ASYNC, BECAUSE THE MCP
SERVER THAT USES IT IS. NOTHING ON THIS SIDE IS: chatting.py IS A LOOP ON A
THREAD, SO EVERY ANSWER IS WAITED FOR HERE AND HANDED BACK AS A PLAIN VALUE.
"""

import asyncio
from pathlib import Path

from mcps.servers.whatsapp.client import WhatsAppClient

reaching = None


def settled():
    """UP, LINKED, AND DONE WITH ITS OPENING SYNC.

    EVERY CONNECT PUTS THE BRIDGE BACK INTO ONE, AND WHAT IT KNOWS DURING A SYNC
    IS WHATEVER IT HAD BEFORE. ASKING THEN WOULD MARK MESSAGES NOBODY HAS SEEN.
    """
    if not (asked(client().get_status()) or {}).get("connected"):
        return False

    return not (asked(client().get("/sync-status")) or {}).get("syncing")


def pushed(chat, since):
    """WHETHER THIS DEVICE HAS PUT ANYTHING INTO THAT CHAT SINCE THEN, BY TOOL.

    A SEND OF OUR OWN IS NEVER ECHOED BACK TO US, SO IT IS IN NO CHAT WE READ.
    THE BRIDGE NOTES EVERY ONE IT ACKNOWLEDGED AND THIS IS THE ONLY WAY TO ASK.
    """
    found = asked(client().get_pushed(since))

    if not isinstance(found, list):
        return False

    return any(each.get("chatJid") == chat for each in found)


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
