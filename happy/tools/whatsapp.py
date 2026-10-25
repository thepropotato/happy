"""WhatsApp for local models: a few plain tools over the WhatsApp MCP server, with the searching done here."""

import json
import re
import time
from typing import Annotated

from happy.integrations.mcp import hub
from happy.tools import report, tool


def connected():
    return hub.get("whatsapp") is not None


async def ask(name, **args):
    result = await hub.call("whatsapp", name, {k: v for k, v in args.items() if v not in (None, "", [])})
    text = result if isinstance(result, str) else result.note
    try:
        return json.loads(text)
    except ValueError:
        return text


def when(message):
    stamp = message.get("timestamp")
    if not stamp:
        return message.get("time", "")[:16]
    age = time.time() - stamp
    fmt = "%I:%M %p" if age < 86400 else "%a %d %b, %I:%M %p" if age < 86400 * 300 else "%d %b %Y"
    return time.strftime(fmt, time.localtime(stamp)).lstrip("0")


def line(message, with_chat=True):
    who = "Me" if message.get("fromMe") else (message.get("from") or "").split(" (")[0] or "Them"
    # A PHOTO NOT DOWNLOADED YET STILL HAS ITS TYPE; WITHOUT IT, IT READ AS AN EMPTY MESSAGE.
    kind = message.get("mediaType") or (message.get("type") if message.get("type") not in (None, "chat", "text") else None)
    body = message.get("body") or ""
    if kind and body != f"[{kind}]":
        body = f"[{kind}] {body}".strip()
    if message.get("filename"):
        body += f" (file {message['filename']})"
    where = f" in {message.get('chatName')}" if with_chat and message.get("chatName") else ""
    return f"[{when(message)}{where}] {who}: {body}"


def listing(messages, with_chat=True):
    if isinstance(messages, str):
        return messages
    if isinstance(messages, dict):
        found = messages.get("messages") or messages.get("results")
        if found is None:
            return messages.get("user_message") or messages.get("message") or json.dumps(messages)[:1500]
        messages = found
    if not messages:
        return "No messages found."
    return "\n".join(line(m, with_chat) for m in messages)


@tool(say="Checking WhatsApp.", label="Checking WhatsApp", local_only=True, needs=connected)
async def whatsapp_unread():
    """Who has sent unread WhatsApp messages, and the latest from each."""
    data = await ask("get_unread_messages")
    if not isinstance(data, dict):
        return data
    chats = data.get("unread_chats") or []
    if not chats:
        return "No unread WhatsApp messages."
    rows = [f"{c['name']}: {c['unread']} unread, last from {c.get('lastMessageFrom') or c['name']}: {c.get('lastMessage', '')}"
            for c in chats if not c.get("pollVotesOnly")]
    return f"{data.get('unread_messages', '?')} unread messages in {len(rows)} chats:\n" + "\n".join(rows)


def bridge(path, **params):
    """A read straight from the WhatsApp bridge, for what the MCP server has no tool for."""
    import httpx

    from happy.integrations import whatsapp

    try:
        return httpx.get(f"{whatsapp.BASE}{path}", params=params, timeout=15).json()
    except (httpx.HTTPError, ValueError) as error:
        return f"Could not reach WhatsApp: {error}"


