"""THE JIRA SERVER: WHAT IS IN THE BACKLOG, WHO HAS IT, AND MOVING IT ALONG."""

import base64
import sys
from pathlib import Path

# THE SERVER'S OWN FOLDER COMES OFF THE PATH SO A FILE BESIDE THIS ONE CAN NEVER
# BE WHAT SOME LIBRARY'S import FINDS FIRST.
sys.path[0] = str(Path(__file__).resolve().parents[2])

from mcp.server.fastmcp import FastMCP  # noqa: E402

from servers.shared import credentials  # noqa: E402
from servers.shared.answering import ok, some  # noqa: E402
from servers.shared.reaching import Service  # noqa: E402

mcp = FastMCP("jira", log_level="ERROR")

NAME = "jira"

MISSING = (
    "Jira is not connected. Paste your site, your email and an API token in Happy's "
    "connections panel."
)

# EVERY COMPANY'S JIRA IS AT ITS OWN ADDRESS, SO THE SITE IS PASTED ALONGSIDE THE TOKEN.
UNSITED = "Jira has no site. Paste the one ending atlassian.net in Happy's connections panel."

# VERSION 3 IS THE ONE THAT SPEAKS THE DOCUMENT FORMAT BELOW; 2 TAKES PLAIN STRINGS AND IS
# DEPRECATED ON CLOUD.
API = "rest/api/3"

# ONLY WHAT IS WORTH SAYING. ASKING FOR EVERYTHING BRINGS BACK A QUARTER MEGABYTE PER ISSUE.
FIELDS = "summary,status,assignee,reporter,priority,issuetype,project,created,updated,duedate"

WHOLE = FIELDS + ",description,labels,parent,subtasks"

MOST = 50


@mcp.tool()
def list_issues(project: str = "", assignee: str = "", status: str = "", limit: int = 20) -> str:
    """List issues in the backlog, most recently changed first.

    Every narrowing is optional and they stack. project is a key like ENG. assignee is a
    person's name, or "me" for whoever the token belongs to. status is the column — "To Do",
    "In Progress", "Done".

    Use this for "what is assigned to me", "what is open in ENG". For words inside an
    issue's summary or description, search_issues is the one that looks there.
    """
    wheres = []

    if project:
        wheres.append(f"project = {quoted(project)}")

    if assignee:
        wheres.append(
            "assignee = currentUser()"
            if assignee.strip().lower() in ("me", "mine", "myself")
            else f"assignee in ({quoted(assignee)})"
        )

    if status:
        wheres.append(f"status = {quoted(status)}")

    return ok(hunted(" AND ".join(wheres), limit))


@mcp.tool()
def search_issues(text: str, limit: int = 20) -> str:
    """Find issues with words in their summary or description, when the key is not known.

    text is what to look for — "the login bug", "onboarding email". This is the only tool
    that reads the words inside an issue, so anything phrased as "the ticket about X" comes
    here rather than to list_issues.
    """
    return ok(hunted(f"text ~ {quoted(text)}", limit))


@mcp.tool()
def read_issue(issue: str) -> str:
    """Read one issue whole: its description, labels, parent, subtasks and dates.

    issue is the key, which is the project and a number — ENG-42. The other tools give it
    back on every row. Comments are not in here; read_comments has those.
    """
    found = asked(f"issue/{keyed(issue)}", {"fields": WHOLE})
    fields = found.get("fields") or {}

    return ok(
        {
            **outlined(found),
            "description": some(flattened(fields.get("description")), 1500),
            "labels": fields.get("labels") or [],
            "parent": ((fields.get("parent") or {}).get("key")),
            "subtasks": [each.get("key") for each in (fields.get("subtasks") or [])],
            "reporter": ((fields.get("reporter") or {}) or {}).get("displayName"),
            "due": fields.get("duedate"),
            "made": fields.get("created"),
            "changed": fields.get("updated"),
        }
    )


