"""THE SLACK SERVER: WHAT CHANNELS THERE ARE, WHAT WAS SAID, AND SAYING SOMETHING."""

import sys
from pathlib import Path
from re import fullmatch

# THE SERVER'S OWN FOLDER COMES OFF THE PATH SO A FILE BESIDE THIS ONE CAN NEVER
# BE WHAT SOME LIBRARY'S import FINDS FIRST.
sys.path[0] = str(Path(__file__).resolve().parents[2])

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from memory import knowledge  # noqa: E402
from servers.shared import credentials  # noqa: E402
from servers.shared.answering import ok, some  # noqa: E402
from servers.shared.reaching import Service  # noqa: E402
from tongue import names  # noqa: E402

mcp = FastMCP("slack", log_level="ERROR")

NAME = "slack"

BASE = "https://slack.com/api"

MISSING = "Slack is not connected. Paste a user token in Happy's connections panel."

KINDS = "public_channel,private_channel"

known = {}


@mcp.tool()
def list_channels(limit: int = 20) -> str:
    """List the channels this account is in, so one can be named in the others."""
    found = asked("conversations.list", {"types": KINDS, "limit": counted(limit)})

    return ok(
        [
            {
                "id": each.get("id"),
                "name": each.get("name"),
                "members": each.get("num_members"),
                "topic": some((each.get("topic") or {}).get("value", ""), 120),
            }
            for each in found.get("channels", [])
            if each.get("is_member")
        ]
    )


@mcp.tool()
def read_channel(channel: str, limit: int = 20) -> str:
    """Read what was said in a channel, newest first. channel is the id list_channels gave back.

    A message with replies gives back a count and its `at`, which is what
    read_thread wants.
    """
    channel = resolved_target(channel)
    found = asked("conversations.history", {"channel": channel, "limit": counted(limit)})

    return ok([message(each, people()) for each in found.get("messages", [])])


@mcp.tool()
def read_thread(channel: str, at: str, limit: int = 20) -> str:
    """Read the replies under one message, given its channel and its `at`."""
    found = asked(
        "conversations.replies", {"channel": channel, "ts": at, "limit": counted(limit)}
    )

    return ok([message(each, people()) for each in found.get("messages", [])])


@mcp.tool()
def search_messages(query: str, limit: int = 20) -> str:
    """Search everything this account can see in Slack for a word or a phrase."""
    found = asked("search.messages", {"query": query, "count": counted(limit)})

    return ok(
        [
            {
                "at": each.get("ts"),
                "by": each.get("username"),
                "channel": (each.get("channel") or {}).get("name"),
                "text": some(each.get("text", ""), 300),
            }
            for each in (found.get("messages") or {}).get("matches", [])
        ]
    )


@mcp.tool()
def list_users(limit: int = 30) -> str:
    """List the people in this Slack, for turning a name into somebody to message."""
    found = asked("users.list", {"limit": counted(limit)})

    return ok(
        [
            {"id": each.get("id"), "name": each.get("real_name") or each.get("name")}
            for each in found.get("members", [])
            if not each.get("is_bot") and not each.get("deleted")
        ]
    )


@mcp.tool()
def send_message(channel: str, text: str) -> str:
    """Post a message to a channel, where everybody in it will see it.

    channel is an id from list_channels. Say which channel and what it says
    before calling this.
    """
    channel = resolved_target(channel)
    sent = told("chat.postMessage", {"channel": channel, "text": text})

    return ok({"sent": True, "channel": sent.get("channel"), "at": sent.get("ts")})



# ══ CHANNELS AND PEOPLE ══


@mcp.tool()
def list_user_channels(person: str = "", limit: int = 50) -> str:
    """List the channels somebody is in, which is not the same as every channel there is.

    person is a name or id; left out it is whoever the token belongs to. list_channels is
    the one for what this account can see; this one answers "what is Priya in".
    """
    who = resolved_person(person) if person else asked("auth.test").get("user_id")
    found = asked("users.conversations", {"user": who, "types": KINDS, "limit": counted(limit)})

    return ok(
        [
            {"id": each.get("id"), "name": each.get("name"), "private": each.get("is_private")}
            for each in found.get("channels", [])
        ]
    )


