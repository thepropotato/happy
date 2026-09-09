"""THE NOTION SERVER: A WORKSPACE SEARCHED, READ, WRITTEN AND SHARED.

NOTION'S OWN SERVER OFFERS FORTY-TWO TOOLS AND EIGHTEEN OF THEM HAVE NO PUBLIC ENDPOINT AT
ALL: EVERY AGENT SESSION ONE, THE SKILLS AND AGENTS, THE AI SEARCH, MEETING NOTES, THE
TEAMSPACE FOLDERS — /v1/folders ANSWERS 400 — AND TWO THAT ONLY DRAW AN UPSELL CARD. VIEWS AND
BACKGROUND TASKS ARE THREE MORE THE REST OF THE API NEVER REACHES. WHAT IS LEFT IS HERE."""

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

# NOTION PINS ITS API TO A DATE. AN OLDER ONE KEEPS WORKING; A MISSING ONE DOES NOT. THIS ONE
# IS WHERE A DATABASE BECAME A DATA SOURCE, WHICH IS WHAT THE QUERY AND VIEW TOOLS TALK TO.
VERSION = "2025-09-03"

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



# ══ FINDING AND READING ══


@mcp.tool()
def fetch(url_or_id: str) -> str:
    """Read whatever a Notion link points at, whether it is a page or a database.

    url_or_id is a link somebody pasted or an id. This is the one for "what does this link
    say"; read_page is the one when a page id is already in hand.
    """
    wanted = identified(url_or_id)

    try:
        return read_page(wanted)
    except Exception:
        found = notion().get(f"databases/{wanted}")

        return ok(outlined(found))


@mcp.tool()
def list_recent_pages(limit: int = 20) -> str:
    """List what was edited most recently in this workspace, newest first.

    Use this for "what has been worked on", or as a way in when nothing has been named.
    """
    found = notion().post(
        "search",
        {
            "page_size": counted(limit),
            "sort": {"direction": "descending", "timestamp": "last_edited_time"},
        },
    )

    return ok([outlined(each) for each in found.get("results", [])])


@mcp.tool()
def list_private_pages(limit: int = 20) -> str:
    """List the pages that live in somebody's own private section rather than a shared one.

    A page is private when it has no parent workspace or teamspace above it.
    """
    found = notion().post(
        "search", {"page_size": counted(limit), "filter": {"property": "object", "value": "page"}}
    )

    return ok(
        [
            outlined(each)
            for each in found.get("results", [])
            if ((each.get("parent") or {}).get("type")) == "workspace"
        ]
    )


@mcp.tool()
def list_shared_pages(limit: int = 20) -> str:
    """List the pages that sit inside a teamspace, which is what everybody there can see.

    This is the opposite of list_private_pages: what is shared rather than somebody's own.
    """
    found = notion().post(
        "search", {"page_size": counted(limit), "filter": {"property": "object", "value": "page"}}
    )

    return ok(
        [
            outlined(each)
            for each in found.get("results", [])
            if ((each.get("parent") or {}).get("type")) != "workspace"
        ]
    )


@mcp.tool()
def list_favorite_pages(limit: int = 20) -> str:
    """List the pages somebody has starred in Notion.

    Notion does not hand favourites to an integration, so this answers with what was edited
    most recently instead and says so — it is the nearest thing the public API has.
    """
    found = notion().post(
        "search",
        {
            "page_size": counted(limit),
            "sort": {"direction": "descending", "timestamp": "last_edited_time"},
        },
    )

    return ok(
        {
            "note": "Notion's API does not expose favourites; these are the most recent instead.",
            "pages": [outlined(each) for each in found.get("results", [])],
        }
    )


# ══ PAGES ══


@mcp.tool()
def create_pages(parent_id: str, titles: str, inside: str = "page") -> str:
    """Make several pages at once under the same parent.

    titles is one title per line. inside is page or database, saying what the parent is.
    create_page is the one for a single page with content in it.
    """
    made = []

    for line in str(titles or "").split("\n"):
        if line.strip():
            made.append(create_page(parent_id, line.strip(), "", inside))

    return ok({"made": len(made)})


@mcp.tool()
def update_page(page_id: str, title: str = "", archived: bool = False) -> str:
    """Change a page's title, or put it in the archive.

    page_id is its id. archived being true is Notion's delete: the page goes to the trash
    and can be brought back from there. append_to_page is the one for adding words.
    """
    wanted = {}

    if title:
        wanted["properties"] = {
            "title": {"title": [{"type": "text", "text": {"content": title}}]}
        }

    if archived:
        wanted["archived"] = True

    if not wanted:
        raise LookupError("Nothing was given to change on that page.")

    changed = notion().patch(f"pages/{page_id}", wanted)

    return ok(outlined(changed))