@mcp.tool()
def read_comments(issue: str, limit: int = 20) -> str:
    """Read what people have said under an issue, oldest first.

    issue is the key like ENG-42. This is where the discussion is: the issue's own
    description is what it was raised with, and read_issue has that.
    """
    found = asked(f"issue/{keyed(issue)}/comment", {"maxResults": counted(limit)})

    return ok(
        [
            {
                "by": ((each.get("author") or {}) or {}).get("displayName"),
                "at": each.get("created"),
                "said": some(flattened(each.get("body")), 600),
            }
            for each in found.get("comments", [])
        ]
    )


@mcp.tool()
def list_projects(limit: int = 20) -> str:
    """List the projects on this Jira site, with the key each one is named by.

    A key like ENG is what list_issues and create_issue want. Ask this first when a project
    has been named out loud and its exact key is not known.
    """
    found = asked("project/search", {"maxResults": counted(limit)})

    return ok(
        [
            {
                "key": each.get("key"),
                "name": each.get("name"),
                "kind": each.get("projectTypeKey"),
                "lead": ((each.get("lead") or {}) or {}).get("displayName"),
            }
            for each in found.get("values", [])
        ]
    )


@mcp.tool()
def list_moves(issue: str) -> str:
    """List the columns an issue can move to from where it is now.

    issue is the key like ENG-42. Jira only allows the moves its own workflow permits, so
    these are the only words move_issue will take for this issue. Ask this before moving one.
    """
    found = asked(f"issue/{keyed(issue)}/transitions")

    return ok(
        [
            {"to": ((each.get("to") or {}) or {}).get("name"), "called": each.get("name")}
            for each in found.get("transitions", [])
        ]
    )


@mcp.tool()
def create_issue(project: str, summary: str, description: str = "", kind: str = "Task") -> str:
    """Raise a new issue in a project and give back its key.

    project is the key like ENG, which list_projects gives back. kind is the issue type —
    Task, Bug, Story — and a project only takes the ones it has been set up with. It is
    raised unassigned and in that workflow's first column.
    """
    wanted = {
        "project": {"key": keyed(project)},
        "summary": summary,
        "issuetype": {"name": kind},
    }

    if description:
        wanted["description"] = written(description)

    made = told("issue", {"fields": wanted})

    return ok({"id": made.get("key"), "url": browsing(made.get("key"))})


@mcp.tool()
def move_issue(issue: str, state: str) -> str:
    """Move an issue to another column on its own project's board.

    issue is the key like ENG-42, and state is the column to land in — "In Progress",
    "Done". Jira's workflow decides which moves are allowed from where the issue is now, so
    list_moves is what says which words it will take.
    """
    key = keyed(issue)
    wanted = str(state or "").strip().lower()
    moves = asked(f"issue/{key}/transitions").get("transitions", [])

    for each in moves:
        landing = ((each.get("to") or {}) or {}).get("name") or ""

        if wanted in (str(landing).lower(), str(each.get("name") or "").lower()):
            told(f"issue/{key}/transitions", {"transition": {"id": each["id"]}})

            return ok({"id": key, "state": landing})

    allowed = [((each.get("to") or {}) or {}).get("name") for each in moves]

    raise LookupError(f"{key} cannot move to {state} from where it is. It can go to {allowed}.")


@mcp.tool()
def comment_on_issue(issue: str, text: str) -> str:
    """Say something under an issue, as whoever the token belongs to.

    issue is the key like ENG-42. This posts as a real comment that everybody on the project
    sees, so it is said once and cannot be taken back from here.
    """
    key = keyed(issue)

    told(f"issue/{key}/comment", {"body": written(text)})

    return ok({"on": key, "said": some(text, 200)})


def who_signed_in() -> str:
    """THE NAME ON THIS ACCOUNT. HAPPY ASKS IT HIMSELF; IT IS NEVER OFFERED TO THE MODEL."""
    who = asked("myself")

    return f"{who.get('displayName') or who.get('emailAddress') or ''} on {sited()}".strip()