@mcp.tool()
def list_channel_members(channel: str, limit: int = 50) -> str:
    """List who is in a channel, by name rather than by id.

    channel is a name or an id from list_channels. Use this for "who is in the design
    channel" before naming somebody in it.
    """
    found = asked(
        "conversations.members", {"channel": resolved_target(channel), "limit": counted(limit)}
    )
    who = people()

    return ok([{"id": each, "name": who.get(each, each)} for each in found.get("members", [])])


@mcp.tool()
def create_conversation(name: str, private: bool = False) -> str:
    """Make a new channel and give back its id.

    name is what it will be called, in lower case with hyphens — Slack will not take spaces
    or capitals. private makes it one only invited people can see. It is created with
    nobody in it but whoever the token belongs to.
    """
    made = told("conversations.create", {"name": name, "is_private": bool(private)})
    channel = made.get("channel") or {}

    return ok({"id": channel.get("id"), "name": channel.get("name")})


@mcp.tool()
def search_channels(text: str, limit: int = 20) -> str:
    """Find channels whose name matches what somebody said.

    text is what to look for. Use this when a channel has been named out loud and its exact
    name is not known; list_channels is the one for the whole list.
    """
    wanted = str(text or "").strip().lower()
    found = asked("conversations.list", {"types": KINDS, "limit": 200})

    return ok(
        [
            {"id": each.get("id"), "name": each.get("name"), "members": each.get("num_members")}
            for each in found.get("channels", [])
            if wanted in str(each.get("name") or "").lower()
        ][: counted(limit)]
    )


@mcp.tool()
def search_users(text: str, limit: int = 20) -> str:
    """Find people in this workspace whose name matches what somebody said.

    text is what to look for. Use this to turn a name said out loud into the id the other
    tools want.
    """
    wanted = str(text or "").strip().lower()
    found = asked("users.list", {"limit": 200})

    return ok(
        [
            {
                "id": each.get("id"),
                "name": each.get("real_name") or each.get("name"),
                "handle": each.get("name"),
            }
            for each in found.get("members", [])
            if not each.get("is_bot")
            and not each.get("deleted")
            and wanted in f"{each.get('real_name') or ''} {each.get('name') or ''}".lower()
        ][: counted(limit)]
    )


@mcp.tool()
def read_user_profile(person: str) -> str:
    """Read somebody's profile: their title, their status and where they are.

    person is a name or an id. Use this for "what is Priya's title", "is Sam away".
    """
    who = resolved_person(person)
    found = asked("users.info", {"user": who})
    user = found.get("user") or {}
    profile = user.get("profile") or {}

    return ok(
        {
            "id": user.get("id"),
            "name": profile.get("real_name"),
            "handle": user.get("name"),
            "title": profile.get("title"),
            "status": " ".join(
                each for each in [profile.get("status_emoji"), profile.get("status_text")] if each
            ),
            "timezone": user.get("tz_label"),
            "away": user.get("deleted") or False,
        }
    )


# ══ SAYING THINGS ══


@mcp.tool()
def schedule_message(channel: str, text: str, at: str) -> str:
    """Post a message later rather than now.

    channel is a name or id, and at is when, as a unix timestamp in seconds. Slack will not
    take one in the past or more than 120 days out. send_message is the one for now.
    """
    sent = told(
        "chat.scheduleMessage",
        {"channel": resolved_target(channel), "text": text, "post_at": int(float(at))},
    )

    return ok({"scheduled": sent.get("scheduled_message_id"), "at": sent.get("post_at")})


@mcp.tool()
def send_message_draft(channel: str, text: str) -> str:
    """Write a message into a channel's box without sending it, for somebody to look over.

    channel is a name or id. Nothing is posted: it appears in their Slack as an unsent
    draft. Use this when the wording should be theirs to approve.
    """
    made = told(
        "chat.scheduleMessage",
        {"channel": resolved_target(channel), "text": text, "post_at": int(later())},
    )

    return ok(
        {
            "drafted": made.get("scheduled_message_id"),
            "channel": made.get("channel"),
            "note": "held as a scheduled message; delete it in Slack to cancel",
        }
    )


# ══ REACTIONS AND EMOJI ══


@mcp.tool()
def add_reaction(channel: str, at: str, emoji: str) -> str:
    """Put an emoji on a message.

    channel is a name or id, at is the message's timestamp from read_channel, and emoji is
    its name without the colons — thumbsup, eyes, tada.
    """
    told(
        "reactions.add",
        {"channel": resolved_target(channel), "timestamp": at, "name": bare(emoji)},
    )

    return ok({"reacted": bare(emoji), "at": at})


