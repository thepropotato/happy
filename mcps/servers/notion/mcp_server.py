"""THE NOTION SERVER: SEARCHING A WORKSPACE, READING A PAGE, AND WRITING ONE."""

import sys
from pathlib import Path

# THE SERVER'S OWN FOLDER COMES OFF THE PATH SO A FILE BESIDE THIS ONE CAN NEVER
# BE WHAT SOME LIBRARY'S import FINDS FIRST.
sys.path[0] = str(Path(__file__).resolve().parents[2])

from mcp.server.fastmcp import FastMCP  # noqa: E402

from servers.shared import credentials  # noqa: E402
from servers.shared.answering import ok, some  # noqa: E402
from servers.shared.reaching import Service  # noqa: E402

mcp = FastMCP("notion", log_level="ERROR")

NAME = "notion"

BASE = "https://api.notion.com/v1"

# NOTION PINS ITS API TO A DATE. AN OLDER ONE KEEPS WORKING; A MISSING ONE DOES NOT.
VERSION = "2022-06-28"

MISSING = "Notion is not connected. Paste an integration token in Happy's connections panel."

MOST_BODY = 4000


@mcp.tool()
def search(query: str = "", limit: int = 10) -> str:
    """Find pages and databases in Notion by title.

    Left empty it gives whatever was touched most recently. Reading one in full
    needs read_page and the id this gives back.
    """
    found = notion().post(
        "search", {"query": query or "", "page_size": max(1, min(int(limit), 25))}
    )

    return ok([outlined(each) for each in found.get("results", [])])


@mcp.tool()
def read_page(page_id: str) -> str:
    """Read a Notion page: what it is called, and the text on it."""
    service = notion()
    page = service.get(f"pages/{page_id}")
    blocks = service.get(f"blocks/{page_id}/children", {"page_size": 100})

    lines = [worded(each) for each in blocks.get("results", [])]

    return ok(
        {
            "id": page_id,
            "title": titled(page),
            "url": page.get("url"),
            "body": "\n".join(line for line in lines if line)[:MOST_BODY],
        }
    )


@mcp.tool()
def create_page(parent_id: str, title: str, content: str = "", inside: str = "page") -> str:
    """Make a new page in Notion, under a page or inside a database.

    inside is `page` when parent_id is another page, or `database` when it is a
    database. Content becomes one paragraph per line.
    """
    where = "database_id" if inside == "database" else "page_id"
    made = notion().post(
        "pages",
        {
            "parent": {where: parent_id},
            "properties": {"title": {"title": [{"text": {"content": title}}]}},
            "children": paragraphs(content),
        },
    )

    return ok({"created": True, "id": made.get("id"), "title": title, "url": made.get("url")})


@mcp.tool()
def append_to_page(page_id: str, content: str) -> str:
    """Add text to the bottom of a page that already exists, one paragraph per line."""
    added = notion().patch(f"blocks/{page_id}/children", {"children": paragraphs(content)})

    return ok({"added": len(added.get("results", [])), "id": page_id})


@mcp.tool()
def query_database(database_id: str, limit: int = 10) -> str:
    """List the rows of a Notion database, most recently changed first."""
    found = notion().post(
        f"databases/{database_id}/query",
        {
            "page_size": max(1, min(int(limit), 25)),
            "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}],
        },
    )

    return ok([outlined(each) for each in found.get("results", [])])


@mcp.tool()
def who_signed_in() -> str:
    """THE NAME ON THIS ACCOUNT. HAPPY ASKS IT HIMSELF; IT IS NEVER OFFERED TO THE MODEL."""
    found = notion().get("users/me")

    # THE TOKEN BELONGS TO AN INTEGRATION, SO THE PERSON IS WHOEVER MADE IT.
    owner = (((found.get("bot") or {}).get("owner")) or {}).get("user") or {}

    return str(owner.get("name") or "").strip()


def notion():
    token = credentials.token(NAME)

    if not token:
        raise PermissionError(MISSING)

    return Service(
        BASE,
        {
            "Authorization": f"Bearer {token}",
            "Notion-Version": VERSION,
            "Content-Type": "application/json",
        },
        "Notion",
    )


def outlined(thing):
    return {
        "id": thing.get("id"),
        "kind": thing.get("object"),
        "title": some(titled(thing), 160),
        "url": thing.get("url"),
        "changed": thing.get("last_edited_time"),
    }


def titled(thing):
    """WHAT A PAGE OR A DATABASE IS CALLED, WHEREVER IT HAPPENS TO KEEP IT."""
    written = thing.get("title")

    if isinstance(written, list):
        return joined(written)

    for name, held in (thing.get("properties") or {}).items():
        if held.get("type") == "title":
            return joined(held.get("title") or []) or name

    return ""


def worded(block):
    """ONE BLOCK AS THE LINE OF TEXT IT HOLDS, WHATEVER KIND OF BLOCK IT IS."""
    kind = block.get("type", "")

    return joined((block.get(kind) or {}).get("rich_text") or [])


def joined(rich):
    return "".join(each.get("plain_text", "") for each in rich)


def paragraphs(content):
    """A LUMP OF TEXT AS THE BLOCKS NOTION WANTS, ONE PER LINE."""
    return [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]},
        }
        for line in (content or "").split("\n")
        if line.strip()
    ]


if __name__ == "__main__":
    mcp.run()
