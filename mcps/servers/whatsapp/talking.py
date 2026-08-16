"""THE HANDFUL OF THE BRIDGE HAPPY HIMSELF NEEDS, ASKED FROM A PLAIN THREAD."""

import asyncio
from pathlib import Path

from mcps.servers.whatsapp.client import WhatsAppClient

reaching = None


def settled():
    """UP, LINKED, AND DONE WITH ITS OPENING SYNC."""
    if not (asked(client().get_status()) or {}).get("connected"):
        return False

    return not (asked(client().get("/sync-status")) or {}).get("syncing")


def pushed(chat, since):
    """WHETHER THIS DEVICE HAS PUT ANYTHING INTO THAT CHAT SINCE THEN, BY TOOL."""
    found = asked(client().get_pushed(since))

    if not isinstance(found, list):
        return False

    return any(each.get("chatJid") == chat for each in found)


def tail(chat, limit):
    """THE TAIL OF ONE CHAT, OLDEST FIRST."""
    found = asked(client().get_messages(chat, limit=limit))

    return found if isinstance(found, list) else []


def own(limit):
    """THE OWNER'S OWN LAST FEW MESSAGES ACROSS EVERY CHAT, OLDEST FIRST."""
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
    """A PICTURE INTO THE CHAT, AND OFF THIS DISK AFTERWARDS."""
    try:
        return note(chat, where)
    finally:
        Path(where).unlink(missing_ok=True)


def facing(chat, photo):
    """A PICTURE PUT ON A GROUP. GIVES BACK WHAT WENT WRONG, OR None."""
    return (asked(client().set_group_photo(chat, photo)) or {}).get("error")


def client():
    global reaching

    if reaching is None:
        reaching = WhatsAppClient()

    return reaching


def asked(coro):
    """THE CLIENT IS ASYNC BECAUSE THE MCP SERVER IS. NOTHING ON THIS SIDE IS."""
    return asyncio.run(coro)