@mcp.tool()
def duplicate_page(page_id: str, parent_id: str, title: str = "") -> str:
    """Copy a page, with what is written on it, to somewhere else.

    page_id is the one to copy and parent_id is where the copy goes. title renames the copy;
    left out it keeps the original's name with a note that it is a copy.
    """
    original = notion().get(f"pages/{page_id}")
    blocks = notion().get(f"blocks/{page_id}/children", {"page_size": 100})
    name = title or f"{titled(original)} (copy)"

    made = notion().post(
        "pages",
        {
            "parent": {"page_id": parent_id},
            "properties": {"title": {"title": [{"type": "text", "text": {"content": name}}]}},
        },
    )

    lines = [worded(each) for each in blocks.get("results", [])]
    written = "\n".join(each for each in lines if each)

    if written:
        notion().patch(f"blocks/{made['id']}/children", {"children": paragraphs(written)})

    return ok(outlined(made))


@mcp.tool()
def move_pages(page_ids: str, parent_id: str) -> str:
    """Move pages under a different parent.

    page_ids is one id per line. Notion cannot reparent a page in place, so each one is
    copied to the new parent and the original is archived.
    """
    moved = []

    for each in str(page_ids or "").split("\n"):
        if each.strip():
            duplicate_page(each.strip(), parent_id)
            notion().patch(f"pages/{each.strip()}", {"archived": True})
            moved.append(each.strip())

    return ok({"moved": moved})


# ══ DATABASES, DATA SOURCES AND VIEWS ══


@mcp.tool()
def create_database(parent_id: str, title: str, columns: str = "") -> str:
    """Make a database under a page, with the columns it should have.

    columns is one per line, written as name:kind — "Status:select", "Due:date",
    "Owner:people". A title column is always made and needs no naming. Left empty it gets a
    title column only.
    """
    made = notion().post(
        "databases",
        {
            "parent": {"type": "page_id", "page_id": parent_id},
            "title": [{"type": "text", "text": {"content": title}}],
            "properties": shaped(columns),
        },
    )

    return ok(outlined(made))


@mcp.tool()
def query_data_sources(data_source_id: str, limit: int = 20) -> str:
    """List the rows of a data source, most recently changed first.

    A data source is what Notion now calls the rows behind a database. data_source_id is its
    id, which is not the database's — get_teams and search give it back on a database.
    """
    found = notion().post(
        f"data_sources/{data_source_id}/query",
        {
            "page_size": counted(limit),
            "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}],
        },
    )

    return ok([outlined(each) for each in found.get("results", [])])


@mcp.tool()
def query_multiple_data_sources(data_source_ids: str, limit: int = 10) -> str:
    """List rows from several data sources at once, for a question that spans them.

    data_source_ids is one id per line. Each one is asked separately and the answers come
    back grouped, because Notion has no single call that spans them.
    """
    out = {}

    for each in str(data_source_ids or "").split("\n"):
        wanted = each.strip()

        if not wanted:
            continue

        try:
            found = notion().post(
                f"data_sources/{wanted}/query", {"page_size": counted(limit)}
            )
            out[wanted] = [outlined(one) for one in found.get("results", [])]
        except Exception as trouble:
            out[wanted] = f"could not be read: {some(str(trouble), 120)}"

    return ok(out)


@mcp.tool()
def update_data_source(data_source_id: str, title: str = "", columns: str = "") -> str:
    """Change what a data source is called, or add columns to it.

    columns is one per line as name:kind, the same as create_database takes. Existing columns
    are left alone; naming one that already exists changes its kind.
    """
    wanted = {}

    if title:
        wanted["title"] = [{"type": "text", "text": {"content": title}}]

    if columns:
        wanted["properties"] = shaped(columns, titled_first=False)

    if not wanted:
        raise LookupError("Nothing was given to change on that data source.")

    changed = notion().patch(f"data_sources/{data_source_id}", wanted)

    return ok(outlined(changed))




# ══ COMMENTS ══


@mcp.tool()
def get_comments(page_id: str, limit: int = 20) -> str:
    """Read the comments left on a page.

    page_id is its id. These are the comments on the page itself, which is where discussion
    about a page lives.
    """
    found = notion().get("comments", {"block_id": page_id, "page_size": counted(limit)})

    return ok(
        [
            {
                "id": each.get("id"),
                "by": ((each.get("created_by") or {}) or {}).get("id"),
                "at": each.get("created_time"),
                "said": some(joined(each.get("rich_text") or []), 600),
            }
            for each in found.get("results", [])
        ]
    )


