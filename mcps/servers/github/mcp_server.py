"""THE GITHUB SERVER: FINDING REPOSITORIES, READING THEM, AND THEIR ISSUES."""

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

mcp = FastMCP("github", log_level="ERROR")

NAME = "github"

BASE = "https://api.github.com"

# PINNING THE VERSION KEEPS A RESPONSE THE SHAPE THESE TOOLS EXPECT WHEN GITHUB
# CHANGES ITS DEFAULT ONE.
VERSION = "2022-11-28"

MISSING = "GitHub is not connected. Paste a personal access token in Happy's connections panel."

MOST_BODY = 4000


@mcp.tool()
def list_repositories(limit: int = 10) -> str:
    """List this account's own repositories, most recently pushed to first."""
    found = github().get(
        "user/repos", {"sort": "pushed", "per_page": counted(limit), "affiliation": "owner"}
    )

    return ok([repository(each) for each in found])


@mcp.tool()
def search_repositories(query: str, limit: int = 10) -> str:
    """Search all of GitHub for repositories, most starred first.

    The query is GitHub's own search, so `language:python stars:>500` works.
    """
    found = github().get(
        "search/repositories", {"q": query, "sort": "stars", "per_page": counted(limit)}
    )

    return ok([repository(each) for each in found.get("items", [])])


@mcp.tool()
def read_file(repo: str, path: str, ref: str = "") -> str:
    """Read one file out of a repository. repo is owner/name, like torvalds/linux.

    ref is a branch, tag or commit, and left empty it reads the default branch.
    """
    found = github().get(f"repos/{repo}/contents/{path}", {"ref": ref} if ref else None)

    if isinstance(found, list):
        return ok({"repo": repo, "path": path, "folder": [each["name"] for each in found]})

    return ok({"repo": repo, "path": path, "body": decoded(found.get("content", ""))[:MOST_BODY]})


@mcp.tool()
def list_issues(repo: str, state: str = "open", limit: int = 10) -> str:
    """List a repository's issues. state is open, closed or all.

    Pull requests are left out; list_pull_requests has those.
    """
    found = github().get(
        f"repos/{repo}/issues", {"state": state or "open", "per_page": counted(limit)}
    )

    return ok([issue(each) for each in found if "pull_request" not in each])


@mcp.tool()
def search_issues(query: str, limit: int = 10) -> str:
    """Search issues and pull requests across GitHub.

    The query is GitHub's own, so `repo:owner/name is:open label:bug` works.
    """
    found = github().get("search/issues", {"q": query, "per_page": counted(limit)})

    return ok([issue(each) for each in found.get("items", [])])


@mcp.tool()
def create_issue(repo: str, title: str, body: str = "") -> str:
    """Open an issue on a repository. Everybody watching it is told.

    Say which repository and what the issue says before calling this.
    """
    made = github().post(f"repos/{repo}/issues", {"title": title, "body": body})

    return ok({"created": True, "number": made.get("number"), "url": made.get("html_url")})


@mcp.tool()
def list_pull_requests(repo: str, state: str = "open", limit: int = 10) -> str:
    """List a repository's pull requests. state is open, closed or all."""
    found = github().get(
        f"repos/{repo}/pulls", {"state": state or "open", "per_page": counted(limit)}
    )

    return ok([issue(each) for each in found])


@mcp.tool()
def list_commits(repo: str, limit: int = 10) -> str:
    """List the most recent commits on a repository's default branch."""
    found = github().get(f"repos/{repo}/commits", {"per_page": counted(limit)})

    return ok([commit(each) for each in found])


@mcp.tool()
def who_signed_in() -> str:
    """THE NAME ON THIS ACCOUNT. HAPPY ASKS IT HIMSELF; IT IS NEVER OFFERED TO THE MODEL."""
    found = github().get("user")

    return str(found.get("name") or found.get("login") or "").strip()


def github():
    token = credentials.token(NAME)

    if not token:
        raise PermissionError(MISSING)

    return Service(
        BASE,
        {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": VERSION,
        },
        "GitHub",
    )


def repository(each):
    return {
        "repo": each.get("full_name"),
        "about": some(each.get("description", ""), 160),
        "language": each.get("language"),
        "stars": each.get("stargazers_count"),
        "private": each.get("private"),
        "url": each.get("html_url"),
    }


def issue(each):
    return {
        "number": each.get("number"),
        "title": some(each.get("title", ""), 160),
        "state": each.get("state"),
        "by": (each.get("user") or {}).get("login"),
        "comments": each.get("comments"),
        "opened": each.get("created_at"),
        "url": each.get("html_url"),
    }


def commit(each):
    written = each.get("commit") or {}

    return {
        "sha": (each.get("sha") or "")[:8],
        "message": some(written.get("message", ""), 160),
        "by": (written.get("author") or {}).get("name"),
        "at": (written.get("author") or {}).get("date"),
    }


def counted(limit):
    return max(1, min(int(limit), 25))


def decoded(content):
    return base64.b64decode(content).decode("utf-8", "replace")


if __name__ == "__main__":
    mcp.run()
