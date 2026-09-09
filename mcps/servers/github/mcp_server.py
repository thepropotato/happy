"""THE GITHUB SERVER: REPOSITORIES, WHAT IS IN THEM, AND EVERYTHING AROUND THEM.

GITHUB'S OWN SERVER OFFERS NINETY-FOUR TOOLS. FOUR OF THEM HAVE NO PUBLIC REST ENDPOINT —
THE THREE COPILOT AGENT ONES, WHICH DRIVE GITHUB'S OWN AGENT AND ANSWER 404 TO ANYBODY ELSE,
AND github_support_docs_search, WHICH READS GITHUB'S HELP SITE RATHER THAN AN ACCOUNT. THE
REST ARE HERE, AND THE SERVICE GOES BEHIND ONE DOOR IN mcps/opening.py BECAUSE NINETY SCHEMAS
IN FRONT OF THE PREFIX CACHE WOULD COST EVERY TURN THAT IS NOT ABOUT GITHUB."""

import base64
import sys
from pathlib import Path

# THE SERVER'S OWN FOLDER COMES OFF THE PATH SO A FILE BESIDE THIS ONE CAN NEVER
# BE WHAT SOME LIBRARY'S import FINDS FIRST.
sys.path[0] = str(Path(__file__).resolve().parents[2])

from mcp.server.fastmcp import FastMCP  # noqa: E402

from servers.github import shapes  # noqa: E402
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

    return ok([shapes.repository(each) for each in found])


@mcp.tool()
def search_repositories(query: str, limit: int = 10) -> str:
    """Search all of GitHub for repositories, most starred first.

    The query is GitHub's own search, so `language:python stars:>500` works.
    """
    found = github().get(
        "search/repositories", {"q": query, "sort": "stars", "per_page": counted(limit)}
    )

    return ok([shapes.repository(each) for each in found.get("items", [])])


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

    return ok([shapes.issue(each) for each in found if "pull_request" not in each])


@mcp.tool()
def search_issues(query: str, limit: int = 10) -> str:
    """Search issues and pull requests across GitHub.

    The query is GitHub's own, so `repo:owner/name is:open label:bug` works.
    """
    found = github().get("search/issues", {"q": query, "per_page": counted(limit)})

    return ok([shapes.issue(each) for each in found.get("items", [])])


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

    return ok([shapes.issue(each) for each in found])


@mcp.tool()
def list_commits(repo: str, limit: int = 10) -> str:
    """List the most recent commits on a repository's default branch."""
    found = github().get(f"repos/{repo}/commits", {"per_page": counted(limit)})

    return ok([shapes.commit(each) for each in found])



# ══ DISCUSSIONS ══


@mcp.tool()
def list_discussions(repo: str, limit: int = 20) -> str:
    """List a repository's discussions, which are its conversations rather than its issues.

    repo is owner/name. Not every repository has them switched on; one that has not says so.
    """
    found = github().get(f"repos/{repo}/discussions", {"per_page": counted(limit)})

    return ok([shapes.discussion(each) for each in found])


@mcp.tool()
def get_discussion(repo: str, number: int) -> str:
    """Read one discussion whole, with what it was opened with.

    number is the discussion's. get_discussion_comments is the one for the replies.
    """
    found = github().get(f"repos/{repo}/discussions/{number}")

    return ok({**shapes.discussion(found), "body": some(found.get("body"), MOST_BODY)})


@mcp.tool()
def get_discussion_comments(repo: str, number: int, limit: int = 30) -> str:
    """Read the replies on a discussion, oldest first.

    number is the discussion's.
    """
    found = github().get(
        f"repos/{repo}/discussions/{number}/comments", {"per_page": counted(limit)}
    )

    return ok(
        [
            {
                "id": each.get("id"),
                "by": ((each.get("user") or {}) or {}).get("login"),
                "at": each.get("created_at"),
                "said": some(each.get("body"), 600),
            }
            for each in found
        ]
    )


@mcp.tool()
def list_discussion_categories(repo: str) -> str:
    """List the categories a repository sorts its discussions into.

    A category is what a discussion is filed under — Q&A, Ideas, Show and tell.
    """
    found = github().get(f"repos/{repo}/discussions/categories")

    return ok(
        [
            {"id": each.get("id"), "name": each.get("name"),
             "about": some(each.get("description"), 150)}
            for each in (found if isinstance(found, list) else found.get("categories", []))
        ]
    )


@mcp.tool()
def discussion_comment_write(repo: str, number: int, body: str) -> str:
    """Reply to a discussion.

    number is the discussion's. It is posted as whoever the token belongs to and everybody
    watching is told.
    """
    made = github().post(f"repos/{repo}/discussions/{number}/comments", {"body": body})

    return ok({"comment": made.get("id"), "on": number})


# ══ NOTIFICATIONS ══


@mcp.tool()
def list_notifications(unread: bool = True, limit: int = 30) -> str:
    """Read what GitHub has been trying to tell whoever the token belongs to.

    unread being true, which it is unless said otherwise, leaves out what has been read. Use
    this for "anything from GitHub", "what did I miss".
    """
    found = github().get("notifications", {"all": not unread, "per_page": counted(limit)})

    return ok([shapes.notification(each) for each in found])


@mcp.tool()
def get_notification_details(notification: str) -> str:
    """Read one notification, with what it is actually about.

    notification is the id list_notifications gives back.
    """
    found = github().get(f"notifications/threads/{notification}")

    return ok(shapes.notification(found))


