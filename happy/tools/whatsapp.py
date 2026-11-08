"""WhatsApp for local models: a few plain tools over the WhatsApp MCP server, with the searching done here."""

import json
import re
import time
from typing import Annotated

from happy.integrations.mcp import hub
from happy.tools import asked, report, said_lately, tool


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


def me():
    from happy.agent.prompt import owner

    return owner()


def line(message, with_chat=True, them="Them"):
    # THEIR OWN MESSAGES UNDER THEIR OWN NAME: "Me" WAS READ AS THE OTHER PERSON, AND THEIR WORDS WERE REPORTED AS THE REPLY.
    who = me() if message.get("fromMe") else (message.get("from") or "").split(" (")[0] or them
    # A PHOTO NOT DOWNLOADED YET STILL HAS ITS TYPE; WITHOUT IT, IT READ AS AN EMPTY MESSAGE.
    kind = message.get("mediaType") or (message.get("type") if message.get("type") not in (None, "chat", "text") else None)
    body = message.get("body") or ""
    if kind and body != f"[{kind}]":
        body = f"[{kind}] {body}".strip()
    # A STICKER'S FILE IS A HASH, AND "(file 3A5B…)" READ AS A FILE TO GO AND FIND.
    if message.get("filename") and kind != "sticker":
        body += f" (file {message['filename']})"
    where = f" in {message.get('chatName')}" if with_chat and message.get("chatName") else ""
    return f"[{when(message)}{where}] {who}: {body}"


def listing(messages, with_chat=True, them="Them"):
    if isinstance(messages, str):
        return messages
    if isinstance(messages, dict):
        found = messages.get("messages") or messages.get("results")
        if found is None:
            return messages.get("user_message") or messages.get("message") or json.dumps(messages)[:1500]
        messages = found
    if not messages:
        return "No messages found."
    return "\n".join(line(m, with_chat, them) for m in messages)


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


# A DAY IS READ FROM THIS MANY OF THE CHAT'S NEWEST MESSAGES, AND SHOWN IN THIS MANY CHARACTERS, NEWEST KEPT.
DAY_READ = 600
DAY_BUDGET = 3400


def day_bounds(day):
    """The start and end of a day they named, in their own time, or None when it is not a day."""
    import datetime

    word = day.strip().lower()
    today = datetime.date.today()
    if word == "today":
        date = today
    elif word == "yesterday":
        date = today - datetime.timedelta(days=1)
    else:
        try:
            date = datetime.date.fromisoformat(word)
        except ValueError:
            return None
    start = time.mktime(date.timetuple())
    return start, time.mktime((date + datetime.timedelta(days=1)).timetuple())


def without_reactions(messages):
    """The messages that say something, and how many reactions were left out: an emoji on a message is not a message."""
    said = [m for m in messages if m.get("type") != "reaction"]
    return said, len(messages) - len(said)


async def whole_day(chat, day):
    bounds = day_bounds(day)
    if bounds is None:
        return "Error: day is 'today', 'yesterday' or a date like 2026-10-26."
    data = await messages_in(chat, DAY_READ)
    if not isinstance(data, list) or not data:
        return listing(data, with_chat=False)
    data = sorted(data, key=lambda m: m.get("timestamp") or 0)
    chat = re.sub(r"\s*\([^()]*\)$", "", chat.strip()) or chat
    said, reactions = without_reactions([m for m in data if bounds[0] <= (m.get("timestamp") or 0) < bounds[1]])
    if not said:
        return f"Nothing was said in {chat} {day}" + (f", only {reactions} reactions." if reactions else ".")
    lines = [line(m, False, chat) for m in said]
    kept, size = [], 0
    for text in reversed(lines):
        size += len(text) + 1
        if size > DAY_BUDGET:
            break
        kept.insert(0, text)
    notes = [f"Chat with {chat}, {day}, oldest first: {len(said)} messages"
             + (f", and {reactions} reactions left out." if reactions else ".")
             + f" Lines from {me()} are {me()}'s own messages."]
    if len(data) == DAY_READ and (data[0].get("timestamp") or 0) > bounds[0]:
        notes.append(f"Only the last {len(said)} messages of that day were synced.")
    if len(kept) < len(lines):
        notes.append(f"The {len(lines) - len(kept)} earliest messages of that day are not shown; these are the latest.")
    return "\n".join(notes) + "\n\n" + "\n".join(kept)


