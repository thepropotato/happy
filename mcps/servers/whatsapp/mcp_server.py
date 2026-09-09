import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Annotated, Optional

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# THE SERVER'S OWN FOLDER COMES OFF THE PATH SO A FILE BESIDE THIS ONE CAN NEVER
# BE WHAT SOME LIBRARY'S import FINDS FIRST.
sys.path[0] = str(Path(__file__).resolve().parents[2])

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server.fastmcp import Context, FastMCP
from pydantic import BeforeValidator, Field

from memory import knowledge
from servers.shared.answering import ok
from servers.whatsapp.client import WhatsAppClient


def coerce_str(v):
    """Coerce any non-string value to empty string so Pydantic validation never crashes."""
    if isinstance(v, (dict, list)):
        return ""
    if v is None:
        return ""
    s = str(v).strip()
    if s.startswith("```") or (s.startswith("{") and s.endswith("}")):
        return ""
    # THE MODEL QUOTES ITS OWN ARGUMENTS: '"the boys"' IS MEANT AS 'the boys'.
    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
        s = s[1:-1].strip()
    return s


CoercedStr = Annotated[str, BeforeValidator(coerce_str)]

NOBODY = (
    'No WhatsApp contact matches "{name}". Ask this person who they meant, saying "{name}" '
    "back to them the way you heard it, and use only the name they give you. Do not send "
    "this to anyone else, and never to someone named earlier in the conversation. "
    "When they give you a name and it is found, remember it against \"{name}\" with "
    "remember_contact and go straight on with what they first asked for, here on WhatsApp: "
    "a name that failed is a step to repeat, not a reason to start driving the app by hand."
)

mcp = FastMCP("whatsapp", log_level="ERROR")

from contextvars import ContextVar

# A CONTEXTVAR, NOT A GLOBAL: CONCURRENT REQUESTS MUST NOT SHARE WHICHEVER
# CLIENT WAS LAZILY MADE FIRST.
client: ContextVar["WhatsAppClient | None"] = ContextVar("whatsapp_client", default=None)


def get_client() -> WhatsAppClient:
    wa = client.get()
    if wa is None:
        wa = WhatsAppClient()
        client.set(wa)
    return wa

def _json(obj) -> str:
    """Serialize to a single JSON string so FastMCP returns ONE content block instead of
    splitting lists into N separate blocks."""
    return json.dumps(obj, ensure_ascii=False, default=str)

async def check_sync_status(wa: WhatsAppClient) -> dict | None:
    """Check if sync is in progress. Returns sync status dict if syncing, None otherwise."""
    try:
        sync_status = await wa.get("/sync-status", timeout=3.0)
        if sync_status.get("syncing"):
            return sync_status
    except Exception:
        pass
    return None

async def should_sync_on_error(result: dict) -> bool:
    """Check if the error indicates sync is needed (contact not found, empty contacts, etc.)."""
    if not isinstance(result, dict):
        return False
    error = result.get("error", "")
    if not error:
        return False
    # NARROW ON PURPOSE: "Media file not found" MUST NOT START A SYNC.
    return "Contact not found" in error

@mcp.tool()
async def get_status() -> str:
    """Get WhatsApp connection status and client info."""
    wa = get_client()
    return _json(await wa.get_status())

@mcp.tool()
async def who_signed_in() -> str:
    """THE NAME ON THIS ACCOUNT. HAPPY ASKS IT HIMSELF; IT IS NEVER OFFERED TO THE MODEL."""
    found = await get_client().get_status() or {}

    if not (found.get("connected") or found.get("authenticated")):
        return ""

    return str(found.get("name") or "").strip()

@mcp.tool()
async def get_sync_status() -> str:
    """Whether WhatsApp is up to date with the phone, and whether it is still catching up.
    Use this for: "are the messages synced?", "is WhatsApp up to date?", "did it finish syncing?",
    "is WhatsApp connected?". This is the ONLY tool that can answer that - reading messages
    or chats tells you nothing about whether they are current.

    "connected": true means the live socket is up and every new message arrives the instant
    it is sent, so nothing is waiting. "syncing": true means old history is still loading in
    the background; new messages still arrive live while that happens.
    """
    wa = get_client()
    try:
        found = await wa.get("/sync-status", timeout=5.0)
    except Exception as e:
        return _json({"error": f"Could not reach WhatsApp: {e}"})

    if not isinstance(found, dict):
        return _json({"error": "Could not read sync status"})

    if not found.get("connected"):
        found["user_message"] = "WhatsApp is not connected, so new messages are not arriving."
    elif found.get("syncing"):
        found["user_message"] = f"Connected - new messages arrive live. Still loading old history ({found.get('message') or 'syncing'})."
    else:
        found["user_message"] = "Connected and fully synced - new messages arrive the moment they are sent."

    return _json(found)