@mcp.tool()
def dismiss_notification(notification: str) -> str:
    """Mark one notification read, so it stops coming back.

    notification is the id list_notifications gives back.
    """
    github().patch(f"notifications/threads/{notification}", {})

    return ok({"dismissed": notification})


@mcp.tool()
def mark_all_notifications_read() -> str:
    """Mark every notification read at once.

    Use this only when somebody has said to clear the lot: nothing here can put them back.
    """
    github().sent("PUT", "notifications", json={"read": True})

    return ok({"cleared": True})


@mcp.tool()
def manage_notification_subscription(notification: str, ignored: bool = False,
                                     stop: bool = False) -> str:
    """Say whether to keep hearing about one thread.

    ignored mutes it while leaving it there; stop unsubscribes altogether.
    """
    if stop:
        github().sent("DELETE", f"notifications/threads/{notification}/subscription")

        return ok({"unsubscribed": notification})

    github().sent(
        "PUT", f"notifications/threads/{notification}/subscription",
        json={"ignored": bool(ignored)},
    )

    return ok({"thread": notification, "muted": bool(ignored)})


@mcp.tool()
def manage_repository_notification_subscription(repo: str, watching: bool = True,
                                                ignored: bool = False) -> str:
    """Say whether to hear about everything in a repository.

    watching means every conversation in it; ignored mutes the lot. Both false stops
    watching without muting.
    """
    if not watching and not ignored:
        github().sent("DELETE", f"repos/{repo}/subscription")

        return ok({"repo": repo, "watching": False})

    github().sent(
        "PUT", f"repos/{repo}/subscription",
        json={"subscribed": bool(watching), "ignored": bool(ignored)},
    )

    return ok({"repo": repo, "watching": bool(watching), "muted": bool(ignored)})


# ══ SECURITY ══


@mcp.tool()
def list_code_scanning_alerts(repo: str, state: str = "open", limit: int = 20) -> str:
    """List what GitHub's code scanning has found in a repository.

    state is open, fixed or dismissed. These are findings in the code itself, which is not
    the same as a vulnerable dependency — list_dependabot_alerts has those.
    """
    found = github().get(
        f"repos/{repo}/code-scanning/alerts", {"state": state, "per_page": counted(limit)}
    )

    return ok([shapes.alert(each) for each in found])


@mcp.tool()
def get_code_scanning_alert(repo: str, number: int) -> str:
    """Read one code scanning finding, with where in the code it is.

    number is the alert's, which list_code_scanning_alerts gives back.
    """
    return ok(shapes.alert(github().get(f"repos/{repo}/code-scanning/alerts/{number}")))


@mcp.tool()
def list_dependabot_alerts(repo: str, state: str = "open", limit: int = 20) -> str:
    """List the vulnerable dependencies GitHub has found in a repository.

    state is open, fixed, dismissed or auto_dismissed. These are libraries the repository
    depends on, not its own code.
    """
    found = github().get(
        f"repos/{repo}/dependabot/alerts", {"state": state, "per_page": counted(limit)}
    )

    return ok([shapes.alert(each) for each in found])


@mcp.tool()
def get_dependabot_alert(repo: str, number: int) -> str:
    """Read one dependency alert, with which package and which version fixes it.

    number is the alert's.
    """
    return ok(shapes.alert(github().get(f"repos/{repo}/dependabot/alerts/{number}")))


@mcp.tool()
def list_secret_scanning_alerts(repo: str, state: str = "open", limit: int = 20) -> str:
    """List the secrets GitHub has found committed into a repository.

    state is open or resolved. A hit here is a key or token somebody pushed by accident, and
    it is worth saying plainly rather than burying.
    """
    found = github().get(
        f"repos/{repo}/secret-scanning/alerts", {"state": state, "per_page": counted(limit)}
    )

    return ok([shapes.alert(each) for each in found])


@mcp.tool()
def get_secret_scanning_alert(repo: str, number: int) -> str:
    """Read one secret scanning alert, with what kind of secret it is.

    number is the alert's. The secret itself is not handed back.
    """
    return ok(shapes.alert(github().get(f"repos/{repo}/secret-scanning/alerts/{number}")))


@mcp.tool()
def get_code_quality_finding(repo: str, number: int) -> str:
    """Read one code quality finding, which is a smell rather than a vulnerability.

    number is the finding's. Not every repository has this switched on.
    """
    return ok(shapes.alert(github().get(f"repos/{repo}/code-quality/findings/{number}")))


@mcp.tool()
def list_global_security_advisories(text: str = "", severity: str = "", limit: int = 20) -> str:
    """Search GitHub's whole database of known vulnerabilities, across every project.

    text narrows by what is written in them and severity is low, medium, high or critical.
    This is the public list, not anything about one repository.
    """
    wanted = {"per_page": counted(limit)}

    if text:
        wanted["query"] = text

    if severity:
        wanted["severity"] = severity

    return ok([shapes.advisory(each) for each in github().get("advisories", wanted)])


@mcp.tool()
def get_global_security_advisory(advisory: str) -> str:
    """Read one published vulnerability by its GHSA number.

    advisory is like GHSA-xxxx-xxxx-xxxx.
    """
    return ok(shapes.advisory(github().get(f"advisories/{advisory}")))


@mcp.tool()
def list_repository_security_advisories(repo: str, limit: int = 20) -> str:
    """List the advisories a repository has written about itself.

    These are ones its own maintainers published, which is not the same as what was found in it.
    """
    found = github().get(f"repos/{repo}/security-advisories", {"per_page": counted(limit)})

    return ok([shapes.advisory(each) for each in found])


