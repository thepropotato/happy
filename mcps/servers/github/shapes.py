"""WHAT GITHUB HANDS BACK, CUT DOWN TO WHAT IS WORTH SAYING.

EVERY GITHUB OBJECT ARRIVES WITH FIFTY FIELDS AND FORTY OF THEM ARE URLS TO OTHER ENDPOINTS.
ONE SHAPE PER KIND, WRITTEN ONCE, SO EVERY TOOL THAT HANDS ONE BACK SAYS IT THE SAME WAY."""

from servers.shared.answering import some


def repository(each):
    return {
        "repo": each.get("full_name"),
        "about": some(each.get("description"), 200),
        "language": each.get("language"),
        "stars": each.get("stargazers_count"),
        "private": each.get("private"),
        "branch": each.get("default_branch"),
        "url": each.get("html_url"),
    }


def issue(each):
    return {
        "number": each.get("number"),
        "title": some(each.get("title"), 200),
        "state": each.get("state"),
        "by": ((each.get("user") or {}) or {}).get("login"),
        "assignees": [one.get("login") for one in (each.get("assignees") or [])],
        "labels": [labelled(one) for one in (each.get("labels") or [])],
        "comments": each.get("comments"),
        "at": each.get("updated_at"),
        "url": each.get("html_url"),
    }


def pull(each):
    return {
        "number": each.get("number"),
        "title": some(each.get("title"), 200),
        "state": "merged" if each.get("merged_at") else each.get("state"),
        "by": ((each.get("user") or {}) or {}).get("login"),
        "from": ((each.get("head") or {}) or {}).get("ref"),
        "into": ((each.get("base") or {}) or {}).get("ref"),
        "draft": each.get("draft"),
        "at": each.get("updated_at"),
        "url": each.get("html_url"),
    }


def commit(each):
    written = each.get("commit") or {}

    return {
        "sha": (each.get("sha") or "")[:10],
        "said": some((written.get("message") or "").split("\n")[0], 200),
        "by": ((written.get("author") or {}) or {}).get("name"),
        "at": ((written.get("author") or {}) or {}).get("date"),
        "url": each.get("html_url"),
    }


def labelled(each):
    """A LABEL IS A STRING WHEN IT WAS SET AND AN OBJECT WHEN IT WAS READ."""
    return each.get("name") if isinstance(each, dict) else each


def run(each):
    return {
        "id": each.get("id"),
        "name": each.get("name") or each.get("display_title"),
        "state": each.get("status"),
        "how": each.get("conclusion"),
        "branch": each.get("head_branch"),
        "number": each.get("run_number"),
        "at": each.get("created_at"),
        "url": each.get("html_url"),
    }


def job(each):
    return {
        "id": each.get("id"),
        "name": each.get("name"),
        "state": each.get("status"),
        "how": each.get("conclusion"),
        "began": each.get("started_at"),
        "ended": each.get("completed_at"),
    }


def release(each):
    return {
        "tag": each.get("tag_name"),
        "name": each.get("name"),
        "draft": each.get("draft"),
        "early": each.get("prerelease"),
        "at": each.get("published_at"),
        "notes": some(each.get("body"), 600),
        "url": each.get("html_url"),
    }


def discussion(each):
    return {
        "number": each.get("number"),
        "title": some(each.get("title"), 200),
        "category": ((each.get("category") or {}) or {}).get("name"),
        "by": ((each.get("user") or {}) or {}).get("login"),
        "answered": bool(each.get("answer_chosen_at")),
        "comments": each.get("comments"),
        "at": each.get("updated_at"),
        "url": each.get("html_url"),
    }


def notification(each):
    subject = each.get("subject") or {}

    return {
        "id": each.get("id"),
        "title": some(subject.get("title"), 200),
        "kind": subject.get("type"),
        "repo": ((each.get("repository") or {}) or {}).get("full_name"),
        "why": each.get("reason"),
        "unread": each.get("unread"),
        "at": each.get("updated_at"),
    }


def alert(each):
    """CODE SCANNING, DEPENDABOT AND SECRET SCANNING ALL WEAR SLIGHTLY DIFFERENT CLOTHES."""
    rule = each.get("rule") or {}
    advisory = (each.get("security_advisory") or {}) or {}
    package = ((each.get("dependency") or {}) or {}).get("package") or {}

    return {
        "number": each.get("number"),
        "state": each.get("state"),
        "severity": (
            rule.get("security_severity_level")
            or rule.get("severity")
            or advisory.get("severity")
            or each.get("secret_type_display_name")
        ),
        "what": some(
            rule.get("description") or advisory.get("summary") or each.get("secret_type"), 200
        ),
        "where": ((each.get("most_recent_instance") or {}).get("location") or {}).get("path")
        or package.get("name")
        or each.get("locations_url"),
        "at": each.get("created_at"),
        "url": each.get("html_url"),
    }


def advisory(each):
    return {
        "id": each.get("ghsa_id"),
        "cve": each.get("cve_id"),
        "summary": some(each.get("summary"), 200),
        "severity": each.get("severity"),
        "at": each.get("published_at"),
        "url": each.get("html_url"),
    }


def gist(each):
    return {
        "id": each.get("id"),
        "about": some(each.get("description"), 200),
        "public": each.get("public"),
        "files": list((each.get("files") or {})),
        "at": each.get("updated_at"),
        "url": each.get("html_url"),
    }


def person(each):
    return {
        "login": each.get("login"),
        "name": each.get("name"),
        "kind": each.get("type"),
        "url": each.get("html_url"),
    }


def team(each):
    return {
        "slug": each.get("slug"),
        "name": each.get("name"),
        "about": some(each.get("description"), 200),
        "privacy": each.get("privacy"),
    }
