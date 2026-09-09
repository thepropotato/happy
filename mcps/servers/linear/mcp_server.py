"""THE LINEAR SERVER: WHAT IS ON THE BOARD, WHO HAS IT, AND MOVING IT ALONG."""

import sys
from pathlib import Path

# THE SERVER'S OWN FOLDER COMES OFF THE PATH SO A FILE BESIDE THIS ONE CAN NEVER
# BE WHAT SOME LIBRARY'S import FINDS FIRST.
sys.path[0] = str(Path(__file__).resolve().parents[2])

from mcp.server.fastmcp import FastMCP  # noqa: E402

from servers.linear import queries  # noqa: E402
from servers.shared import credentials  # noqa: E402
from servers.shared.answering import ok, some  # noqa: E402
from servers.shared.reaching import Service  # noqa: E402

mcp = FastMCP("linear", log_level="ERROR")

NAME = "linear"

# ONE ADDRESS FOR THE WHOLE API: LINEAR IS GRAPHQL, SO EVERY CALL IS A POST TO THIS.
BASE = "https://api.linear.app"

MISSING = "Linear is not connected. Paste a personal API key in Happy's connections panel."

# WHAT LINEAR CALLS THE FIVE PRIORITIES, WHICH IT STORES AS 0 TO 4 AND NEVER NAMES.
URGENCY = {0: "none", 1: "urgent", 2: "high", 3: "medium", 4: "low"}

WANTED = {name: number for number, name in URGENCY.items()}

MOST = 50


@mcp.tool()
def list_issues(assignee: str = "", team: str = "", state: str = "", limit: int = 20) -> str:
    """List issues on the board, most recently touched first.

    Every narrowing is optional and they stack. assignee is a person's name, or "me" for
    whoever the key belongs to. team is a team key like ENG. state is the status column,
    which is one of the words list_teams gives back for that team — "In Progress", "Done".

    Use this for "what am I working on", "what is open in ENG", "what is assigned to Priya".
    For words that appear inside an issue's title or text, search_issues is the one that
    looks there.
    """
    narrowed = {}

    if assignee:
        narrowed["assignee"] = (
            {"isMe": {"eq": True}}
            if assignee.strip().lower() in ("me", "mine", "myself")
            else {"name": {"containsIgnoreCase": assignee}}
        )

    if team:
        narrowed["team"] = {"key": {"eqIgnoreCase": team}}

    if state:
        narrowed["state"] = {"name": {"eqIgnoreCase": state}}

    found = asked(
        queries.ISSUES, {"filter": narrowed or None, "first": counted(limit)}
    )["issues"]["nodes"]

    return ok([outlined(each) for each in found])


@mcp.tool()
def search_issues(text: str, limit: int = 20) -> str:
    """Find issues with words in their title or description, when the issue is not known by id.

    text is what to look for — "the login bug", "onboarding email". This is the only tool
    that reads the text of an issue, so anything phrased as "the issue about X" comes here
    rather than to list_issues.
    """
    found = asked(queries.SEARCH, {"term": text, "first": counted(limit)})

    return ok([outlined(each) for each in found["searchIssues"]["nodes"]])


@mcp.tool()
def read_issue(issue: str) -> str:
    """Read one issue whole: its description, labels, project, cycle, estimate and dates.

    issue is the identifier, which is the team key and a number — ENG-42. The other tools
    give it back on every row. Comments are not in here; read_comments has those.
    """
    found = asked(queries.ONE_ISSUE, {"id": named(issue)})["issue"]

    if not found:
        raise LookupError(f"Linear has no issue called {issue}.")

    return ok(
        {
            **outlined(found),
            "description": some(found.get("description"), 1500),
            "project": ((found.get("project") or {}) or {}).get("name"),
            "cycle": ((found.get("cycle") or {}) or {}).get("name")
            or ((found.get("cycle") or {}) or {}).get("number"),
            "labels": [each["name"] for each in (found.get("labels") or {}).get("nodes", [])],
            "estimate": found.get("estimate"),
            "due": found.get("dueDate"),
            "made": found.get("createdAt"),
            "changed": found.get("updatedAt"),
        }
    )