@mcp.tool()
def list_org_repository_security_advisories(owner: str, limit: int = 20) -> str:
    """List the advisories every repository in an organisation has published.

    owner is the organisation's name.
    """
    found = github().get(f"orgs/{owner}/security-advisories", {"per_page": counted(limit)})

    return ok([shapes.advisory(each) for each in found])


@mcp.tool()
def repository_ruleset_read(repo: str, ruleset: str = "") -> str:
    """Read the rules a repository enforces on its branches.

    Left without a ruleset it lists them; with one it reads that rule whole. These are what
    stop a push or require a review.
    """
    if ruleset:
        found = github().get(f"repos/{repo}/rulesets/{ruleset}")

        return ok(
            {
                "id": found.get("id"),
                "name": found.get("name"),
                "state": found.get("enforcement"),
                "rules": [each.get("type") for each in (found.get("rules") or [])],
            }
        )

    found = github().get(f"repos/{repo}/rulesets", {"per_page": 50})

    return ok(
        [
            {"id": each.get("id"), "name": each.get("name"), "state": each.get("enforcement")}
            for each in found
        ]
    )


@mcp.tool()
def create_repository_ruleset(repo: str, name: str, rules: str, enforce: bool = True) -> str:
    """Put a rule on a repository's branches.

    rules is comma separated — deletion, non_fast_forward, required_signatures,
    pull_request. enforce being false makes it a rule that reports rather than blocks.
    """
    made = github().post(
        f"repos/{repo}/rulesets",
        {
            "name": name,
            "target": "branch",
            "enforcement": "active" if enforce else "evaluate",
            "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
            "rules": [{"type": each} for each in split(rules)],
        },
    )

    return ok({"id": made.get("id"), "name": made.get("name"), "state": made.get("enforcement")})


@mcp.tool()
def custom_properties_read(repo: str) -> str:
    """Read the custom properties an organisation has set on a repository.

    These are labels an organisation puts on its repositories — tier, team, compliance.
    """
    found = github().get(f"repos/{repo}/properties/values")

    return ok(
        [
            {"name": each.get("property_name"), "value": each.get("value")}
            for each in (found if isinstance(found, list) else [])
        ]
    )


@mcp.tool()
def custom_properties_write(repo: str, name: str, value: str) -> str:
    """Set one custom property on a repository.

    The property has to already exist on the organisation; this sets its value for one
    repository.
    """
    github().patch(
        f"repos/{repo}/properties/values",
        {"properties": [{"property_name": name, "value": value}]},
    )

    return ok({"repo": repo, "set": name, "to": value})


# ══ PROJECTS ══


@mcp.tool()
def projects_list(owner: str, limit: int = 20) -> str:
    """List the project boards an organisation or a person has.

    owner is the organisation or the account name. These are GitHub Projects, the boards
    issues get tracked on.
    """
    try:
        found = github().get(f"orgs/{owner}/projectsV2", {"per_page": counted(limit)})
    except Exception:
        found = github().get(f"users/{owner}/projectsV2", {"per_page": counted(limit)})

    rows = found if isinstance(found, list) else found.get("items", [])

    return ok(
        [
            {"number": each.get("number"), "title": each.get("title"),
             "state": each.get("state") or ("closed" if each.get("closed") else "open"),
             "url": each.get("url")}
            for each in rows
        ]
    )


@mcp.tool()
def projects_get(owner: str, number: int) -> str:
    """Read one project board, with what it is for.

    number is the board's, which projects_list gives back.
    """
    try:
        found = github().get(f"orgs/{owner}/projectsV2/{number}")
    except Exception:
        found = github().get(f"users/{owner}/projectsV2/{number}")

    return ok(
        {
            "number": found.get("number"),
            "title": found.get("title"),
            "about": some(found.get("short_description"), 300),
            "state": found.get("state"),
            "url": found.get("url"),
        }
    )


@mcp.tool()
def projects_write(owner: str, number: int, repo: str = "", issue: int = 0) -> str:
    """Put an issue onto a project board.

    number is the board's, and repo with issue says which issue goes on it.
    """
    if not repo or not issue:
        raise LookupError("A repository and an issue number are needed.")

    found = github().get(f"repos/{repo}/issues/{issue}")

    github().post(
        f"orgs/{owner}/projectsV2/{number}/items", {"content_id": found.get("node_id")}
    )

    return ok({"board": number, "added": f"{repo}#{issue}"})


# ══ GISTS ══


@mcp.tool()
def list_gists(limit: int = 20) -> str:
    """List the gists this account has, which are its scratch files.

    Use this for "what snippets have I saved".
    """
    return ok([shapes.gist(each) for each in github().get("gists", {"per_page": counted(limit)})])


@mcp.tool()
def get_gist(gist: str) -> str:
    """Read one gist, with what is in each of its files.

    gist is its id, which list_gists gives back.
    """
    found = github().get(f"gists/{gist}")

    return ok(
        {
            **shapes.gist(found),
            "content": {
                name: some(each.get("content"), 1500)
                for name, each in (found.get("files") or {}).items()
            },
        }
    )


@mcp.tool()
def create_gist(filename: str, content: str, description: str = "", public: bool = False) -> str:
    """Save a snippet as a gist.

    public being false, which it is unless said otherwise, keeps it unlisted — a gist made by
    accident should not be one the world can read.
    """
    made = github().post(
        "gists",
        {
            "description": description,
            "public": bool(public),
            "files": {filename: {"content": content}},
        },
    )

    return ok(shapes.gist(made))