@tool(say="Opening that chat.", label="Reading the chat with {chat}", local_only=True, needs=connected)
async def whatsapp_read(
    chat: Annotated[str, "person or group name, a short partial name is fine; empty for the newest messages from anyone"] = "",
    count: Annotated[int, "how many recent messages"] = 10,
    people_only: Annotated[bool, "with no chat: true to leave groups out"] = False,
    day: Annotated[str, "'today', 'yesterday' or YYYY-MM-DD for all of that day's messages in the chat; empty for the latest few"] = "",
):
    """Read what someone said on WhatsApp, or whether they wrote at all, like 'any word from Jane' or 'has Jane replied': the latest messages in their chat, newest last, and the last thing they wrote. With a day, everything said in the chat that day, for what a chat was about or a summary of it. With no chat, the newest messages received across all chats."""
    if not chat.strip():
        import asyncio

        # TEN IS THE DEFAULT FOR ONE CHAT; ACROSS EVERY CHAT "THE LAST MESSAGE" WANTS ONLY THE NEWEST FEW.
        wanted = 3 if count == 10 else max(1, min(count, 10))
        found = await asyncio.to_thread(bridge, "/latest", limit=wanted, people="1" if people_only else "0")
        if isinstance(found, str) or not found:
            return found or "No messages received yet."
        return "Newest received, newest first:\n" + "\n".join(
            line(m) + (" (group)" if m.get("isGroup") else "") for m in found)
    if day.strip():
        return await whole_day(chat, day)
    count = max(1, min(count, 50))
    # REACTIONS ARE FETCHED PAST AND LEFT OUT: HALF OF A GROUP'S LATEST FIFTY WERE EMOJI ON OTHER MESSAGES.
    data = await messages_in(chat, min(count * 3, 150))
    if not isinstance(data, list) or not data:
        return listing(data, with_chat=False)
    data = sorted(data, key=lambda m: m.get("timestamp") or 0)
    data = without_reactions(data)[0][-count:] or data[-1:]
    chat = re.sub(r"\s*\([^()]*\)$", "", chat.strip()) or chat
    theirs = [m for m in data if not m.get("fromMe")]
    if not theirs:
        older = await messages_in(chat, 1, received_only=True)
        theirs = older if isinstance(older, list) else []
    # WHO SAID THE LAST THING IS STATED, NOT LEFT TO BE WORKED OUT: "ANY WORD FROM HER" WAS ANSWERED WITH HIS OWN MESSAGE.
    notes = [f"Chat with {chat}, newest last. Lines from {me()} are {me()}'s own messages."]
    if data[-1].get("fromMe"):
        notes.append(f"The newest message is {me()}'s own, not {chat}'s.")
    notes.append(f"The last message from {chat}: {line(theirs[-1], False, chat)}" if theirs
                 else f"{chat} has sent nothing in the messages synced so far.")
    return "\n".join(notes) + "\n\n" + listing(data, with_chat=False, them=chat)