@mcp.tool()
def read_comments(issue: str, limit: int = 20) -> str:
    """Read what people have said under an issue, oldest first.

    issue is the identifier like ENG-42. This is where the discussion is: the issue's own
    description is what it was opened with, and read_issue has that.
    """
    found = asked(queries.COMMENTS, {"id": named(issue), "first": counted(limit)})["issue"]

    if not found:
        raise LookupError(f"Linear has no issue called {issue}.")

    return ok(
        [
            {
                "by": ((each.get("user") or {}) or {}).get("name"),
                "at": each.get("createdAt"),
                "said": some(each.get("body"), 600),
            }
            for each in (found.get("comments") or {}).get("nodes", [])
        ]
    )


@mcp.tool()
def list_teams(limit: int = 20) -> str:
    """List the teams in this workspace, with the states each team's board actually has.

    A team key like ENG is what list_issues and create_issue want, and the state names are
    the only words move_issue will take for that team. Ask this first when a team or a
    column has been named out loud and its exact spelling is not known.
    """
    found = asked(queries.TEAMS, {"first": counted(limit)})["teams"]["nodes"]

    return ok(
        [
            {
                "key": each.get("key"),
                "name": each.get("name"),
                "about": some(each.get("description"), 120),
                "states": columns(each.get("key")),
            }
            for each in found
        ]
    )


@mcp.tool()
def list_projects(limit: int = 20) -> str:
    """List the projects, with how far along each one is and when it is due.

    Use this for "what projects are running", "how is the billing project going". A project
    is a body of work across issues; a cycle is a fixed run of days, and list_cycles has those.
    """
    found = asked(queries.PROJECTS, {"first": counted(limit)})["projects"]["nodes"]

    return ok(
        [
            {
                "name": each.get("name"),
                "state": each.get("state"),
                "done": portion(each.get("progress")),
                "target": each.get("targetDate"),
                "lead": ((each.get("lead") or {}) or {}).get("name"),
                "teams": [one["key"] for one in (each.get("teams") or {}).get("nodes", [])],
            }
            for each in found
        ]
    )


@mcp.tool()
def list_cycles(limit: int = 20) -> str:
    """List the cycles running right now, one per team, with how far through each one is.

    A cycle is Linear's sprint: a fixed run of days. Use this for "what is in this sprint",
    "how far through the cycle are we". Finished and future cycles are not listed.
    """
    found = asked(queries.CYCLES, {"first": counted(limit)})["cycles"]["nodes"]

    return ok(
        [
            {
                "team": ((each.get("team") or {}) or {}).get("key"),
                "number": each.get("number"),
                "name": each.get("name"),
                "from": each.get("startsAt"),
                "to": each.get("endsAt"),
                "done": portion(each.get("progress")),
            }
            for each in found
        ]
    )


@mcp.tool()
def create_issue(team: str, title: str, description: str = "", priority: str = "") -> str:
    """Open a new issue on a team's board and give back its identifier.

    team is the key like ENG, which list_teams gives back. priority is one of urgent, high,
    medium, low, and left out means none. It is created unassigned and in that team's first
    state; move_issue is what puts it somewhere else.
    """
    wanted = {"teamId": team_id(team), "title": title}

    if description:
        wanted["description"] = description

    if priority:
        wanted["priority"] = ranked(priority)

    done = asked(queries.NEW_ISSUE, {"input": wanted})["issueCreate"]

    if not done.get("success"):
        raise PermissionError("Linear would not open that issue.")

    return ok(outlined(done["issue"]))


@mcp.tool()
def move_issue(issue: str, state: str) -> str:
    """Move an issue to another column on its own team's board.

    issue is the identifier like ENG-42, and state is the column's name — "In Progress",
    "Done", "Cancelled". The names differ per team, so list_teams is what says which words
    that team's board will take.
    """
    found = asked(queries.ONE_ISSUE, {"id": named(issue)})["issue"]

    if not found:
        raise LookupError(f"Linear has no issue called {issue}.")

    key = ((found.get("team") or {}) or {}).get("key")
    wanted = state_id(key, state)

    if not wanted:
        raise LookupError(f"{key} has no column called {state}. Its own are {columns(key)}.")

    done = asked(queries.MOVE_ISSUE, {"id": found["id"], "input": {"stateId": wanted}})

    if not done["issueUpdate"].get("success"):
        raise PermissionError(f"Linear would not move {issue}.")

    return ok(outlined(done["issueUpdate"]["issue"]))