@mcp.tool()
def update_gist(gist: str, filename: str = "", content: str = "", description: str = "") -> str:
    """Change a gist: what is in one of its files, or what it says it is for.

    gist is its id. Naming a file that is not there yet adds it.
    """
    wanted = {}

    if description:
        wanted["description"] = description

    if filename:
        wanted["files"] = {filename: {"content": content}}

    if not wanted:
        raise LookupError("Nothing was given to change on that gist.")

    return ok(shapes.gist(github().patch(f"gists/{gist}", wanted)))


# ══ PEOPLE, TEAMS AND SEARCH ══


@mcp.tool()
def get_me() -> str:
    """Read the account this token belongs to.

    Use this for "who am I signed in as on GitHub", or to get the login name the other tools
    want for "me".
    """
    found = github().get("user")

    return ok(
        {
            **shapes.person(found),
            "repos": found.get("public_repos"),
            "company": found.get("company"),
        }
    )


@mcp.tool()
def get_teams(owner: str, limit: int = 30) -> str:
    """List the teams inside an organisation.

    owner is the organisation's name. A team is a group of people access is given to.
    """
    found = github().get(f"orgs/{owner}/teams", {"per_page": counted(limit)})

    return ok([shapes.team(each) for each in found])


@mcp.tool()
def get_team_members(owner: str, team: str, limit: int = 30) -> str:
    """List who is in one team.

    owner is the organisation and team is the team's slug, which get_teams gives back.
    """
    found = github().get(f"orgs/{owner}/teams/{team}/members", {"per_page": counted(limit)})

    return ok([shapes.person(each) for each in found])


@mcp.tool()
def search_users(query: str, limit: int = 20) -> str:
    """Search GitHub's people by name, login or what is in their profile.

    query takes GitHub's modifiers — location:London, followers:>100.
    """
    found = github().get("search/users", {"q": f"{query} type:user", "per_page": counted(limit)})

    return ok([shapes.person(each) for each in found.get("items", [])])


@mcp.tool()
def search_orgs(query: str, limit: int = 20) -> str:
    """Search GitHub's organisations by name or what is in their profile.

    query is what to look for.
    """
    found = github().get("search/users", {"q": f"{query} type:org", "per_page": counted(limit)})

    return ok([shapes.person(each) for each in found.get("items", [])])


@mcp.tool()
def search_code(query: str, limit: int = 20) -> str:
    """Search the contents of code across GitHub.

    query takes GitHub's modifiers — repo:owner/name, language:python, path:src. This looks
    inside files, which search_repositories does not.
    """
    found = github().get("search/code", {"q": query, "per_page": counted(limit)})

    return ok(
        [
            {
                "repo": ((each.get("repository") or {}) or {}).get("full_name"),
                "path": each.get("path"),
                "url": each.get("html_url"),
            }
            for each in found.get("items", [])
        ]
    )


@mcp.tool()
def search_commits(query: str, limit: int = 20) -> str:
    """Search commit messages across GitHub.

    query takes GitHub's modifiers — repo:owner/name, author:someone. Use this for "when was
    that changed", "who wrote the commit about X".
    """
    found = github().get("search/commits", {"q": query, "per_page": counted(limit)})

    return ok(
        [
            {
                **shapes.commit(each),
                "repo": ((each.get("repository") or {}) or {}).get("full_name"),
            }
            for each in found.get("items", [])
        ]
    )


# ══ ISSUES ══


@mcp.tool()
def issue_read(repo: str, number: int, what: str = "issue") -> str:
    """Read one issue whole, or what is under it.

    what is issue for the issue itself, comments for the discussion, or sub_issues for the
    ones broken out of it. list_issues is the one for a list.
    """
    wanted = str(what or "issue").strip().lower()

    if wanted.startswith("comment"):
        found = github().get(f"repos/{repo}/issues/{number}/comments", {"per_page": 50})

        return ok(
            [
                {
                    "by": ((each.get("user") or {}) or {}).get("login"),
                    "at": each.get("created_at"),
                    "said": some(each.get("body"), 600),
                }
                for each in found
            ]
        )

    if wanted.startswith("sub"):
        found = github().get(f"repos/{repo}/issues/{number}/sub_issues", {"per_page": 50})

        return ok([shapes.issue(each) for each in found])

    found = github().get(f"repos/{repo}/issues/{number}")

    return ok({**shapes.issue(found), "body": some(found.get("body"), MOST_BODY)})


@mcp.tool()
def issue_write(repo: str, number: int, title: str = "", body: str = "", state: str = "",
                assignees: str = "", labels: str = "") -> str:
    """Change an issue that already exists: its title, its text, whether it is open, who has it.

    number is the issue's. state is open or closed. assignees and labels are comma separated
    and replace what is there. create_issue is the one for a new issue.
    """
    wanted = {}

    if title:
        wanted["title"] = title

    if body:
        wanted["body"] = body

    if state:
        wanted["state"] = state

    if assignees:
        wanted["assignees"] = split(assignees)

    if labels:
        wanted["labels"] = split(labels)

    if not wanted:
        raise LookupError("Nothing was given to change on that issue.")

    changed = github().patch(f"repos/{repo}/issues/{number}", wanted)

    return ok(shapes.issue(changed))


@mcp.tool()
def add_issue_comment(repo: str, number: int, body: str) -> str:
    """Say something under an issue or a pull request, which are numbered the same way.

    Everybody watching it is told, so it is said once.
    """
    made = github().post(f"repos/{repo}/issues/{number}/comments", {"body": body})

    return ok({"id": made.get("id"), "on": number, "url": made.get("html_url")})