async def messages_in(chat, count, received_only=False):
    """One chat's newest messages, as a list when the chat was found, or what went wrong."""
    data = await ask("get_messages", contact=[chat], limit=count, received_only=received_only)
    if isinstance(data, dict) and isinstance(data.get(chat), list):
        return data[chat]
    if isinstance(data, dict) and len(data) == 1 and isinstance(next(iter(data.values())), list):
        return next(iter(data.values()))
    return data


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
    today = ", ".join(f"{b['name']}{' (group)' if b['isGroup'] else ''} {b['messages']}" for b in data.get("busiest_today", []))
    return (f"{data['chats']} chats: {data['people_chats']} with people and {data['groups']} groups, {data['archived']} archived. "
            f"{data['contacts']} contacts. Unread: {data['unread_messages']} messages in {data['unread_chats']} chats.\n"
            f"Today: {data['today']['received']} received and {data['today']['sent']} sent, across {data['today']['chats']} chats"
            f"{': ' + today if today else ''}. "
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
    # A KIND IT DOES NOT KNOW, LIKE "text", FILTERED EVERY MESSAGE OUT, AND THE EMPTY RESULT READ AS SILENCE.
    kind = kind if kind.strip().lower() in ("document", "image", "video", "audio") else ""
    data = await ask("query_messages", text=words, contact=chat, from_me=sent_by_me, kind=kind, since=since,
                     limit=max(1, min(count, 40)))
    if chat.strip() and not (data.get("messages") or data.get("results") if isinstance(data, dict) else data):
        # A NAME THAT MATCHES NOBODY IS SAID TO, WITH WHO IT COULD BE, AS A READ SAYS IT, NOT PASSED OFF AS NO MESSAGES.
        probe = await messages_in(chat, 1)
        if isinstance(probe, dict) and probe.get("error"):
            return json.dumps(probe, ensure_ascii=False)
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


ME = {"me", "myself", "here", "this chat", "my chat", "your chat"}


def named(person, said):
    """Whether they named the person, by a word of the name as speech spells it, or by a nickname kept for them."""
    import difflib

    from whatsapp_server import contacts, nearing

    heard = [nearing.squeeze(w) for w in nearing.words(said)]
    for part in (nearing.squeeze(w) for w in nearing.words(person)):
        # A SHORT WORD IS SAID EXACTLY OR NOT AT ALL: LOOSELY, "do" WAS "Doe" AND "any" WAS "Aunty".
        if any(part == word or min(len(part), len(word)) >= 4 and difflib.SequenceMatcher(None, part, word).ratio() >= 0.8
               for word in heard):
            return True
    kept = contacts.loaded_facts()
    return any(re.search(rf"\b{re.escape(nickname)}\b", said) for nickname, where in kept.items()
               if str(where.get("whatsapp", "")).lower() == person.strip().lower())


def wordless(args):
    """A send with nothing in it is the model guessing at a reply they have not given yet."""
    if (args.get("message") or "").strip() or (args.get("file") or "").strip():
        return None
    return ("Error: not sent: the message was empty. If they gave what to send, like a link or what to ask, write it in "
            "message and send again. If they have not said what to send, ask them what to say.")


# WHO A SEND IS WAITING ON THEIR ANSWER ABOUT, AND THE REQUEST THAT RAISED THE QUESTION, SINCE THE ANSWER COMES ON THE NEXT TURN.
waiting = {"words": None, "jids": set()}


def recipients(name):
    """Everyone the name could mean, or the reason nobody could be looked up."""
    import httpx

    from happy.integrations import whatsapp

    try:
        return httpx.get(f"{whatsapp.BASE}/recipients", params={"q": name}, timeout=30).raise_for_status().json()
    except (httpx.HTTPError, ValueError) as error:
        return f"Error: not sent: could not check who that is on WhatsApp: {error}"


def answering():
    """Whether this turn comes straight after the one that put a question to them."""
    from happy import history

    words = asked.get()
    if waiting["words"] is None or words == waiting["words"]:
        return False
    before = [turn["request"] for turn in history.recent(limit=3) if turn["request"] != words]
    return bool(before) and before[0] == waiting["words"]


def spelled(said, people):
    """Once asked, their answer as written decides, since matching two names that sound alike by sound would only ask again."""
    from whatsapp_server import nearing

    exact = [person for person in people if person["name"].lower() == said.lower()]
    words = set(nearing.words(said))
    literal = [person for person in people if words <= set(nearing.words(person["name"]))]
    return next((narrowed for narrowed in (exact, literal) if len(narrowed) == 1), people)


def hold(people):
    waiting.update(words=asked.get(), jids={person["jid"] for person in people})


def which_one(said, people):
    """The question to put when a name fits several people, spelled out, because told only the rule a small model does not ask it."""
    names = [person["name"] for person in people]
    shown = [f"{name} ending {' '.join(person['number'][-4:])}" if names.count(name) > 1 else name for name, person in zip(names, people)]
    choice = ", ".join(shown[:6][:-1]) + f" or {shown[:6][-1]}"
    twins = "".join(f" The one ending {person['number'][-4:]} is sent with to {person['number']}." for name, person in zip(names, people) if names.count(name) > 1)
    return (f"Not sent: '{said}' fits {len(people)} contacts. Ask them exactly: \"Which {said} do you mean, {choice}?\" "
            f"When they choose, send again with to set to the name they chose.{twins}")


def first_contact(person):
    ending = " ".join(person["number"][-4:])
    return (f"Not sent: {person['name']} is not a saved contact and has never been messaged from this account. Ask them exactly: "
            f"\"{person['name']}, number ending {ending}, isn't saved and you've never messaged them. Should I send it?\" "
            f"Send it only if they say yes.")


@tool(say="Sending it.", label="Sending to {to} on WhatsApp", local_only=True, needs=connected, check=wordless)
async def whatsapp_send(
    to: Annotated[str, "the person or group, by name; 'me' for the person you are talking with, which goes to their chat with you"],
    message: Annotated[str, "the whole message written out: their words, any link, and what they asked you to ask or tell; with a file, a caption or empty"] = "",
    file: Annotated[str, "full path of a file on this computer to send, like a document or photo; empty for only words"] = "",
    relation: Annotated[str, "the relationship word they used for the person, like 'brother', 'mom' or 'boss', never the name; empty if they only gave a name"] = "",
):
    """Send a WhatsApp message, or a file on this computer like a document or photo."""
    import asyncio
    from pathlib import Path

    from happy.integrations import whatsapp

    file = file.strip()
    if file and not Path(file).expanduser().is_file():
        return f"Error: there is no file at {file}. Find it first, then send it with its full path."
    said = said_lately()
    if to.strip().lower() in ME:
        own = whatsapp.own_chat()
        if not own:
            return "Error: your chat with me on WhatsApp is not set up yet, so there is nowhere to send it."
        if file:
            body = {"to": own, "url": str(Path(file).expanduser().resolve()), "caption": message, "filename": Path(file).name}
            data = await asyncio.to_thread(post, "/send-media", body)
        else:
            data = await asyncio.to_thread(post, "/send-group", {"groupId": own, "message": message})
        return data if isinstance(data, str) else json.dumps(data)[:800]
    from whatsapp_server import contacts

    looked = contacts.recall(to.strip(), "whatsapp") or to.strip()
    people = await asyncio.to_thread(recipients, looked)
    if isinstance(people, str):
        return people
    told = answering()
    if len(people) > 1 and told:
        people = spelled(looked, people)
    person = people[0] if len(people) == 1 else None
    answered = told and person is not None and person["jid"] in waiting["jids"]
    # A SEND NOBODY ASKED FOR CANNOT BE TAKEN BACK: "SEND IT HERE" WENT TO THE LAST PERSON TALKED ABOUT, AS THE WORDS "SEND IT HERE".
    word = relation.strip().lower().removeprefix("my ").strip()
    # "TELL MY BROTHER" NAMES HIM AS SURELY AS HIS NAME DOES, ONCE THE CONTACT IT MEANS WAS LOOKED UP.
    if not answered and said is not None and not named(to, said) and not (word and re.search(rf"\b{re.escape(word)}\b", said)):
        return (f"Not sent: they never named {to}. Ask them who it should go to, or whether they meant you, "
                f"and send it only once they say.")
    if len(people) > 1:
        hold(people)
        return which_one(to.strip(), people)
    # NO PICKING FOR THEM: THE ANSWER HAS TO COME FROM THEIR NEXT WORDS, NOT THE SAME TURN THAT RAISED THE QUESTION.
    if person and asked.get() == waiting["words"] and person["jid"] in waiting["jids"]:
        return f"Not sent: they have not answered yet. Ask them first, and do not send to {person['name']} until they do."
    if person and not (person["saved"] or person["talked"] or answered):
        hold(people)
        return first_contact(person)
    target = person["jid"] if person else to
    if file:
        data = await ask("send_media_message", recipients=[target], source=str(Path(file).expanduser().resolve()), caption=message)
    else:
        data = await ask("send_message", recipients=[target], message=message)
    failed = (isinstance(data, str) and data.lower().startswith("error")) or (isinstance(data, dict) and (data.get("error") or data.get("success") is False))
    # ONLY A WORD THEY ACTUALLY SAID IS KEPT: A GUESSED "brother" ONCE WROTE A WRONG PERSON INTO THE NOTES FOR GOOD.
    if word and word != to.strip().lower() and not failed and said is not None and re.search(rf"\b{re.escape(word)}\b", said):
        from happy.tools.notes import note

        # "MY BROTHER, JOHN DOE" SAID ONCE IS KEPT, SO TOMORROW "MY BROTHER" NEEDS NO EXPLAINING.
        note(f"'{word}' means {to.strip()} (their name in WhatsApp)")
        await hub.call("whatsapp", "remember_contact", {"said": word, "means": to.strip()})
    return data if isinstance(data, str) else json.dumps(data)[:800]


def post(path, body):
    """A send straight through the WhatsApp bridge, for Happy's own chat, which is not a contact."""
    import httpx

    from happy.integrations import whatsapp

    try:
        return httpx.post(f"{whatsapp.BASE}{path}", json=body, timeout=60).json()
    except (httpx.HTTPError, ValueError) as error:
        return f"Error: could not reach WhatsApp: {error}"


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