@mcp.tool()
async def get_qr_code() -> str:
    """Get QR code for WhatsApp authentication. Returns base64 encoded QR image if not authenticated."""
    wa = get_client()
    return _json(await wa.get_qr_code())


@mcp.tool()
async def search_contacts(query: str) -> str:
    """Search contacts by name or phone number. Also returns group memberships for each match.

    Args:
        query: Search string to match against contact names or numbers.
    """
    if isinstance(query, dict):
        query = query.get("query", query.get("q", str(query)))

    query = str(query).strip()
    wa = get_client()

    # knowledge.resolved() awaits wa.search_contacts (an async method) via inspect.isawaitable,
    # SO THE COROUTINE IS NEVER RETURNED UN-AWAITED.
    result, remembered = await knowledge.resolved(query, "whatsapp", wa.search_contacts)

    if remembered:
        # SIGNAL TO THE MODEL THIS CONTACT WAS ALREADY CONFIRMED — NO NEED TO RE-ASK.
        return _json({"remembered": True, "contacts": [{"name": result}]})

    # AN EMPTY LIST READS AS NOTHING TO GO ON, AND NOTHING TO GO ON IS WHERE A NAME OFF THE
    # LAST FEW MINUTES GETS PUT IN ITS PLACE. SAY WHOSE NAME FAILED AND WHAT TO DO INSTEAD.
    if not result:
        return NOBODY.format(name=query)

    return _json(result)


@mcp.tool()
async def remember_contact(said: str, means: str) -> str:
    """Remember that when the person says 'said', they mean the
    WhatsApp contact 'means'. Only call this once, right after a
    contact search failed for 'said' and the person then directly
    confirmed 'means' as correct, which worked."""
    knowledge.remember_fact(said, "whatsapp", means)
    return ok({"remembered": True, "said": said, "means": means})

@mcp.tool()
async def get_chats(days: Optional[int] = None) -> str:
    """Get WhatsApp chats list with last-message previews. All returned timestamps are in UTC.

    Each chat's "lastMessage" is its newest line, and "lastMessageFromMe" says who wrote it:
    true means the USER sent it, so it is his own message and not one from that contact.

    Use this when the user explicitly asks to SEE or LIST their chats (e.g. "show my chats",
    "list all conversations"), and to read the real names when a lookup by name came back empty:
    a misheard name is not in the list, so find the one that is plainly the same person or group
    said differently, and call the tool that failed again with that name.

    NEVER use this for: "unread messages", "new messages", "any messages?", "did someone message me?" - use get_unread_messages instead.
    NEVER call this after get_latest_received_message or get_unread_messages - those tools already give the complete answer.

    Args:
        days: Only return chats with activity in the last N days. Returns all if not set.
    """
    wa = get_client()
    sync_status = await check_sync_status(wa)
    if sync_status:
        return _json({
            "sync_in_progress": True,
            "message": sync_status.get("message"),
            "user_message": f"WhatsApp sync in progress ({sync_status.get('message', 'syncing')}). Please wait 30-60 seconds and try again."
        })

    result = await wa.get_chats()
    if not result:
        pass
        await wa.sync()
        result = await wa.get_chats()

    if days is not None and isinstance(result, list):
        cutoff = time.time() - (days * 86400)
        result = [chat for chat in result if chat.get("timestamp", 0) >= cutoff]

    return _json(result)