@tool(say="Opening that chat.", label="Reading the chat with {chat}", local_only=True, needs=connected)
async def whatsapp_read(
    chat: Annotated[str, "person or group name, a short partial name is fine; empty for the newest messages from anyone"] = "",
    count: Annotated[int, "how many recent messages"] = 10,
    people_only: Annotated[bool, "with no chat: true to leave groups out"] = False,
):
    """Read what someone said: the latest messages in one WhatsApp chat, newest last. With no chat, the newest messages received across all chats."""
    if not chat.strip():
        import asyncio

        # TEN IS THE DEFAULT FOR ONE CHAT; ACROSS EVERY CHAT "THE LAST MESSAGE" WANTS ONLY THE NEWEST FEW.
        wanted = 3 if count == 10 else max(1, min(count, 10))
        found = await asyncio.to_thread(bridge, "/latest", limit=wanted, people="1" if people_only else "0")
        if isinstance(found, str) or not found:
            return found or "No messages received yet."
        return "Newest received, newest first:\n" + "\n".join(
            line(m) + (" (group)" if m.get("isGroup") else "") for m in found)
    data = await ask("get_messages", contact=[chat], limit=max(1, min(count, 50)))
    if isinstance(data, dict) and isinstance(data.get(chat), list):
        data = data[chat]
    elif isinstance(data, dict) and len(data) == 1 and isinstance(next(iter(data.values())), list):
        data = next(iter(data.values()))
    if isinstance(data, list):
        data = sorted(data, key=lambda m: m.get("timestamp") or 0)
    return listing(data, with_chat=False)


@tool(say="Counting up your chats.", label="WhatsApp stats", local_only=True, needs=connected)
async def whatsapp_stats():
    """Numbers and patterns across all of WhatsApp: how many chats and groups, unread, today's and this week's activity, busiest chats, the biggest groups, and who is waiting on a reply."""
    import asyncio

    data = await asyncio.to_thread(bridge, "/stats")
    if isinstance(data, str):
        return data
    busiest = ", ".join(f"{b['name']}{' (group)' if b['isGroup'] else ''} {b['messages']}" for b in data["busiest_this_week"]) or "none"
    waiting = "; ".join(f"{w['name']} ({when(w)}): {w['said'] or '[' + (w.get('kind') or 'message') + ']'}"
                        for w in data["waiting_on_your_reply"]) or "nobody"
    biggest = ", ".join(f"{g['name']} ({g['members']} members)" for g in data["biggest_groups"]) or "none"
    return (f"{data['chats']} chats: {data['people_chats']} with people and {data['groups']} groups, {data['archived']} archived. "
            f"{data['contacts']} contacts. Unread: {data['unread_messages']} messages in {data['unread_chats']} chats.\n"
            f"Today: {data['today']['received']} received and {data['today']['sent']} sent, across {data['today']['chats']} chats. "
            f"This week: {data['this_week']['received']} received, {data['this_week']['sent']} sent.\n"
            f"Busiest this week (messages): {busiest}.\nWaiting on your reply: {waiting}.\nBiggest groups: {biggest}.\n"
            f"Counted from {data['messages_synced']} messages synced since {data['synced_since']}.")


@tool(say="Searching your chats.", label="Searching WhatsApp for {words}", local_only=True, needs=connected)
async def whatsapp_search(
    words: Annotated[str, "words that appear in the message; empty for any"] = "",
    chat: Annotated[str, "limit to one person or group"] = "",
    sent_by_me: Annotated[bool, "true for only my messages, false for only theirs"] = None,
    kind: Annotated[str, "document, image, video or audio, to find a file"] = "",
    since: Annotated[str, "YYYY-MM-DD"] = "",
    count: int = 10,
):
    """Search WhatsApp messages by words, person, who sent them, file type or date."""
    data = await ask("query_messages", text=words, contact=chat, from_me=sent_by_me, kind=kind, since=since,
                     limit=max(1, min(count, 40)))
    return listing(data)


DETECTORS = {
    "address": re.compile(
        r"(?i)\b(?:flat|door|house|plot|h\.?\s?no|d\.?\s?no|apartment|apt|floor|block|street|st\b|road|rd\b|lane|nagar|colony|"
        r"layout|sector|cross|main|avenue|ave\b|near|opp|beside|village|mandal|district|dist\b|pin|zip|suite|building|tower|residency|enclave|phase)"),
    "phone": re.compile(r"(?<!\d)(?:\+?\d[\d\s-]{8,}\d)(?!\d)"),
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    "link": re.compile(r"https?://\S+"),
    "location": re.compile(r"(?i)maps\.(?:app\.)?goo|google\.com/maps|location:|\b-?\d{1,3}\.\d{4,},\s*-?\d{1,3}\.\d{4,}"),
    "account": re.compile(r"(?i)\b(?:a/?c|account|ifsc|upi|iban|swift)\b"),
}
SYNONYMS = {"address": ["address", "home", "house", "where i live", "location", "place"],
            "phone": ["phone", "number", "mobile", "contact number"], "email": ["email", "mail id", "e-mail"],
            "link": ["link", "url", "website"], "location": ["location", "pin", "maps"],
            "account": ["account", "bank", "ifsc", "upi"]}