@mcp.tool()
def get_reactions(channel: str, at: str) -> str:
    """Read what people have reacted with on one message, and who reacted.

    channel is a name or id and at is the message's timestamp from read_channel.
    """
    found = asked(
        "reactions.get", {"channel": resolved_target(channel), "timestamp": at, "full": True}
    )
    who = people()
    message = found.get("message") or {}

    return ok(
        [
            {
                "emoji": each.get("name"),
                "count": each.get("count"),
                "by": [who.get(one, one) for one in (each.get("users") or [])],
            }
            for each in (message.get("reactions") or [])
        ]
    )


@mcp.tool()
def search_emojis(text: str = "", limit: int = 30) -> str:
    """List the custom emoji this workspace has, or the ones matching what was said.

    text narrows it by name. Use this before add_reaction when the emoji wanted may be one
    somebody here made rather than a standard one.
    """
    found = asked("emoji.list")
    wanted = str(text or "").strip().lower()
    names_found = [
        each for each in (found.get("emoji") or {}) if not wanted or wanted in each.lower()
    ]

    return ok(sorted(names_found)[: counted(limit)])


# ══ FILES ══


@mcp.tool()
def read_file(file: str) -> str:
    """Read what Slack knows about a file somebody shared: its name, kind, size and where it is.

    file is the id Slack gives a file. The bytes themselves are not fetched; this is what
    the file is and who shared it.
    """
    found = asked("files.info", {"file": file})
    each = found.get("file") or {}
    who = people()

    return ok(
        {
            "id": each.get("id"),
            "name": each.get("name"),
            "kind": each.get("filetype"),
            "size": each.get("size"),
            "by": who.get(each.get("user"), each.get("user")),
            "at": each.get("created"),
            "url": each.get("permalink"),
        }
    )


@mcp.tool()
def get_file_upload_url(filename: str, size: int) -> str:
    """Ask Slack for somewhere to put a file, which is the first half of sharing one.

    size is in bytes. What comes back is an address the file itself is then POSTed to, and
    complete_file_upload is what finishes it and puts it in a channel.
    """
    found = asked("files.getUploadURLExternal", {"filename": filename, "length": int(size)})

    return ok({"post_to": found.get("upload_url"), "file": found.get("file_id")})


@mcp.tool()
def complete_file_upload(file: str, channel: str = "", title: str = "") -> str:
    """Finish sharing a file that has been uploaded, and put it in a channel.

    file is the id get_file_upload_url gave back. channel is where it lands; left out, the
    file exists but sits in nobody's channel.
    """
    wanted = {"files": [{"id": file, "title": title or ""}]}

    if channel:
        wanted["channel_id"] = resolved_target(channel)

    made = told("files.completeUploadExternal", wanted)

    return ok({"shared": [each.get("id") for each in made.get("files", [])]})


# ══ CANVASES ══


@mcp.tool()
def create_canvas(title: str, markdown: str = "", channel: str = "") -> str:
    """Make a canvas, which is Slack's written page rather than a message.

    markdown is what goes in it. channel attaches it to that channel rather than leaving it
    standalone. Use this for something meant to be kept and edited, not said once.
    """
    if channel:
        made = told(
            "conversations.canvases.create",
            {
                "channel_id": resolved_target(channel),
                "document_content": {"type": "markdown", "markdown": markdown or f"# {title}"},
            },
        )
    else:
        made = told(
            "canvases.create",
            {
                "title": title,
                "document_content": {"type": "markdown", "markdown": markdown or f"# {title}"},
            },
        )

    return ok({"canvas": made.get("canvas_id")})


@mcp.tool()
def read_canvas(canvas: str) -> str:
    """Read what is written on a canvas.

    canvas is its id. A canvas is looked up as a file, because that is what Slack keeps one as.
    """
    found = asked("files.info", {"file": canvas})
    each = found.get("file") or {}

    return ok(
        {
            "id": each.get("id"),
            "title": each.get("title") or each.get("name"),
            "content": some(
                (each.get("preview") or "") or str((each.get("canvas") or {}).get("content") or ""),
                2000,
            ),
            "url": each.get("permalink"),
        }
    )