@mcp.tool()
async def get_messages(contact: list[str], limit: int = 10, order_newest: bool = True,  received_only: bool = False) -> str:
    """Get messages from one or more contacts or groups. Pass a list - use a one-item list for a single contact, e.g. ["john"]. Returns a list for single contact, or a dict keyed by name for multiple. All returned timestamps are in UTC (ISO 8601 "time" field and Unix "timestamp" field). Convert to the user's timezone before displaying.

    A message with a photo, video or voice note on it comes back with "localPath": that file is
    already on this computer, at that exact path. To show it, open that path. Never go looking
    for it on the disk and never guess where WhatsApp keeps its files.

    Args:
        contact: List of contact names, phone numbers, or group names. For a single contact pass a one-item list: ["john"]
        limit: Number of messages to return per contact (default: 10).
        order_newest: If True (default), returns newest messages first. If False, returns oldest messages first.
        received_only: If True, only return messages received from the contact (excludes messages you sent). Defaults to False.

    "The last message FROM someone" means the last one THEY sent. Pass received_only=True
    for that: the newest line in a chat is often one the user sent himself, and reporting
    his own words back to him as theirs is wrong. Every message says whose it is in
    "fromMe" - true means the user wrote it. Never call a message theirs when fromMe is true.
    """
    order = "newest" if order_newest else "oldest"
    wa = get_client()
    if isinstance(contact, list):
        contacts = [c.strip() for c in contact if c.strip()]
    else:
        contacts = [c.strip() for c in contact.split(",") if c.strip()]

    async def fetch_one(c: str):
        result = await wa.get_messages(c, limit, order=order, received_only=received_only)

        # A FAILURE SAYS SO NOW. IT MUST NOT BE TRADED FOR A SYNC MESSAGE THAT
        # GUESSES AT A DIFFERENT CAUSE.
        if isinstance(result, dict) and "error" in result:
            return c, result

        if not result:
            sync_status = await check_sync_status(wa)
            if sync_status:
                return c, [{"syncing": True, "contact": c, "message": f"Contact '{c}' not found yet - sync in progress."}]
        return c, result

    results = await asyncio.gather(*[fetch_one(c) for c in contacts])
    data = {c: msgs for c, msgs in results}
    return _json(data[contacts[0]] if len(contacts) == 1 else data)



@mcp.tool()
async def download_media(message_id: str, chat: CoercedStr = "") -> str:
    """Fetch the photo, video, voice note or document attached to a message onto this computer, and say where it landed.

    Usually you do not need this. Media arrives already downloaded, and any message
    holding some comes back with a "localPath" saying exactly where that file is -
    open or read that path directly. Only call this for a message whose
    "downloadable" is true and which has no "localPath" yet.

    Args:
        message_id: The "id" field of the message the media is attached to.
        chat: Contact or group name that message is in. Helps find it when the file is not on disk yet.
    """
    message_id = str(message_id or "").strip()

    # AN ID WAS ONCE PASSED IN SHORTENED WITH AN ELLIPSIS, WHICH CAN ONLY EVER MISS.
    if not message_id or "..." in message_id or "\u2026" in message_id:
        return _json({
            "error": "That is not a whole message id. Pass the message's \"id\" field exactly as it "
                     "came back, with nothing trimmed off it.",
        })

    wa = get_client()
    return _json(await wa.download_media_from_message(message_id, chat=chat))