@mcp.tool()
def sub_issue_write(repo: str, number: int, child: int, remove: bool = False) -> str:
    """Break an issue out under another one, or take it back out.

    number is the parent and child is the issue going under it. remove being true undoes it.
    """
    if remove:
        github().sent("DELETE", f"repos/{repo}/issues/{number}/sub_issue",
                      json={"sub_issue_id": int(child)})

        return ok({"parent": number, "removed": child})

    found = github().get(f"repos/{repo}/issues/{child}")

    github().post(f"repos/{repo}/issues/{number}/sub_issues", {"sub_issue_id": found.get("id")})

    return ok({"parent": number, "child": child})


@mcp.tool()
def list_issue_types(owner: str) -> str:
    """List the kinds of issue an organisation has set up — Bug, Feature, Task.

    owner is the organisation's name. Not every organisation uses these; an empty list means
    it does not.
    """
    found = github().get(f"orgs/{owner}/issue-types")

    return ok(
        [
            {"name": each.get("name"), "about": some(each.get("description"), 150)}
            for each in (found if isinstance(found, list) else found.get("issue_types", []))
        ]
    )


@mcp.tool()
def list_issue_fields(owner: str) -> str:
    """List the extra fields an organisation has added to its issues.

    owner is the organisation's name. These are set up per organisation, so most have none.
    """
    found = github().get(f"orgs/{owner}/issue-fields")

    return ok(
        [
            {"name": each.get("name"), "kind": each.get("data_type")}
            for each in (found if isinstance(found, list) else found.get("issue_fields", []))
        ]
    )


@mcp.tool()
def list_label(repo: str, limit: int = 50) -> str:
    """List the labels a repository has.

    repo is owner/name. These are the only words issue_write will take for labels.
    """
    found = github().get(f"repos/{repo}/labels", {"per_page": counted(limit)})

    return ok(
        [
            {"name": each.get("name"), "colour": each.get("color"),
             "about": some(each.get("description"), 150)}
            for each in found
        ]
    )


@mcp.tool()
def get_label(repo: str, name: str) -> str:
    """Read one label: its colour and what it is for.

    name is the label's own name, which list_label gives back.
    """
    found = github().get(f"repos/{repo}/labels/{name}")

    return ok(
        {"name": found.get("name"), "colour": found.get("color"),
         "about": some(found.get("description"), 200)}
    )


@mcp.tool()
def label_write(repo: str, name: str, colour: str = "", description: str = "",
                remove: bool = False) -> str:
    """Make a label, change one, or delete it.

    colour is a hex value without the hash — ff8800. remove being true deletes it, which
    takes it off every issue wearing it.
    """
    if remove:
        github().sent("DELETE", f"repos/{repo}/labels/{name}")

        return ok({"deleted": name})

    wanted = {"name": name}

    if colour:
        wanted["color"] = colour.lstrip("#")

    if description:
        wanted["description"] = description

    try:
        github().get(f"repos/{repo}/labels/{name}")
        made = github().patch(f"repos/{repo}/labels/{name}", wanted)
    except Exception:
        made = github().post(f"repos/{repo}/labels", wanted)

    return ok({"name": made.get("name"), "colour": made.get("color")})


# ══ PULL REQUESTS ══


@mcp.tool()
def pull_request_read(repo: str, number: int, what: str = "pull") -> str:
    """Read one pull request, or what is under it.

    what is pull for the request itself, files for what it changes, reviews for what people
    said about it, comments for the line by line ones, or status for whether the checks passed.
    """
    wanted = str(what or "pull").strip().lower()

    if wanted.startswith("file"):
        found = github().get(f"repos/{repo}/pulls/{number}/files", {"per_page": 50})

        return ok(
            [
                {"path": each.get("filename"), "how": each.get("status"),
                 "added": each.get("additions"), "removed": each.get("deletions")}
                for each in found
            ]
        )

    if wanted.startswith("review"):
        found = github().get(f"repos/{repo}/pulls/{number}/reviews", {"per_page": 50})

        return ok(
            [
                {"by": ((each.get("user") or {}) or {}).get("login"), "said": each.get("state"),
                 "at": each.get("submitted_at"), "body": some(each.get("body"), 400)}
                for each in found
            ]
        )

    if wanted.startswith("comment"):
        found = github().get(f"repos/{repo}/pulls/{number}/comments", {"per_page": 50})

        return ok(
            [
                {"by": ((each.get("user") or {}) or {}).get("login"), "path": each.get("path"),
                 "line": each.get("line"), "said": some(each.get("body"), 400),
                 "id": each.get("id")}
                for each in found
            ]
        )

    found = github().get(f"repos/{repo}/pulls/{number}")

    if wanted.startswith("status"):
        checks = github().get(f"repos/{repo}/commits/{(found.get('head') or {}).get('sha')}/status")

        return ok(
            {
                "number": number,
                "state": checks.get("state"),
                "checks": [
                    {"name": each.get("context"), "how": each.get("state")}
                    for each in checks.get("statuses", [])
                ],
            }
        )

    return ok(
        {
            **shapes.pull(found),
            "body": some(found.get("body"), MOST_BODY),
            "mergeable": found.get("mergeable"),
            "added": found.get("additions"),
            "removed": found.get("deletions"),
            "files": found.get("changed_files"),
        }
    )