# ── ASKING JIRA ──


def jira():
    held = credentials.kept(NAME)
    token = (held.get("tokens") or {}).get("access_token") or ""
    beside = held.get("client") or {}
    email = str(beside.get("email") or "").strip()

    if not token or not email:
        raise PermissionError(MISSING)

    # ATLASSIAN CLOUD TAKES THE TOKEN AS THE PASSWORD HALF OF ORDINARY BASIC AUTH, NEVER
    # AS A BEARER: A BEARER THERE MEANS AN OAUTH TOKEN, WHICH THIS IS NOT.
    signed = base64.b64encode(f"{email}:{token}".encode("utf-8")).decode("ascii")

    return Service(
        f"https://{sited()}/{API}",
        {
            "Authorization": f"Basic {signed}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        "Jira",
    )


def sited():
    """THE COMPANY'S OWN JIRA ADDRESS, WITHOUT WHATEVER WAS PASTED AROUND IT."""
    held = (credentials.kept(NAME).get("client") or {}).get("site") or ""
    where = str(held).strip().replace("https://", "").replace("http://", "").strip("/")

    if not where:
        raise PermissionError(UNSITED)

    return where


def asked(path, params=None):
    return jira().get(path, params)


def told(path, body):
    return jira().post(path, body)


def hunted(where, limit):
    """ONE JQL SEARCH, ORDERED THE ONE WAY ANYBODY ASKING OUT LOUD WANTS IT."""
    said = f"{where} ORDER BY updated DESC" if where else "ORDER BY updated DESC"
    found = asked("search/jql", {"jql": said, "maxResults": counted(limit), "fields": FIELDS})

    return [outlined(each) for each in found.get("issues", [])]


# ── WHAT A ROW LOOKS LIKE ──


def outlined(issue):
    """ONE ISSUE, SAID THE SAME WAY BY EVERY TOOL THAT HANDS ONE BACK."""
    fields = issue.get("fields") or {}

    return {
        "id": issue.get("key"),
        "title": some(fields.get("summary"), 200),
        "state": ((fields.get("status") or {}) or {}).get("name"),
        "priority": ((fields.get("priority") or {}) or {}).get("name"),
        "assignee": ((fields.get("assignee") or {}) or {}).get("displayName"),
        "kind": ((fields.get("issuetype") or {}) or {}).get("name"),
        "project": ((fields.get("project") or {}) or {}).get("key"),
        "url": browsing(issue.get("key")),
    }


def browsing(key):
    """WHERE A PERSON WOULD OPEN THIS ISSUE, WHICH THE API NEVER HANDS BACK ITSELF."""
    try:
        return f"https://{sited()}/browse/{key}" if key else None
    except PermissionError:
        return None


def written(text):
    """PLAIN WORDS AS THE DOCUMENT FORMAT VERSION 3 INSISTS ON, WHICH IS THE ONLY WAY IN."""
    return {
        "type": "doc",
        "version": 1,
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": str(text)}]}],
    }


def flattened(document):
    """THE WORDS BACK OUT OF THAT SAME FORMAT, WHICH NESTS THEM ARBITRARILY DEEP."""
    if document is None:
        return ""

    if isinstance(document, str):
        return document

    if isinstance(document, list):
        return " ".join(flattened(each) for each in document)

    if not isinstance(document, dict):
        return ""

    if document.get("type") == "text":
        return document.get("text") or ""

    return flattened(document.get("content"))


def quoted(said):
    """A VALUE INSIDE JQL, WITH THE QUOTES THAT WOULD END IT EARLY TAKEN OUT."""
    return '"' + str(said or "").replace('\\', '').replace('"', '') + '"'


def keyed(issue):
    """A KEY AS JIRA WANTS IT: ENG-42, NOT eng-42 AND NOT " ENG-42"."""
    return str(issue or "").strip().upper()


def counted(limit):
    return max(1, min(int(limit), MOST))


if __name__ == "__main__":
    mcp.run()