@mcp.tool()
async def get_unread_messages(include_archived: bool = True) -> str:
    """Check for unread WhatsApp messages across all chats including archived ones.
    Use this for: "any unread messages?", "any new messages?", "did anyone message me?",
    "what's new on WhatsApp?", "check WhatsApp", "unread messages".
    Returns chats sorted by unread count - this is the COMPLETE answer.

    "lastMessage" is the chat's newest line and "lastMessageFromMe" says who wrote it.
    When that is true the last line is one the USER sent, so it is not an unread message
    from them and must never be described as something they said.

    This says how many are unread and what the last line of each chat is. It does NOT
    contain the unread messages themselves - to say what they actually are, call
    get_messages for that contact with received_only=True. Never invent their contents.

    Each chat carries "bodiesHeld": how many received messages are actually on this
    computer for it. When that is 0 the count came from the phone but the messages have
    not synced down, and get_messages will return nothing for that chat. An empty result
    there does NOT mean the chat has nothing unread - say the messages have not arrived
    yet.

    "unreadCount" is a badge off the phone, not a count of messages. It survives an old
    sync and only ever climbs, so it can claim far more than the chat holds.
    "heldSinceMine" is how many received messages are here that are newer than the last
    line the USER sent - the most the badge can honestly mean. When "count_warning" is
    present, say the held number for those chats, never the badge, and never add the
    badges into one total.

    Args:
        include_archived: If True (default), also include archived chats with unread messages.
    """
    wa = get_client()
    chats = await wa.get_chats()
    if not isinstance(chats, list):
        # THE READER SAYS WHY IT FAILED NOW, AND THAT REASON IS WORTH MORE THAN
        # A FLAT "COULD NOT FETCH CHATS".
        return _json(chats if isinstance(chats, dict) else {"error": "Could not fetch chats"})

    unread = [
        {
            "name": c.get("name") or c.get("id"),
            "unreadCount": c["unreadCount"],
            "lastMessage": c.get("lastMessage", ""),
            # WHOSE LAST LINE IT IS, SO HIS OWN WORDS ARE NEVER READ BACK AS THEIRS.
            "lastMessageFromMe": bool(c.get("lastMessageFromMe")),
            "lastMessageFrom": c.get("lastMessageFrom") or "",
            "isGroup": c.get("isGroup", False),
            "archived": c.get("archived", False),
            # THE COUNT COMES FROM THE PHONE AND THE BODIES ARRIVE SEPARATELY, SO A
            # CHAT CAN BE COUNTED UNREAD WITH NOTHING HERE TO SHOW FOR IT.
            "bodiesHeld": c.get("receivedHeld", 0),
            # RECEIVED SINCE HIS OWN LAST LINE: THE MOST THE BADGE CAN HONESTLY MEAN.
            "heldSinceMine": c.get("heldSinceMine", 0),
        }
        for c in chats
        if c.get("unreadCount", 0) > 0 and (include_archived or not c.get("archived"))
    ]

    unread.sort(key=lambda x: -x["unreadCount"])

    empty = [c["name"] for c in unread if not c["bodiesHeld"]]

    # A BADGE FROM AN OLD SYNC OUTLIVES THE MESSAGES IT COUNTED, SO A CHAT CAN CLAIM
    # FIFTY-ONE WITH NINE LINES BEHIND IT. THE HELD COUNT IS THE ONE THAT WAS CHECKED.
    stale = [
        c for c in unread
        if c["bodiesHeld"] and c["unreadCount"] > c["heldSinceMine"]
    ]

    answer = {
        "total_unread_chats": len(unread),
        "total_held_here": sum(c["heldSinceMine"] for c in unread),
        "archived_chats_with_unread": sum(1 for c in unread if c["archived"]),
        "unread_chats": unread,
    }

    if not stale:
        # NOTHING IS STALE, SO THE BADGES ADD UP TO SOMETHING TRUE AND CAN BE SAID.
        answer["total_unread_messages"] = sum(c["unreadCount"] for c in unread)

    if stale:
        worst = ", ".join(
            f"{c['name']} says {c['unreadCount']} with {c['heldSinceMine']} here"
            for c in stale
        )
        answer["count_warning"] = (
            "These chats claim more unread than there are messages behind them: "
            f"{worst}. The badge came off the phone in an old sync and was never "
            "cleared, so it is not a message count. Say the smaller, held number for "
            "these chats. Never say the badge total out loud, as a total or beside the "
            "held one: there are not that many messages. Say how many chats, and the "
            "held count."
        )

    if empty:
        answer["note"] = (
            "These chats are counted unread but their messages have not been synced down "
            f"yet: {', '.join(empty)}. get_messages will come back empty for them. That is "
            "not the same as having nothing unread — say the messages have not arrived on "
            "this computer yet, and never report these chats as having no unread messages."
        )

    return _json(answer)




@mcp.tool()
async def get_latest_received_message(include_groups: bool = False) -> str:
    """Get the single most recent message SOMEONE ELSE sent you on WhatsApp, with who sent it and when.
    Use this for: "what was the last message I received?", "who messaged me last?", "what's the latest message?",
    "read me the last message". This is the COMPLETE answer - do not follow it with get_chats or get_messages.

    Messages you sent yourself are never returned, including the ones in your own "Message yourself" chat.
    The timestamp is UTC - convert to the user's timezone before saying it.

    A message with a photo, video or voice note on it comes back with "localPath": that file is
    already on this computer, at that exact path. To show it, open that path. Never go looking
    for it on the disk and never guess where WhatsApp keeps its files.

    Args:
        include_groups: If True, a group message can be the answer. Defaults to False, direct chats only.
    """
    wa = get_client()
    result = await wa.get_latest_received_message(include_groups=include_groups)

    if isinstance(result, dict) and result.get("error"):
        sync_status = await check_sync_status(wa)
        if sync_status:
            return _json({
                "sync_in_progress": True,
                "user_message": f"WhatsApp sync in progress ({sync_status.get('message', 'syncing')}). Please wait 30-60 seconds and try again.",
            })

    return _json(result)