@mcp.tool()
def create_pull_request(repo: str, title: str, head: str, base: str = "", body: str = "",
                        draft: bool = False) -> str:
    """Open a pull request from one branch into another.

    head is the branch with the work on it and base is where it is going, or the default
    branch when left out. draft opens it as one not ready for review.
    """
    where = base or github().get(f"repos/{repo}").get("default_branch")
    made = github().post(
        f"repos/{repo}/pulls",
        {"title": title, "head": head, "base": where, "body": body, "draft": bool(draft)},
    )

    return ok(shapes.pull(made))


@mcp.tool()
def update_pull_request(repo: str, number: int, title: str = "", body: str = "",
                        state: str = "", base: str = "") -> str:
    """Change a pull request: its title, its text, what it is going into, or close it.

    state is open or closed. merge_pull_request is the one for merging it.
    """
    wanted = {}

    for name, value in (("title", title), ("body", body), ("state", state), ("base", base)):
        if value:
            wanted[name] = value

    if not wanted:
        raise LookupError("Nothing was given to change on that pull request.")

    return ok(shapes.pull(github().patch(f"repos/{repo}/pulls/{number}", wanted)))


@mcp.tool()
def merge_pull_request(repo: str, number: int, how: str = "merge", title: str = "") -> str:
    """Merge a pull request into its base branch.

    how is merge, squash or rebase. This is not undone from here, so it is only called when
    somebody has said to merge that number.
    """
    wanted = {"merge_method": str(how or "merge").strip().lower()}

    if title:
        wanted["commit_title"] = title

    made = github().sent("PUT", f"repos/{repo}/pulls/{number}/merge", json=wanted)

    return ok({"merged": made.get("merged"), "sha": (made.get("sha") or "")[:10]})


@mcp.tool()
def update_pull_request_branch(repo: str, number: int) -> str:
    """Bring a pull request's branch up to date with what it is merging into.

    This is the "update branch" button: it merges the base back into the head so the request
    is no longer behind.
    """
    made = github().sent("PUT", f"repos/{repo}/pulls/{number}/update-branch", json={})

    return ok({"updated": number, "said": some(made.get("message"), 200)})


@mcp.tool()
def pull_request_review_write(repo: str, number: int, event: str, body: str = "") -> str:
    """Review a pull request: approve it, ask for changes, or just comment.

    event is APPROVE, REQUEST_CHANGES or COMMENT. A review is posted as whoever the token
    belongs to and everybody watching is told.
    """
    made = github().post(
        f"repos/{repo}/pulls/{number}/reviews",
        {"event": str(event or "COMMENT").strip().upper(), "body": body},
    )

    return ok({"review": made.get("id"), "said": made.get("state")})


@mcp.tool()
def add_comment_to_pending_review(repo: str, number: int, path: str, line: int,
                                  body: str) -> str:
    """Leave a comment on one line of a pull request's diff.

    path is the file and line is the line number in the new version. This posts on its own
    rather than waiting for a review to be submitted around it.
    """
    found = github().get(f"repos/{repo}/pulls/{number}")
    made = github().post(
        f"repos/{repo}/pulls/{number}/comments",
        {
            "body": body,
            "commit_id": ((found.get("head") or {}) or {}).get("sha"),
            "path": path,
            "line": int(line),
            "side": "RIGHT",
        },
    )

    return ok({"comment": made.get("id"), "path": path, "line": line})


@mcp.tool()
def add_reply_to_pull_request_comment(repo: str, number: int, comment: int, body: str) -> str:
    """Reply to a line comment somebody left on a pull request.

    comment is the id pull_request_read with what=comments gives back.
    """
    made = github().post(
        f"repos/{repo}/pulls/{number}/comments/{comment}/replies", {"body": body}
    )

    return ok({"reply": made.get("id"), "to": comment})


@mcp.tool()
def request_copilot_review(repo: str, number: int) -> str:
    """Ask GitHub Copilot to review a pull request.

    This adds Copilot as a reviewer the same way a person would be added. What it says comes
    back through pull_request_read with what=reviews, once it has looked.
    """
    github().post(
        f"repos/{repo}/pulls/{number}/requested_reviewers", {"reviewers": ["copilot-pull-request-reviewer[bot]"]}
    )

    return ok({"asked": number, "of": "copilot"})


@mcp.tool()
def search_pull_requests(query: str, limit: int = 20) -> str:
    """Search pull requests across GitHub with its own query language.

    query takes GitHub's modifiers — repo:owner/name, author:someone, is:open, review:required.
    """
    found = github().get(
        "search/issues",
        {"q": f"{query} type:pr", "per_page": counted(limit)},
    )

    return ok([shapes.pull(each) for each in found.get("items", [])])


# ══ REPOSITORIES ══


@mcp.tool()
def create_repository(name: str, description: str = "", private: bool = True) -> str:
    """Make a new repository under whoever the token belongs to.

    private is true unless said otherwise, because a repository made by accident should not
    be one the world can read. It is made empty, with no README and no first commit.
    """
    made = github().post(
        "user/repos", {"name": name, "description": description, "private": bool(private)}
    )

    return ok(shapes.repository(made))


@mcp.tool()
def delete_repository(repo: str) -> str:
    """Delete a repository for good.

    repo is owner/name. GitHub does not undo this and neither does anything here, so it is
    only ever called when somebody has said the full name of the repository out loud.
    """
    github().sent("DELETE", f"repos/{repo}")

    return ok({"deleted": repo})