@mcp.tool()
def create_comment(page_id: str, text: str) -> str:
    """Leave a comment on a page, which everybody who can see the page will see.

    page_id is its id. It is posted as whoever the integration belongs to.
    """
    made = notion().post(
        "comments",
        {
            "parent": {"page_id": page_id},
            "rich_text": [{"type": "text", "text": {"content": text}}],
        },
    )

    return ok({"id": made.get("id"), "on": page_id})


# ══ PEOPLE AND TEAMS ══


@mcp.tool()
def get_users(limit: int = 30) -> str:
    """List the people in this Notion workspace.

    Use this to turn a name said out loud into somebody a page can be shared with or a
    person column can be set to.
    """
    found = notion().get("users", {"page_size": counted(limit)})

    return ok(
        [
            {
                "id": each.get("id"),
                "name": each.get("name"),
                "kind": each.get("type"),
                "email": ((each.get("person") or {}) or {}).get("email"),
            }
            for each in found.get("results", [])
            if each.get("type") != "bot"
        ]
    )


@mcp.tool()
def get_teams(limit: int = 20) -> str:
    """List the teamspaces this workspace has, which are what pages are shared inside.

    A teamspace is Notion's group of people and the pages they share.
    """
    found = notion().get("teamspaces", {"page_size": counted(limit)})

    return ok(
        [
            {"id": each.get("id"), "name": each.get("name"), "kind": each.get("type")}
            for each in found.get("results", [])
        ]
    )


# ══ FILES ══


@mcp.tool()
def create_file_upload(filename: str, kind: str = "") -> str:
    """Ask Notion for somewhere to put a file, which is the first half of attaching one.

    kind is the content type like image/png. What comes back is an id and an address the
    file itself is then POSTed to; create_attachment puts the result on a page.
    """
    wanted = {"filename": filename, "mode": "single_part"}

    if kind:
        wanted["content_type"] = kind

    made = notion().post("file_uploads", wanted)

    return ok({"upload": made.get("id"), "post_to": made.get("upload_url"),
               "state": made.get("status")})


@mcp.tool()
def create_attachment(page_id: str, upload_id: str, caption: str = "") -> str:
    """Put an uploaded file onto a page.

    upload_id is what create_file_upload gave back, after the file itself has been sent to
    the address it named. page_id is the page it lands on.
    """
    block = {
        "object": "block",
        "type": "file",
        "file": {"type": "file_upload", "file_upload": {"id": upload_id}},
    }

    if caption:
        block["file"]["caption"] = [{"type": "text", "text": {"content": caption}}]

    added = notion().patch(f"blocks/{page_id}/children", {"children": [block]})

    return ok({"attached": len(added.get("results", [])), "on": page_id})


@mcp.tool()
def download_attachment(block_id: str) -> str:
    """Get the address a file on a page can be fetched from.

    block_id is the block the file sits in. Notion signs these addresses and they go stale
    within the hour, so it is fetched soon after asking or asked for again.
    """
    found = notion().get(f"blocks/{block_id}")
    kind = found.get("type")
    held = found.get(kind) or {}
    where = (held.get("file") or {}).get("url") or (held.get("external") or {}).get("url")

    if not where:
        raise LookupError("That block holds no file.")

    return ok({"url": where, "kind": kind, "name": joined(held.get("caption") or [])})



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


def counted(limit):
    return max(1, min(int(limit), 100))


def identified(said):
    """AN ID OUT OF WHATEVER WAS PASTED: A NOTION LINK ENDS IN ONE, WITHOUT ITS HYPHENS."""
    wanted = str(said or "").strip().rstrip("/")

    if "/" in wanted:
        wanted = wanted.split("/")[-1].split("?")[0]

    if "-" in wanted and len(wanted) > 32:
        wanted = wanted.rsplit("-", 1)[-1]

    return wanted


# WHAT A COLUMN CAN BE, AND THE EMPTY SHAPE NOTION WANTS FOR EACH ONE.
COLUMNS = {
    "title": {"title": {}},
    "text": {"rich_text": {}},
    "number": {"number": {}},
    "select": {"select": {}},
    "multi_select": {"multi_select": {}},
    "date": {"date": {}},
    "people": {"people": {}},
    "checkbox": {"checkbox": {}},
    "url": {"url": {}},
    "email": {"email": {}},
    "phone": {"phone_number": {}},
    "files": {"files": {}},
}


def shaped(columns, titled_first=True):
    """COLUMNS WRITTEN name:kind PER LINE, AS THE PROPERTY MAP NOTION WANTS."""
    made = {"Name": {"title": {}}} if titled_first else {}

    for line in str(columns or "").split("\n"):
        if not line.strip():
            continue

        name, _, kind = line.partition(":")
        name = name.strip()
        kind = (kind or "text").strip().lower()

        if not name or name == "Name":
            continue

        made[name] = COLUMNS.get(kind, {"rich_text": {}})

    return made


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