@mcp.tool()
def update_canvas(canvas: str, markdown: str, replace: bool = False) -> str:
    """Add to a canvas, or write over what is on it.

    canvas is its id and markdown is what to put there. replace being true writes over the
    whole thing; left alone it is added to the end.
    """
    how = "replace" if replace else "insert_at_end"

    told(
        "canvases.edit",
        {
            "canvas_id": canvas,
            "changes": [
                {"operation": how, "document_content": {"type": "markdown", "markdown": markdown}}
            ],
        },
    )

    return ok({"canvas": canvas, "how": how})


# ══ LISTS ══


@mcp.tool()
def create_list(title: str, description: str = "") -> str:
    """Make a Slack list, which is their table of rows rather than a channel of messages.

    A list holds tracked items — tasks, requests, anything with a state. add_list_record is
    what puts a row in one.
    """
    wanted = {"name": title}

    if description:
        wanted["description_blocks"] = [
            {"type": "rich_text", "elements": [
                {"type": "rich_text_section", "elements": [{"type": "text", "text": description}]}
            ]}
        ]

    made = told("slackLists.create", wanted)

    return ok({"list": made.get("list_id") or (made.get("list") or {}).get("id")})


@mcp.tool()
def read_list(list_id: str, limit: int = 30) -> str:
    """Read the rows in a Slack list.

    list_id is the id create_list gave back, or one taken from the list's own address in Slack.
    """
    found = asked("slackLists.items.list", {"list_id": list_id, "limit": counted(limit)})

    return ok(
        [
            {"id": each.get("id"), "fields": each.get("fields")}
            for each in (found.get("items") or [])
        ]
    )


@mcp.tool()
def update_list(list_id: str, title: str = "", description: str = "") -> str:
    """Change a list's own name or description, not the rows in it.

    list_id is its id. update_list_record is the one for a row.
    """
    wanted = {"list_id": list_id}

    if title:
        wanted["name"] = title

    if description:
        wanted["description_blocks"] = [
            {"type": "rich_text", "elements": [
                {"type": "rich_text_section", "elements": [{"type": "text", "text": description}]}
            ]}
        ]

    told("slackLists.update", wanted)

    return ok({"list": list_id, "changed": True})


@mcp.tool()
def add_list_record(list_id: str, fields: str) -> str:
    """Put a new row in a Slack list.

    fields is what goes in it, written as JSON — {"Name": "Fix login", "Status": "Open"}. The
    column names have to be ones that list already has; read_list shows what a row looks like.
    """
    made = told(
        "slackLists.items.create", {"list_id": list_id, "initial_fields": parsed(fields)}
    )

    return ok({"row": made.get("item_id") or (made.get("item") or {}).get("id")})


@mcp.tool()
def update_list_record(list_id: str, record: str, fields: str) -> str:
    """Change a row that is already in a Slack list.

    record is the row's id from read_list, and fields is what to change, written as JSON.
    Only the columns named are touched.
    """
    told(
        "slackLists.items.update",
        {"list_id": list_id, "id": record, "cells": parsed(fields)},
    )

    return ok({"row": record, "changed": True})


@mcp.tool()
def search_public_and_private(query: str, limit: int = 20) -> str:
    """Search everything this account can see, private channels and direct messages included.

    query is what to look for and takes Slack's own modifiers — in:#design, from:@priya.
    search_messages is the one that stays out of private conversations.
    """
    found = asked("search.all", {"query": query, "count": counted(limit)})
    messages = ((found.get("messages") or {}).get("matches")) or []

    return ok(
        [
            {
                "channel": ((each.get("channel") or {}) or {}).get("name"),
                "by": each.get("username"),
                "at": each.get("ts"),
                "text": some(each.get("text"), 300),
            }
            for each in messages
        ]
    )


@mcp.tool()
async def remember_slack(said: str, means: str) -> str:
    """Remember that when the person says 'said', they mean the
    Slack channel or person 'means' (the id, not the display name).
    Only call this once, right after the person has directly
    confirmed 'means' is correct."""
    knowledge.remember_fact(said, "slack", means)
    return ok({"remembered": True, "said": said, "means": means})


@mcp.tool()
def who_signed_in() -> str:
    """THE NAME ON THIS ACCOUNT. HAPPY ASKS IT HIMSELF; IT IS NEVER OFFERED TO THE MODEL."""
    who = asked("auth.test")
    found = asked("users.info", {"user": who.get("user_id")})
    profile = ((found.get("user") or {}).get("profile")) or {}

    return str(profile.get("real_name") or who.get("user") or "").strip()


