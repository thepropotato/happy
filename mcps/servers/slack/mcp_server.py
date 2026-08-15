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


def counted(limit):
    return max(1, min(int(limit), 50))


if __name__ == "__main__":
    mcp.run()