@mcp.tool()
async def query_messages(
    group: CoercedStr = "",
    contact: CoercedStr = "",
    sender: CoercedStr = "",
    limit: int = 5,
    from_me: Optional[bool] = None,
    date: CoercedStr = "",
    oldest_first: bool = False,
) -> str:
    """Search WhatsApp messages with filters. Use for: "what did X send me?", "messages from Y in Z group", "last message in group", "recent messages". All filtering happens in-memory - single call, instant results.

    Call this tool ONCE with best-guess partial names. Do NOT search groups or contacts first:
    a partial name matches on its own, so "zookie" finds "Zookie bhai" and "rasool" finds "Rasool Khan".
    Only when nothing comes back, read the real names with get_chats and call again with the right one.

    Use ONLY the relevant parameter - group OR contact, not both:
    - Group chat message     -> fill "group", leave "contact" and "sender" empty
    - Sender inside a group  -> fill "group" + "sender", leave "contact" empty
    - "What did X say/send?" (direct chat, received) -> fill "sender" only (auto-excludes your own messages)
    - Messages I sent to X   -> fill "contact", from_me=true
    - All messages in DM     -> fill "contact", leave "sender" empty

    RULE: For "last/latest message from X" or "what did X send/say" - use sender="X" with NO group and NO contact.
    "sender" without a group looks in the direct chat with X and automatically excludes messages you sent.
    Only use contact= when you explicitly need your own sent messages (from_me=true) or all messages in a DM.

    IMPORTANT: parameter values must be SHORT NAMES ONLY (1-3 words). NEVER put sentences or reasoning.

    A message with a photo, video or voice note on it comes back with "localPath": that file is
    already on this computer, at that exact path. To show it, open that path. Never go looking
    for it on the disk and never guess where WhatsApp keeps its files.

    Examples:
    - "last message from Ram in Just Mumbai group"          -> group="just mumbai", sender="ram", limit=1
    - "first message in Dhurandhar group from Siddu today"  -> group="dhurandhar", sender="siddu", date="today", oldest_first=true, limit=1
    - "messages I sent to User"                             -> contact="user", from_me=true
    - "last message Rasool sent in Zookie Bhai group"       -> group="zookie", sender="rasool", limit=1
    - "last message received from Jaswanth / what did Athul say last" -> sender="jaswanth", limit=1
    - "yesterday's messages from User in WhatsApp"          -> sender="user", date="yesterday"
    - "first message today in Just Mumbai"                  -> group="just mumbai", date="today", oldest_first=true, limit=1

    Args:
        group: Partial group name - 1 to 3 words (e.g. "just mumbai", "fans sathi"). Leave empty for DMs.
        contact: Partial contact name for direct messages - 1 to 2 words. Use only for sent messages (from_me=true) or reading all DM messages. Do NOT use for "what did X say/send" - use sender= instead.
        sender: Partial name of the person who sent the message. For direct chats (no group), use this alone - it looks in the direct chat and auto-excludes your own messages. For groups, combine with group=.
        limit: Number of messages to return (default 5, max 50).
        from_me: true = only messages you sent, false = only messages you received, omit for both. Leave unset when using sender= (already implied).
        date: "today", "yesterday", or "YYYY-MM-DD". Leave empty for all dates.
        oldest_first: Set to true to get the earliest/first messages. Default false returns newest/latest messages.
    """
    import re as _re
    KNOWN_NON_NAMES = {"whatsapp", "mcp", "server", "tool", "bridge", "api", "null", "none", "n/a", "na"}

    def _s(v):
        if isinstance(v, (dict, list)): return ""
        return " ".join(str(v).split())

    group, contact, sender, date = _s(group), _s(contact), _s(sender), _s(date)
    order = "oldest" if oldest_first else "newest"

    chat = group if group else contact

    # BOTH FIELDS SET AND NO SENDER MEANS THE AGENT PUT THE PERSON IN THE WRONG ONE.
    if group and contact and not sender:
        sender = contact
        contact = ""

    if from_me is True:
        from_me_str = "true"
    elif from_me is False:
        from_me_str = "false"
    else:
        from_me_str = ""
    if date and not (date in ("today", "yesterday") or _re.fullmatch(r"\d{4}-\d{2}-\d{2}", date)):
        date = ""
    if sender.lower() in KNOWN_NON_NAMES:
        sender = ""

    # A WHOLE SENTENCE IN THE FIELD. THE NAME IS DUG OUT OF IT BEFORE GIVING UP.
    orig_chat, orig_sender = chat, sender
    chat_garbage = len(chat) > 80 or chat.count(" ") > 5
    sender_garbage = len(sender) > 60 or sender.count(" ") > 4

    if chat_garbage:
        m = _re.search(r"[\"']([^\"']{2,60})[\"']", orig_chat)
        if m:
            chat = _s(m.group(1))
            chat_garbage = len(chat) > 80 or chat.count(" ") > 5
        if chat_garbage:
            m = _re.search(r'\bin\s+(?:the\s+)?([A-Za-z0-9@&\s.\-]{3,40}?)\s*(?:group|chat)?\s*(?:[,.\s]|$)', orig_chat, _re.IGNORECASE)
            if m:
                chat = _s(m.group(1).strip().rstrip(',.'))
                chat_garbage = len(chat) > 80 or chat.count(" ") > 5

    if sender_garbage:
        m = _re.search(r'\b(?:from|by)\s+([A-Za-z][A-Za-z0-9\s]{1,25}?)\s+(?:in\b|group\b|sent\b|at\b|who\b|the\b)', orig_sender, _re.IGNORECASE)
        if m and "@" not in m.group(1):
            sender = _s(m.group(1).strip())
            sender_garbage = len(sender) > 60 or sender.count(" ") > 4

    if chat_garbage or sender_garbage:
        bad = []
        if chat_garbage:
            bad.append(f"group/contact='{orig_chat[:40]}...' (too long - use 1-3 word partial name)")
        if sender_garbage:
            bad.append(f"sender='{orig_sender[:40]}...' (too long - use 1-2 word partial name)")
        return _json({
            "error": "Parameters contain full sentences instead of short names. Re-call with short names only.",
            "bad_params": bad,
            "correct_example": {
                "group": "<2-3 word partial group name, e.g. 'fans sathi'>",
                "contact": "<1-2 word contact name for DMs, e.g. 'user'>",
                "sender": "<1-2 word sender name, e.g. 'deekshit'>",
                "limit": limit,
                "order": order,
            }
        })
    wa = get_client()
    result = await wa.query_messages(chat=chat, sender=sender, limit=limit, from_me=from_me_str, date=date, order=order)

    # NOTHING BACK WITH BOTH FIELDS FILLED: THE OTHER ONE WAS PROBABLY THE CHAT.
    if isinstance(result, list) and len(result) == 0 and group and contact:
        fallback_chat = contact if chat == group else group
        result2 = await wa.query_messages(chat=fallback_chat, sender=sender, limit=limit, from_me=from_me_str, date=date, order=order)
        if isinstance(result2, list) and len(result2) > 0:
            result = result2

    # FALLING BACK IN HERE SPARES THE MODEL A SECOND ROUND TRIP TO PICK ANOTHER TOOL.
    is_error = isinstance(result, dict) and "error" in result
    if is_error and sender and not chat:
        fallback = await wa.get_messages(sender, limit, order=order, received_only=(from_me_str == "false"))
        if fallback:
            result = fallback

    return _json(result)