@mcp.tool()
def fork_repository(repo: str, organization: str = "") -> str:
    """Make a copy of somebody else's repository under your own account.

    repo is owner/name. organization puts the fork there instead of on the account itself.
    """
    wanted = {"organization": organization} if organization else {}
    made = github().post(f"repos/{repo}/forks", wanted)

    return ok(shapes.repository(made))


@mcp.tool()
def star_repository(repo: str) -> str:
    """Star a repository, which is how GitHub bookmarks one.

    repo is owner/name.
    """
    github().sent("PUT", f"user/starred/{repo}")

    return ok({"starred": repo})


@mcp.tool()
def unstar_repository(repo: str) -> str:
    """Take a star back off a repository.

    repo is owner/name.
    """
    github().sent("DELETE", f"user/starred/{repo}")

    return ok({"unstarred": repo})


@mcp.tool()
def list_starred_repositories(limit: int = 30) -> str:
    """List the repositories this account has starred.

    Use this for "what have I bookmarked", or as a way in when a repository has been
    referred to but not named.
    """
    found = github().get("user/starred", {"per_page": counted(limit)})

    return ok([shapes.repository(each) for each in found])


@mcp.tool()
def list_repository_collaborators(repo: str, limit: int = 30) -> str:
    """List who can push to a repository.

    repo is owner/name. This is who has been given access, not everybody who has ever
    contributed to it.
    """
    found = github().get(f"repos/{repo}/collaborators", {"per_page": counted(limit)})

    return ok([shapes.person(each) for each in found])


# ══ FILES AND BRANCHES ══


@mcp.tool()
def create_or_update_file(repo: str, path: str, content: str, message: str,
                          branch: str = "") -> str:
    """Write a file into a repository, making it or replacing what is there.

    path is where it goes, message is the commit message, and branch is which branch — left
    out it is the default one. Replacing a file needs no extra step: the current version is
    looked up and written over.
    """
    import base64 as encoding

    wanted = {
        "message": message,
        "content": encoding.b64encode(content.encode("utf-8")).decode("ascii"),
    }

    if branch:
        wanted["branch"] = branch

    # GITHUB REFUSES A WRITE OVER A FILE THAT EXISTS UNLESS IT IS TOLD WHICH VERSION IS
    # BEING REPLACED, WHICH IS WHAT MAKES TWO PEOPLE WRITING AT ONCE FAIL RATHER THAN LOSE ONE.
    try:
        held = github().get(f"repos/{repo}/contents/{path}", {"ref": branch} if branch else None)

        if isinstance(held, dict) and held.get("sha"):
            wanted["sha"] = held["sha"]
    except Exception:
        pass

    made = github().sent("PUT", f"repos/{repo}/contents/{path}", json=wanted)

    return ok(
        {
            "path": path,
            "commit": ((made.get("commit") or {}) or {}).get("sha", "")[:10],
            "url": ((made.get("content") or {}) or {}).get("html_url"),
        }
    )


@mcp.tool()
def delete_file(repo: str, path: str, message: str, branch: str = "") -> str:
    """Take a file out of a repository.

    path is which file and message is the commit message. branch is which branch, or the
    default one when left out.
    """
    held = github().get(f"repos/{repo}/contents/{path}", {"ref": branch} if branch else None)
    wanted = {"message": message, "sha": held.get("sha")}

    if branch:
        wanted["branch"] = branch

    made = github().sent("DELETE", f"repos/{repo}/contents/{path}", json=wanted)

    return ok({"deleted": path, "commit": ((made.get("commit") or {}) or {}).get("sha", "")[:10]})


@mcp.tool()
def push_files(repo: str, branch: str, message: str, files: str) -> str:
    """Write several files in one commit, rather than one commit each.

    files is one per line, written as path=content with the content on that same line. For
    anything with newlines in it, create_or_update_file one at a time is the one.
    """
    written = []

    for line in str(files or "").split("\n"):
        path, _, content = line.partition("=")

        if path.strip():
            create_or_update_file(repo, path.strip(), content, message, branch)
            written.append(path.strip())

    return ok({"written": written, "branch": branch})


@mcp.tool()
def create_branch(repo: str, branch: str, from_branch: str = "") -> str:
    """Make a new branch off another one.

    from_branch is where it starts, or the repository's default branch when left out.
    """
    where = from_branch or github().get(f"repos/{repo}").get("default_branch")
    found = github().get(f"repos/{repo}/git/ref/heads/{where}")

    github().post(
        f"repos/{repo}/git/refs",
        {"ref": f"refs/heads/{branch}", "sha": ((found.get("object") or {}) or {}).get("sha")},
    )

    return ok({"branch": branch, "from": where})


@mcp.tool()
def list_branches(repo: str, limit: int = 30) -> str:
    """List a repository's branches.

    repo is owner/name. Use this before create_branch or create_pull_request when the name
    of a branch is not certain.
    """
    found = github().get(f"repos/{repo}/branches", {"per_page": counted(limit)})

    return ok(
        [
            {
                "name": each.get("name"),
                "sha": ((each.get("commit") or {}) or {}).get("sha", "")[:10],
                "protected": each.get("protected"),
            }
            for each in found
        ]
    )


@mcp.tool()
def list_tags(repo: str, limit: int = 30) -> str:
    """List a repository's tags, which are usually its versions.

    repo is owner/name. list_releases is the one for what was written up about each version.
    """
    found = github().get(f"repos/{repo}/tags", {"per_page": counted(limit)})

    return ok(
        [
            {"name": each.get("name"), "sha": ((each.get("commit") or {}) or {}).get("sha", "")[:10]}
            for each in found
        ]
    )