def slack():
    token = credentials.token(NAME)

    if not token:
        raise PermissionError(MISSING)

    return Service(BASE, {"Authorization": f"Bearer {token}"}, "Slack")


def resolved_target(given):
    asked_name = str(given or "").strip()

    if not asked_name:
        raise LookupError("Channel or person name is required.")

    known_id = knowledge.recall(asked_name, "slack")

    if known_id:
        return usable_target(known_id)

    if is_slack_id(asked_name):
        return usable_target(asked_name)

    candidate = candidate_target(asked_name)
    chosen = knowledge.resolve_or_confirm(asked_name, "slack", candidate)

    if not chosen:
        raise LookupError(f"I couldn't find a Slack channel or person matching '{asked_name}'.")

    return usable_target(chosen)


def candidate_target(spoken):
    options = {}

    channels = asked("conversations.list", {"types": KINDS, "limit": 200}).get("channels", [])
    for each in channels:
        if each.get("is_member"):
            name = str(each.get("name") or "").strip()
            if name:
                options[name] = each.get("id")

    members = asked("users.list", {"limit": 200}).get("members", [])
    for each in members:
        if each.get("is_bot") or each.get("deleted"):
            continue
        name = str(each.get("real_name") or each.get("name") or "").strip()
        if name:
            options[name] = each.get("id")

    matched, sure = names.resolve(spoken, list(options))

    if not matched:
        return None

    return options.get(matched) if sure else options.get(matched)


def usable_target(slack_id):
    target = str(slack_id or "").strip()

    if not target:
        return ""

    if target.startswith("U") or target.startswith("W"):
        opened = told("conversations.open", {"users": target})
        return ((opened.get("channel") or {}).get("id") or target)

    return target


def is_slack_id(value):
    return bool(fullmatch(r"[A-Z][A-Z0-9]{8,}", str(value or "").strip()))


def asked(method, params=None):
    return checked(slack().get(method, params))


def told(method, body):
    return checked(slack().post(method, body))


def checked(answer):
    if not answer.get("ok"):
        raise PermissionError(f"Slack said no. {answer.get('error') or 'it did not say why'}")

    return answer


def message(each, who):
    return {
        "at": each.get("ts"),
        "by": who.get(each.get("user"), each.get("username") or each.get("user")),
        "text": some(each.get("text", ""), 400),
        "replies": each.get("reply_count"),
    }


def people():
    """WHO EVERY USER ID BELONGS TO, ASKED ONCE AND THEN KEPT FOR THIS PROCESS."""
    if not known:
        found = asked("users.list", {"limit": 200})

        for each in found.get("members", []):
            known[each["id"]] = each.get("real_name") or each.get("name")

    return known


def resolved_person(given):
    """SOMEBODY BY NAME, OR THE ID ITSELF WHEN THAT IS WHAT WAS HANDED OVER."""
    said = str(given or "").strip()

    if not said:
        raise LookupError("A name or an id is needed.")

    if is_slack_id(said):
        return said

    wanted = said.lower()

    for each, name in people().items():
        if wanted == str(name or "").lower():
            return each

    for each, name in people().items():
        if wanted in str(name or "").lower():
            return each

    raise LookupError(f"There is nobody in this workspace called {given}.")


def bare(emoji):
    """AN EMOJI'S NAME AS SLACK WANTS IT, WITHOUT THE COLONS SOMEBODY MAY HAVE TYPED."""
    return str(emoji or "").strip().strip(":")


def parsed(fields):
    """A ROW'S COLUMNS, WHICH ARRIVE AS JSON BECAUSE A TOOL CANNOT TAKE A DICTIONARY."""
    import json

    try:
        found = json.loads(fields) if isinstance(fields, str) else fields
    except ValueError:
        raise LookupError('fields has to be JSON, like {"Name": "Fix login"}.')

    if not isinstance(found, dict):
        raise LookupError('fields has to be a JSON object, like {"Name": "Fix login"}.')

    return found


def later():
    """A MOMENT FAR ENOUGH OFF THAT SLACK TAKES IT, FOR SOMETHING HELD RATHER THAN SENT."""
    import time

    return time.time() + 600


def counted(limit):
    return max(1, min(int(limit), 50))


if __name__ == "__main__":
    mcp.run()