def kind_of(what):
    lowered = what.lower()
    for kind, words in SYNONYMS.items():
        if any(w in lowered for w in words):
            return kind
    return None


def address_score(body):
    hits = len(DETECTORS["address"].findall(body))
    pin = 2 if re.search(r"(?<!\d)\d{6}(?!\d)|(?<!\d)\d{5}(?:-\d{4})?(?!\d)", body) else 0
    numbers = 1 if re.search(r"\d+[-/]\d+|\b\d{1,4}[a-z]?\b", body, re.I) else 0
    commas = min(body.count(",") + body.count("\n"), 4) * 0.5
    sized = 1 if 20 <= len(body) <= 400 else -2
    return hits * 1.5 + pin + numbers + commas + sized


def score(message, kind, words):
    body = message.get("body") or ""
    if not body:
        return 0
    if kind == "address":
        value = address_score(body)
        return value if value >= 4 else 0
    if kind:
        return 3 if DETECTORS[kind].search(body) else 0
    lowered = body.lower()
    return sum(1 for w in words if w in lowered) / max(1, len(words)) * 3


CLUES = {
    "address": ["road", "rd ", "street", "flat", "nagar", "colony", "layout", "apartment", "apt", "floor", "house",
                "door no", "h.no", "d.no", "plot", "sector", "block", "near", "opp", "residency", "enclave", "pin",
                "lane", "cross", "main", "village", "district", "avenue", "suite", "building", "tower", "phase"],
    "phone": ["+91", "+1", "+44", "number", "phone", "mobile", "call me", "contact"],
    "email": ["@gmail", "@yahoo", "@outlook", "@hotmail", "@icloud", ".com", "mail"],
    "link": ["http", "www."],
    "location": ["maps.", "goo.gl", "location", "pin"],
    "account": ["ifsc", "a/c", "account", "upi", "@ok", "@ybl", "@paytm", "bank"],
}


async def gather(clues, person, sent_by_me):
    """Every message a set of word searches turns up, since one search hands back at most 50."""
    import asyncio

    where = {"contact": person} if person else {}
    asks = [ask("query_messages", from_me=sent_by_me, limit=50, **where)]
    asks += [ask("query_messages", text=clue, from_me=sent_by_me, limit=50, **where) for clue in clues]
    seen, found = set(), []
    for batch in await asyncio.gather(*asks):
        for message in batch if isinstance(batch, list) else []:
            key = message.get("id") or (message.get("timestamp"), message.get("body"))
            if key not in seen:
                seen.add(key)
                found.append(message)
    return found


@tool(say="Looking through your chats for that.", label="Searching WhatsApp for {what}", needs=connected)
async def whatsapp_find(
    what: Annotated[str, "what to find, like 'my address', 'phone number', 'the wifi password' or 'flight details'"],
    people: Annotated[list[str], "people or groups it was sent to or from; empty searches every chat"] = None,
    sent_by_me: Annotated[bool, "true if I sent it, false if they sent it"] = None,
):
    """Find a piece of information anywhere in WhatsApp, like an address, number or link, even when the message never uses that word. Searches every chat when no one is named. Not for what someone said lately: read their chat for that."""
    kind = kind_of(what)
    words = [w for w in re.findall(r"\w+", what.lower()) if len(w) > 2 and w not in (
        "the", "and", "that", "sent", "send", "for", "from", "with", "about", "message", "my", "his", "her", "their")]
    clues = CLUES.get(kind, words)
    pools = []
    for person in people or [""]:
        report(f"Searching {person or 'every chat'}")
        pools.extend(await gather(clues, person, sent_by_me))
    if not pools and people:
        for person in people:
            pools.extend(await gather(clues, "", sent_by_me))
            break
    if not pools:
        return f"Found no messages{' with ' + ', '.join(people) if people else ''} to look through."
    ranked = sorted(((score(m, kind, words), m) for m in pools), key=lambda pair: (-pair[0], -(pair[1].get("timestamp") or 0)))
    best = [m for value, m in ranked if value > 0][:6]
    if not best:
        return f"Looked through {len(pools)} likely messages and found nothing that looks like {what}."
    return f"Best matches out of {len(pools)} likely messages:\n" + "\n".join(line(m) for m in best)