# AS MANY COPIES OF ONE MESSAGE AS ANYBODY HAS A REASON TO SEND, AND HOW LONG TO
# WAIT BETWEEN THEM SO WHATSAPP READS IT AS A PERSON RATHER THAN A SCRIPT.
MOST_COPIES = 100

BETWEEN_COPIES = 0.4


async def getting_on(ctx, done, whole, said):
    """SAY HOW FAR ALONG WE ARE, IF ANYBODY IS LISTENING. NOTHING RIDES ON IT ARRIVING."""
    if ctx is None:
        return

    try:
        await ctx.report_progress(done, whole, said)
    except Exception:
        pass


def repeats(times):
    """HOW MANY COPIES TO ACTUALLY SEND, OUT OF WHATEVER THE MODEL PUT IN THE FIELD."""
    try:
        wanted = int(times)
    except (TypeError, ValueError):
        return 1

    return max(1, min(wanted, MOST_COPIES))


@mcp.tool()
async def send_message(
    recipients: list[str], message: str, times: int = 1, ctx: Context = None
) -> str:
    """Send a text message to one or more contacts or groups.

    Args:
        recipients: List of contact names, phone numbers, or group names.
                    For a single contact pass a one-item list: ["john"]
        message: The text message to send. Write it out as a plain finished
                 string — never an expression like "hi" * 3 or "hi".repeat(3).
        times: How many separate copies of it to send to each recipient, up to
               100. Use this to send the same text over and over rather than
               repeating it inside message or calling this tool again and again.
    """
    wa = get_client()
    if isinstance(recipients, str):
        recipients = [recipients]
    results = {}
    copies = repeats(times)
    whole = len(recipients) * copies
    done = 0

    for recipient in recipients:
        resolved = knowledge.recall(recipient, "whatsapp") or recipient
        sent = []

        for copy in range(copies):
            result = await wa.send_message(resolved, message)

            if await should_sync_on_error(result):
                await wa.sync()
                result = await wa.send_message(resolved, message)

            sent.append(result)
            done += 1

            # A LONG ERRAND SAYS SO AS IT GOES, AND EVERY WORD OF IT PUTS HAPPY'S
            # WHOLE TIMEOUT BACK. A SEND THAT NEVER SPOKE WOULD BE GIVEN UP ON.
            await getting_on(ctx, done, whole, f"sent {done} of {whole} to {recipient}")

            # WHATSAPP TREATS A BURST WITH NO GAP IN IT AS A ROBOT, AND SAYS SO BY
            # DROPPING THE ACCOUNT.
            if copy + 1 < copies:
                await asyncio.sleep(BETWEEN_COPIES)

        results[recipient] = sent[0] if copies == 1 else tally(sent)

    return _json(results)


