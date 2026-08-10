"""GMAIL: FINDING MAIL, READING ONE, AND WRITING ONE."""

import base64
import re
import sys
from email.message import EmailMessage
from email.utils import getaddresses
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory import knowledge
from tongue import names as matching

from servers.google import account, mcp
from servers.shared.answering import ok, some

WANTED = ["From", "To", "Subject", "Date"]

TAGS = re.compile(r"<[^>]+>")

MOST_BODY = 3000


@mcp.tool()
def search_emails(query: str = "", limit: int = 10) -> str:
    """Find emails, newest first, and say who each one is from and what it is about.

    The query is Gmail's own search, so `from:asha is:unread`, `has:attachment`
    and `newer_than:2d` all work. Left empty it gives the most recent mail.
    Reading one in full needs read_email and the id this gives back.
    """
    service = account.mail()
    found = (
        service.users()
        .messages()
        .list(userId="me", q=query or "", maxResults=max(1, min(int(limit), 25)))
        .execute()
    )

    return ok([outlined(service, each["id"]) for each in found.get("messages", [])])


@mcp.tool()
def read_email(message_id: str) -> str:
    """Read one email in full, given the id search_emails gave back."""
    found = (
        account.mail().users().messages().get(userId="me", id=message_id, format="full").execute()
    )
    headers = named(found)

    return ok(
        {
            "id": message_id,
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "body": readable(found.get("payload") or {})[:MOST_BODY],
        }
    )


@mcp.tool()
def send_email(to: str, subject: str, body: str, cc: str = "") -> str:
    """Send an email. to and cc are addresses separated by commas.

    This one actually leaves the machine, and an address off by one character is
    somebody else's inbox, so say what is being sent and to whom before calling it.
    """
    known = known_addresses()
    to = resolved_addresses(to, known)
    cc = resolved_addresses(cc, known)

    sent = (
        account.mail()
        .users()
        .messages()
        .send(userId="me", body={"raw": written(to, subject, body, cc)})
        .execute()
    )

    return ok({"sent": True, "id": sent.get("id"), "to": to, "subject": subject})


@mcp.tool()
def draft_email(to: str, subject: str, body: str, cc: str = "") -> str:
    """Write an email and leave it in Drafts without sending it.

    Use this when somebody wants to look it over first.
    """
    known = known_addresses()
    to = resolved_addresses(to, known)
    cc = resolved_addresses(cc, known)

    made = (
        account.mail()
        .users()
        .drafts()
        .create(userId="me", body={"message": {"raw": written(to, subject, body, cc)}})
        .execute()
    )

    return ok({"drafted": True, "id": made.get("id"), "to": to, "subject": subject})


@mcp.tool()
def list_labels() -> str:
    """List the labels on this mailbox, for narrowing a search down to one."""
    found = account.mail().users().labels().list(userId="me").execute()

    return ok([each["name"] for each in found.get("labels", [])])


@mcp.tool()
async def remember_email(said: str, means: str) -> str:
    """Remember that when the person says 'said' as a recipient
    name, they mean the email address 'means'. Only call this once,
    right after the person has directly confirmed 'means' is
    correct."""
    knowledge.remember_fact(said, "gmail", means)
    return ok({"remembered": True, "said": said, "means": means})


def known_addresses(limit=200):
    service = account.mail()
    found = {}
    listed = (
        service.users().messages().list(userId="me", maxResults=max(1, min(int(limit), 200))).execute()
    )

    for each in listed.get("messages", []):
        one = (
            service.users()
            .messages()
            .get(userId="me", id=each["id"], format="metadata", metadataHeaders=["From", "To", "Cc"])
            .execute()
        )
        headers = named(one)
        for label in ("From", "To", "Cc"):
            for shown, address in getaddresses([headers.get(label, "")]):
                remembered(found, shown, address)

    return found


def remembered(found, shown, address):
    where = str(address or "").strip().lower()

    if not where or "@" not in where:
        return

    who = str(shown or "").strip()
    local = where.split("@", 1)[0]

    found.setdefault(where, where)

    if local:
        found.setdefault(local, where)

    if who:
        found.setdefault(who, where)


def resolved_addresses(value, known):
    parts = [each.strip() for each in str(value or "").split(",") if each.strip()]

    if not parts:
        return ""

    resolved = []

    for each in parts:
        if "@" in each:
            resolved.append(each)
            continue

        held = knowledge.recall(each, "gmail")

        if held:
            resolved.append(held)
            continue

        match = matching.resolve(each, list(known))[0]
        candidate = known.get(match) if match else None
        chosen = knowledge.resolve_or_confirm(each, "gmail", candidate)

        if chosen:
            resolved.append(chosen)
            continue

        raise LookupError(f"I couldn't find an email address matching '{each}'.")

    return ", ".join(resolved)


def outlined(service, message_id):
    """ONE MAIL AS THE FEW LINES A LIST NEEDS, WHICH IS NOT THE WHOLE OF IT."""
    found = (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="metadata", metadataHeaders=WANTED)
        .execute()
    )
    headers = named(found)

    return {
        "id": message_id,
        "from": some(headers.get("From", ""), 120),
        "subject": some(headers.get("Subject", ""), 160),
        "date": headers.get("Date", ""),
        "unread": "UNREAD" in (found.get("labelIds") or []),
        "snippet": some(found.get("snippet", ""), 200),
    }


def named(found):
    return {
        each["name"]: each["value"]
        for each in ((found.get("payload") or {}).get("headers") or [])
    }


def readable(payload):
    """THE READABLE PART OF A MAIL. PLAIN TEXT WHERE THERE IS ANY, HTML STRIPPED
    BACK WHERE THERE IS NOT, BECAUSE PLENTY OF SENDERS ONLY EVER SEND HTML."""
    plain, marked = gathered(payload)

    return " ".join((plain or TAGS.sub(" ", marked)).split())


def gathered(part):
    """EVERY TEXT PART OF A MAIL, WHICH NESTS AS DEEP AS THE SENDER FELT LIKE."""
    kind = part.get("mimeType", "")
    data = (part.get("body") or {}).get("data")

    if data and kind == "text/plain":
        return decoded(data), ""

    if data and kind == "text/html":
        return "", decoded(data)

    plain, marked = "", ""

    for each in part.get("parts") or []:
        this, that = gathered(each)
        plain, marked = plain or this, marked or that

    return plain, marked


def decoded(data):
    return base64.urlsafe_b64decode(data).decode("utf-8", "replace")


def written(to, subject, text, cc):
    note = EmailMessage()

    note["To"] = to
    note["Subject"] = subject

    if cc:
        note["Cc"] = cc

    note.set_content(text)

    return base64.urlsafe_b64encode(note.as_bytes()).decode()