@tool(label="Looking up {name}", local_only=True, needs=connected)
async def whatsapp_contact(name: Annotated[str, "a name, or a relationship like dad or brother"]):
    """Look up a WhatsApp contact by name or nickname: their saved name, number, and the name on their WhatsApp profile ("profile")."""
    data = await ask("search_contacts", query=name)
    return data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)[:2000]


@tool(say="Getting their picture.", label="Showing {name}'s profile picture", local_only=True, needs=connected)
async def whatsapp_picture(name: Annotated[str, "the person, by name or number"]):
    """Show someone's WhatsApp profile picture (DP) on screen."""
    import asyncio

    import httpx

    from happy.integrations import whatsapp
    from happy.system import native

    try:
        reply = await asyncio.to_thread(httpx.get, f"{whatsapp.BASE}/profile-picture", params={"q": name}, timeout=25)
        data = reply.json()
    except (httpx.HTTPError, ValueError) as error:
        return f"Could not reach WhatsApp: {error}"
    if data.get("error"):
        return data["error"]
    if not data.get("picture"):
        return f"{data.get('name') or name} has {data.get('why') or 'no profile picture'}."
    native.open_path(data["picture"], app="Preview")
    return f"Opened {data.get('name') or name}'s profile picture in Preview."


@tool(say="Sending it.", label="Sending to {to} on WhatsApp", local_only=True, needs=connected)
async def whatsapp_send(
    to: Annotated[str, "the person or group, by name"],
    message: Annotated[str, "the exact words to send"],
    called: Annotated[str, "the relationship word they used for the person, like 'brother', 'mom' or 'boss', never the name; empty if they only gave a name"] = "",
):
    """Send a WhatsApp message."""
    data = await ask("send_message", recipients=[to], message=message)
    said = called.strip().lower().removeprefix("my ").strip()
    failed = (isinstance(data, str) and data.lower().startswith("error")) or (isinstance(data, dict) and (data.get("error") or data.get("success") is False))
    if said and said != to.strip().lower() and not failed:
        from happy.tools.notes import note

        # "MY BROTHER, JOHN DOE" SAID ONCE IS KEPT, SO TOMORROW "MY BROTHER" NEEDS NO EXPLAINING.
        note(f"'{said}' means {to.strip()} (their name in WhatsApp)")
        await hub.call("whatsapp", "remember_contact", {"said": said, "means": to.strip()})
    return data if isinstance(data, str) else json.dumps(data)[:800]


@tool(label="Remembering {said}", local_only=True, needs=connected)
async def whatsapp_remember(
    said: Annotated[str, "what they call the person, like dad"],
    means: Annotated[str, "the contact's name in WhatsApp"],
):
    """Remember who someone means by a nickname or relationship, for next time."""
    from happy.tools.notes import note

    result = await hub.call("whatsapp", "remember_contact", {"said": said, "means": means})
    # KEPT IN THE NOTES AS WELL, SO "MY BROTHER" IS KNOWN TO EVERY TOOL AND NOT ONLY TO WHATSAPP.
    note(f"'{said}' means {means} (their name in WhatsApp)")
    return result
