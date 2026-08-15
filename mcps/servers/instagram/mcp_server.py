"""THE INSTAGRAM SERVER: YOUR OWN ACCOUNT, YOUR OWN POSTS, AND WHAT WAS SAID UNDER THEM."""

import sys
from pathlib import Path

# THE SERVER'S OWN FOLDER COMES OFF THE PATH SO A FILE BESIDE THIS ONE CAN NEVER
# BE WHAT SOME LIBRARY'S import FINDS FIRST.
sys.path[0] = str(Path(__file__).resolve().parents[2])

from mcp.server.fastmcp import FastMCP  # noqa: E402

from servers.shared import credentials  # noqa: E402
from servers.shared.answering import ok, some  # noqa: E402
from servers.shared.reaching import Service  # noqa: E402

mcp = FastMCP("instagram", log_level="ERROR")

NAME = "instagram"

BASE = "https://graph.instagram.com/v21.0"

MISSING = (
    "Instagram is not connected. Paste an Instagram access token in Happy's connections panel."
)

# followers_count IS ONLY THERE FOR A PROFESSIONAL ACCOUNT, AND ASKING FOR IT ON
# ANY OTHER KIND FAILS THE WHOLE REQUEST RATHER THAN LEAVING THE FIELD OUT.
ME = "id,username,account_type,media_count"

POST = "id,caption,media_type,media_url,permalink,timestamp,username"

COMMENT = "id,text,username,timestamp,like_count"

MOST = 25


@mcp.tool()
def get_my_profile() -> str:
    """Who Happy is signed in to Instagram as, and how many posts that account
    has. Use it to check the connection is working, or when somebody asks which
    account this is."""
    return ok(instagram().get("me", {"fields": ME}))


@mcp.tool()
def list_posts(limit: int = 10) -> str:
    """This account's own posts, newest first: the caption, what kind of post it
    is, when it went up and a link to it.

    Every post comes with an id, which is what list_comments wants."""
    found = instagram().get("me/media", {"fields": POST, "limit": counted(limit)})

    return ok([post(each) for each in (found.get("data") or [])])


@mcp.tool()
def list_comments(post_id: str, limit: int = 20) -> str:
    """What people have written under one of this account's posts. post_id is
    the id from list_posts.

    Every comment comes with an id of its own, which is what reply_to_comment
    wants."""
    found = instagram().get(f"{post_id}/comments", {"fields": COMMENT, "limit": counted(limit)})

    return ok([comment(each) for each in (found.get("data") or [])])


@mcp.tool()
def reply_to_comment(comment_id: str, message: str) -> str:
    """Reply to a comment on one of this account's posts. It goes up publicly,
    under that comment, from this account, and it cannot be taken back quietly.

    Say what the reply is going to be before calling this."""
    if not (message or "").strip():
        raise ValueError("A reply with nothing in it is not a reply.")

    made = instagram().post(f"{comment_id}/replies", None, {"message": message})

    return ok({"replied": True, "id": made.get("id")})


def post(each):
    return {
        "id": each.get("id"),
        "caption": some(each.get("caption", ""), 300),
        "kind": (each.get("media_type") or "").lower(),
        "posted": each.get("timestamp"),
        "url": each.get("permalink"),
    }


def comment(each):
    return {
        "id": each.get("id"),
        "by": each.get("username"),
        "said": some(each.get("text", ""), 300),
        "likes": each.get("like_count"),
        "at": each.get("timestamp"),
    }


@mcp.tool()
def who_signed_in() -> str:
    """THE NAME ON THIS ACCOUNT. HAPPY ASKS IT HIMSELF; IT IS NEVER OFFERED TO THE MODEL."""
    found = instagram().get("me", {"fields": "username"})

    return str(found.get("username") or "").strip()


def counted(limit):
    return max(1, min(int(limit), MOST))


def instagram():
    """THE API WITH THE TOKEN ALREADY ON EVERY REQUEST."""
    token = credentials.token(NAME)

    if not token:
        raise PermissionError(MISSING)

    return Tokened(BASE, token)


class Tokened(Service):
    """A Service THAT SIGNS EVERY REQUEST IN THE QUERY INSTEAD OF THE HEADER."""

    def __init__(self, base, token):
        super().__init__(base, {}, "Instagram")

        self.token = token

    def sent(self, way, path, **asked):
        asked["params"] = {**(asked.get("params") or {}), "access_token": self.token}

        return super().sent(way, path, **asked)


if __name__ == "__main__":
    mcp.run()
