"""WHAT EACH CONNECTED SERVICE CALLS THE PERSON WHOSE ACCOUNT IT IS.

EVERY ONE OF THESE IS AN ACCOUNT THIS PERSON SIGNED INTO THEMSELVES, SO THE NAME ON IT IS A
NAME THEY CHOSE. NONE OF THEM IS ASKED UNLESS IT IS CONNECTED, AND NONE OF THEM IS WAITED ON
FOR LONG: A NAME THAT ARRIVES AFTER THE ANSWER DOES IS NO USE TO ANYBODY."""

import concurrent.futures as futures
import time

import httpx

from mcps import store
from mcps.servers.shared import credentials

PATIENCE = 4

# WHO IS ASKED FIRST WHERE SEVERAL ANSWER. MAIL AND WORK CHAT CARRY A REAL NAME BECAUSE
# STRANGERS READ THEM; A HANDLE ON A PHOTO SITE IS THE LAST THING ANYONE MEANT.
ORDER = ("google", "slack", "github", "whatsapp", "notion", "instagram")

RENEWAL = "https://oauth2.googleapis.com/token"

SENDING_AS = "https://gmail.googleapis.com/gmail/v1/users/me/settings/sendAs"

SLACK = "https://slack.com/api"

GITHUB = "https://api.github.com/user"

NOTION = "https://api.notion.com/v1/users/me"

NOTION_VERSION = "2022-06-28"

INSTAGRAM = "https://graph.instagram.com/v21.0/me"


def named():
    """EVERY CONNECTED SERVICE'S NAME FOR THEM, ASKED ALL AT ONCE, BEST SOURCE FIRST."""
    doing = [name for name in ORDER if name in connected()]

    if not doing:
        return []

    pool = futures.ThreadPoolExecutor(max_workers=len(doing))
    ends = time.monotonic() + PATIENCE

    try:
        sent = [(name, pool.submit(guarded, name)) for name in doing]
        found = [(name, waited(each, ends)) for name, each in sent]
    finally:
        # NEVER WAITED ON: ONE SERVICE HAVING A BAD DAY MUST NOT HOLD UP THE ANSWER, AND
        # CLOSING THIS POOL THE USUAL WAY WOULD SIT THERE UNTIL THE SLOWEST OF THEM SPOKE.
        pool.shutdown(wait=False)

    return [(said, name) for name, said in found if said]


def connected():
    """WHAT IS SIGNED IN AND ANSWERING, WHICH IS NOT THE SAME AS WHAT HAPPY SHIPS."""
    try:
        return {row["name"] for row in store.every() if row["tools"]}
    except Exception:
        return set()


def guarded(name):
    """ONE SERVICE ASKED. A SERVICE THAT WILL NOT SAY IS A SERVICE THAT SAID NOTHING."""
    try:
        return EACH[name]()
    except Exception:
        return ""


def waited(each, ends):
    """ONE SHARE OF THE ONE BUDGET, SO SIX SERVICES COST WHAT ONE OF THEM DOES."""
    try:
        return each.result(timeout=max(0.0, ends - time.monotonic()))
    except Exception:
        return ""


def google():
    """THE NAME THEIR OWN MAIL GOES OUT UNDER, WHICH STRANGERS READ AND SO IS THEIR REAL ONE."""
    held = credentials.kept("google")
    tokens, client = held["tokens"], held["client"]

    answer = fetched(
        "POST",
        RENEWAL,
        data={
            "client_id": client.get("client_id"),
            "client_secret": client.get("client_secret"),
            "refresh_token": tokens.get("refresh_token"),
            "grant_type": "refresh_token",
        },
    )

    reaching = answer.get("access_token") or tokens.get("access_token")

    if not reaching:
        return ""

    found = fetched("GET", SENDING_AS, headers={"Authorization": f"Bearer {reaching}"})

    for entry in found.get("sendAs") or []:
        if entry.get("isPrimary") and entry.get("displayName"):
            return str(entry["displayName"]).strip()

    return ""


def slack():
    """auth.test NAMES THE ACCOUNT, AND THE PROFILE BEHIND IT HOLDS THE NAME THEY TYPED."""
    signing = {"Authorization": f"Bearer {credentials.token('slack')}"}

    who = fetched("GET", f"{SLACK}/auth.test", headers=signing)

    if not who.get("ok"):
        return ""

    found = fetched(
        "GET", f"{SLACK}/users.info", headers=signing, params={"user": who.get("user_id")}
    )

    profile = ((found.get("user") or {}).get("profile")) or {}

    return str(profile.get("real_name") or who.get("user") or "").strip()


def github():
    found = fetched(
        "GET", GITHUB, headers={"Authorization": f"Bearer {credentials.token('github')}"}
    )

    return str(found.get("name") or found.get("login") or "").strip()


def notion():
    found = fetched(
        "GET",
        NOTION,
        headers={
            "Authorization": f"Bearer {credentials.token('notion')}",
            "Notion-Version": NOTION_VERSION,
        },
    )

    # THE TOKEN IS THE INTEGRATION'S, SO THE PERSON IS THE ONE IT WAS MADE BY.
    owner = (((found.get("bot") or {}).get("owner")) or {}).get("user") or {}

    return str(owner.get("name") or "").strip()


def instagram():
    found = fetched(
        "GET",
        INSTAGRAM,
        params={"fields": "username", "access_token": credentials.token("instagram")},
    )

    return str(found.get("username") or "").strip()


def fetched(way, where, **asked):
    answer = httpx.request(way, where, timeout=PATIENCE, **asked)

    return answer.json() if answer.status_code < 400 and answer.text else {}


EACH = {
    "google": google,
    "slack": slack,
    "github": github,
    "notion": notion,
    "instagram": instagram,
    "whatsapp": lambda: linked(),
}


def linked():
    """WHAT THEY CALL THEMSELVES ON THE WHATSAPP ACCOUNT THIS IS SIGNED IN AS."""
    from mcps.servers.whatsapp import talking

    found = talking.asked(talking.client().get_status()) or {}

    if not (found.get("connected") or found.get("authenticated")):
        return ""

    return str(found.get("name") or "").strip()