@mcp.tool()
def comment_on_issue(issue: str, text: str) -> str:
    """Say something under an issue, as whoever the key belongs to.

    issue is the identifier like ENG-42. This posts as a real comment that everybody on the
    team sees, so it is said once and cannot be taken back from here.
    """
    found = asked(queries.ONE_ISSUE, {"id": named(issue)})["issue"]

    if not found:
        raise LookupError(f"Linear has no issue called {issue}.")

    done = asked(queries.NEW_COMMENT, {"input": {"issueId": found["id"], "body": text}})

    if not done["commentCreate"].get("success"):
        raise PermissionError(f"Linear would not comment on {issue}.")

    return ok({"on": found.get("identifier"), "said": some(text, 200)})


def who_signed_in() -> str:
    """THE NAME ON THIS ACCOUNT. HAPPY ASKS IT HIMSELF; IT IS NEVER OFFERED TO THE MODEL."""
    found = asked(queries.ME)
    who = found.get("viewer") or {}
    where = found.get("organization") or {}

    return f"{who.get('name') or who.get('email') or ''} at {where.get('name') or 'Linear'}".strip()


# ── ASKING LINEAR ──


def linear():
    token = credentials.token(NAME)

    if not token:
        raise PermissionError(MISSING)

    # THE KEY GOES IN BARE, WITHOUT A Bearer IN FRONT: A PERSONAL KEY IS NOT ONE, AND
    # LINEAR ANSWERS 400 RATHER THAN 401 WHEN IT IS DRESSED UP AS ONE.
    return Service(BASE, {"Authorization": token, "Content-Type": "application/json"}, "Linear")


def asked(query, variables=None):
    """ONE GRAPHQL CALL. A GRAPHQL SERVER ANSWERS 200 WITH THE TROUBLE IN THE BODY."""
    answer = linear().post("graphql", {"query": query, "variables": variables or {}})

    if answer.get("errors"):
        raise PermissionError(f"Linear said no. {complaint(answer['errors'])}")

    return answer.get("data") or {}


def complaint(errors):
    said = [str((each or {}).get("message") or "").strip() for each in errors]

    return some(" ".join(one for one in said if one) or "it did not say why", 200)


# ── WHAT A ROW LOOKS LIKE ──


def outlined(issue):
    """ONE ISSUE, SAID THE SAME WAY BY EVERY TOOL THAT HANDS ONE BACK."""
    return {
        "id": issue.get("identifier"),
        "title": some(issue.get("title"), 200),
        "state": ((issue.get("state") or {}) or {}).get("name"),
        "priority": URGENCY.get(issue.get("priority")),
        "assignee": ((issue.get("assignee") or {}) or {}).get("name"),
        "team": ((issue.get("team") or {}) or {}).get("key"),
        "url": issue.get("url"),
    }


def portion(fraction):
    """LINEAR COUNTS PROGRESS 0 TO 1, AND NOBODY SAYS "NOUGHT POINT SIX" OUT LOUD."""
    try:
        return f"{round(float(fraction) * 100)}%"
    except (TypeError, ValueError):
        return None


def named(issue):
    """AN IDENTIFIER AS LINEAR WANTS IT: ENG-42, NOT eng-42 AND NOT " ENG-42"."""
    return str(issue or "").strip().upper()


def ranked(priority):
    wanted = WANTED.get(str(priority or "").strip().lower())

    if wanted is None:
        raise LookupError(f"Priority is one of {', '.join(WANTED)}.")

    return wanted


def counted(limit):
    return max(1, min(int(limit), MOST))


# ── THE TEAMS AND THEIR COLUMNS, ASKED ONCE AND KEPT FOR THIS PROCESS ──

known = {}


def teams():
    if not known:
        for each in asked(queries.TEAMS, {"first": MOST})["teams"]["nodes"]:
            known[str(each["key"]).upper()] = each

    return known


def team_id(team):
    found = teams().get(str(team or "").strip().upper())

    if not found:
        raise LookupError(f"There is no team called {team}. There are {', '.join(teams())}.")

    return found["id"]


def columns(team):
    """THE STATE NAMES ONE TEAM'S BOARD HAS, WHICH DIFFER PER TEAM."""
    found = asked(queries.STATES, {"team": team_id(team)})["team"]

    return [each["name"] for each in (found.get("states") or {}).get("nodes", [])]


def state_id(team, state):
    wanted = str(state or "").strip().lower()
    found = asked(queries.STATES, {"team": team_id(team)})["team"]

    for each in (found.get("states") or {}).get("nodes", []):
        if str(each["name"]).lower() == wanted:
            return each["id"]

    return None


if __name__ == "__main__":
    mcp.run()