def tally(sent):
    """A HUNDRED MESSAGE IDS TELL NOBODY ANYTHING. HOW MANY LANDED DOES."""
    failed = [each for each in sent if isinstance(each, dict) and "error" in each]

    if not failed:
        return {"sent": len(sent)}

    return {
        "sent": len(sent) - len(failed),
        "failed": len(failed),
        "why": failed[0].get("error"),
    }


@mcp.tool()
async def send_group_message(groups: list[str], message: str) -> str:
    """Send to a named group chat only, never to a person.

    This is for a group by its name: the PG group, the family group, a team.
    A person, a phone number, or a name that is somebody rather than somewhere,
    is send_message instead, even when several people are named at once.

    Args:
        groups: Group name(s) to send to. Can be a single name or a list.
        message: The text message to send.
    """
    wa = get_client()
    if isinstance(groups, str):
        groups = [groups]
    results = {}
    synced = False

    for group in groups:
        resolved = knowledge.recall(group, "whatsapp") or group
        result = await wa.send_group_message(resolved, message)

        if await should_sync_on_error(result) and not synced:
            await wa.sync()
            synced = True
            result = await wa.send_group_message(resolved, message)

        results[group] = result

    return _json(results)


@mcp.tool()
async def send_media_message(recipients: list[str], source: str, caption: str = "") -> str:
    """Send a media file (image, video, document, PDF, etc.) to one or more contacts or groups.

    Args:
        recipients: Contact name(s), phone number(s), or group name(s) to send to.
        source: File path or URL of the media to send.
        caption: Optional text caption to include with the media.
    """
    wa = get_client()
    if isinstance(recipients, str):
        recipients = [recipients]
    results = {}

    for recipient in recipients:
        resolved = knowledge.recall(recipient, "whatsapp") or recipient
        result = await wa.send_media_message(resolved, source, caption)

        if await should_sync_on_error(result):
            await wa.sync()
            result = await wa.send_media_message(resolved, source, caption)

            if await should_sync_on_error(result):
                return _json({
                    "error": f"Contact '{recipient}' not found. Ask user for phone number."
                })

        results[recipient] = result

    return _json(results)


if __name__ == "__main__":
    mcp.run()