@mcp.tool()
def get_tag(repo: str, tag: str) -> str:
    """Read one tag: what it points at and who made it.

    repo is owner/name and tag is its name, like v1.2.0.
    """
    found = github().get(f"repos/{repo}/git/ref/tags/{tag}")
    at = (found.get("object") or {}) or {}

    return ok({"tag": tag, "kind": at.get("type"), "sha": (at.get("sha") or "")[:10]})


@mcp.tool()
def get_repository_tree(repo: str, branch: str = "", deep: bool = False) -> str:
    """List the files in a repository, as paths rather than contents.

    branch is which branch, or the default when left out. deep walks into every folder;
    without it only the top level comes back. Use this to find what to read before
    read_file.
    """
    where = branch or github().get(f"repos/{repo}").get("default_branch")
    wanted = {"recursive": "1"} if deep else None
    found = github().get(f"repos/{repo}/git/trees/{where}", wanted)

    return ok(
        {
            "branch": where,
            "cut": found.get("truncated"),
            "files": [
                {"path": each.get("path"), "kind": each.get("type"), "size": each.get("size")}
                for each in (found.get("tree") or [])
            ][:200],
        }
    )


@mcp.tool()
def get_commit(repo: str, sha: str) -> str:
    """Read one commit: what it said, who made it, and which files it touched.

    sha is the commit's hash, which list_commits gives back shortened and which works either
    way.
    """
    found = github().get(f"repos/{repo}/commits/{sha}")
    stats = found.get("stats") or {}

    return ok(
        {
            **shapes.commit(found),
            "added": stats.get("additions"),
            "removed": stats.get("deletions"),
            "files": [
                {"path": each.get("filename"), "how": each.get("status")}
                for each in (found.get("files") or [])
            ][:50],
        }
    )


# ══ RELEASES ══


@mcp.tool()
def list_releases(repo: str, limit: int = 20) -> str:
    """List a repository's releases, newest first.

    repo is owner/name. Use this for "what versions are there", "when did 2.0 come out".
    """
    found = github().get(f"repos/{repo}/releases", {"per_page": counted(limit)})

    return ok([shapes.release(each) for each in found])


@mcp.tool()
def get_latest_release(repo: str) -> str:
    """Read the most recent release of a repository, with its notes.

    repo is owner/name. This is the fastest answer to "what is the current version".
    """
    return ok(shapes.release(github().get(f"repos/{repo}/releases/latest")))


@mcp.tool()
def get_release_by_tag(repo: str, tag: str) -> str:
    """Read one release by the tag it went out under.

    tag is like v1.2.0. list_releases and list_tags both give the names back.
    """
    return ok(shapes.release(github().get(f"repos/{repo}/releases/tags/{tag}")))


# ══ ACTIONS ══


@mcp.tool()
def actions_list(repo: str, what: str = "runs", limit: int = 20) -> str:
    """List what GitHub Actions has been doing on a repository.

    what is runs for the workflow runs, or workflows for the workflows themselves. Use this
    for "did the build pass", "what is running".
    """
    if str(what).strip().lower().startswith("workflow"):
        found = github().get(f"repos/{repo}/actions/workflows", {"per_page": counted(limit)})

        return ok(
            [
                {"id": each.get("id"), "name": each.get("name"), "state": each.get("state"),
                 "file": each.get("path")}
                for each in found.get("workflows", [])
            ]
        )

    found = github().get(f"repos/{repo}/actions/runs", {"per_page": counted(limit)})

    return ok([shapes.run(each) for each in found.get("workflow_runs", [])])


@mcp.tool()
def actions_get(repo: str, run: str) -> str:
    """Read one workflow run, with the jobs inside it and how each one went.

    run is the run's id, which actions_list gives back. get_job_logs is the one for what a
    failing job actually printed.
    """
    found = github().get(f"repos/{repo}/actions/runs/{run}")
    jobs = github().get(f"repos/{repo}/actions/runs/{run}/jobs", {"per_page": 50})

    return ok({**shapes.run(found), "jobs": [shapes.job(each) for each in jobs.get("jobs", [])]})


@mcp.tool()
def actions_run_trigger(repo: str, workflow: str, branch: str = "") -> str:
    """Start a workflow off by hand rather than waiting for a push.

    workflow is its file name like ci.yml, or its id. branch is which branch to run it on,
    or the default one. The workflow has to allow being started this way.
    """
    where = branch or github().get(f"repos/{repo}").get("default_branch")

    github().post(f"repos/{repo}/actions/workflows/{workflow}/dispatches", {"ref": where})

    return ok({"started": workflow, "branch": where})


@mcp.tool()
def get_job_logs(repo: str, job: str) -> str:
    """Read what one job in a workflow run printed, which is where a failure says why.

    job is the job's id, which actions_get gives back. Only the tail comes back, because a
    log is long and the reason a build failed is at the end of it.
    """
    answer = github().sent("GET", f"repos/{repo}/actions/jobs/{job}/logs", raw=True)

    return ok({"job": job, "tail": some(answer[-MOST_BODY:], MOST_BODY)})


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


def split(said):
    """A COMMA SEPARATED LIST AS THE LIST GITHUB WANTS."""
    return [each.strip() for each in str(said or "").split(",") if each.strip()]


def counted(limit):
    return max(1, min(int(limit), 50))


def decoded(content):
    return base64.b64decode(content).decode("utf-8", "replace")


if __name__ == "__main__":
    mcp.run()
