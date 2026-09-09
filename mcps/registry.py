"""THE SERVICES HAPPY SHIPS, AND WHAT EACH ONE COSTS TO CONNECT."""

from pathlib import Path

from mcps import permission

OURS = Path(__file__).resolve().parents[1]

# HOW A SERVICE IS SIGNED INTO.
NONE = "none"
TOKEN = "token"  # ONE TOKEN MADE ON THEIR SITE.
OAUTH = "oauth"  # A BROWSER AND A CONSENT SCREEN, WITH A CLIENT OF YOUR OWN.

# READ OFF THE DOOR ITSELF SO THE TWO CAN NEVER DRIFT APART.
SENDS_BACK = f"Register {permission.expected()} as the redirect."

# EVERYONE BRINGS THEIR OWN CLIENT: GOOGLE CAPS AN UNVERIFIED APP AT A HUNDRED
# USERS FOR THE LIFE OF THE PROJECT.
GOOGLE = (
    "Make a Google Cloud project, switch on the Gmail, Calendar and Drive APIs, and add a "
    "Web application OAuth client. Publish it — left in testing, Google forgets the sign in "
    "every week. " + SENDS_BACK
)

KNOWN = [
    {
        "name": "google",
        "label": "Google",
        "folder": "google",
        "kind": OAUTH,
        # WHERE SOMEBODY GOES TO MAKE WHAT THIS SERVICE WANTS OF THEM.
        "where": "https://console.cloud.google.com/apis/credentials",
        "also": ["gmail", "mail", "email", "calendar", "googlecalendar", "drive", "googledrive"],
        # ONE SIGN IN FOR MAIL, CALENDAR AND DRIVE: THEY ARE ONE ACCOUNT SAYING YES ONCE.
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "scopes": [
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/drive",
        ],
        "hint": "Mail, calendar and drive, all on the one sign in. " + GOOGLE,
    },
    {
        "name": "whatsapp",
        "label": "WhatsApp",
        "folder": "whatsapp",
        "kind": NONE,
        "also": ["wa", "whatsappweb"],
        # THE SERVER OFFERS EVERY TOOL WHETHER OR NOT THE QR WAS SCANNED, SO THE
        # PANEL NEEDS TELLING THAT STARTED AND LINKED ARE NOT THE SAME THING.
        "scan": True,
        # NO care ON PURPOSE: AN UNOFFICIAL CLIENT IS A CONDITION OF THIS
        # CONNECTION, NOT A FAULT, AND AMBER IS FOR A FAULT.
        "hint": "Reads your chats and can send, asking first every time. Connect it and scan "
        "the QR that appears here; Happy runs the bridge behind it and stops it again on the "
        "way out, so there is nothing to start yourself. It links to your account the way "
        "WhatsApp Web does, which their terms do not allow, and sending from an unofficial "
        "client is what gets numbers banned.",
    },
    {
        "name": "weather",
        "label": "Weather",
        "folder": "weather",
        # NOTHING TO SIGN INTO.
        "kind": NONE,
        "also": ["forecast", "openmeteo"],
        "hint": "Forecasts from Open-Meteo, which wants no account and no key. Connect it and "
        "it works. Ask about anywhere by name; nothing here knows where you are.",
    },
    {
        "name": "instagram",
        "label": "Instagram",
        "folder": "instagram",
        "kind": TOKEN,
        "where": "https://developers.facebook.com/apps",
        "also": ["ig", "insta"],
        "hint": "Needs an Instagram access token from a Meta app of your own, at "
        "developers.facebook.com. Instagram only ever hands over the account's own posts and "
        "the comments under them, so this reads those and can reply to one, asking first.",
    },
    {
        "name": "notion",
        "label": "Notion",
        "folder": "notion",
        "kind": TOKEN,
        "where": "https://notion.so/my-integrations",
        "hint": "Needs an internal integration token from notion.so/my-integrations. Notion "
        "shows an integration nothing at all until you share a page with it, so share the "
        "top of your workspace with it once it exists.",
    },
    {
        "name": "github",
        "label": "GitHub",
        "folder": "github",
        "kind": TOKEN,
        "where": "https://github.com/settings/tokens",
        "also": ["gh"],
        "hint": "Needs a personal access token from github.com/settings/tokens. A fine "
        "grained one only reaches the repositories you tick.",
    },
    {
        "name": "linear",
        "label": "Linear",
        "folder": "linear",
        "kind": TOKEN,
        "where": "https://linear.app/settings/api",
        "also": ["issues", "linearapp", "tickets"],
        "hint": "Issues, projects and cycles, read and moved along. Make a personal API key in "
        "Linear's own settings and paste it; it is one key and it needs nothing else.",
    },
    {
        "name": "jira",
        "label": "Jira",
        "folder": "jira",
        "kind": TOKEN,
        "where": "https://id.atlassian.com/manage-profile/security/api-tokens",
        "also": ["atlassian", "backlog", "sprint"],
        # THE ONE SERVICE THAT NEEDS MORE THAN A TOKEN: ITS API IS AT A DIFFERENT ADDRESS
        # FOR EVERY COMPANY, AND THE TOKEN IS ONLY HALF OF WHAT SIGNS THE CALL.
        "wants": [
            ("site", "Site", "The one ending atlassian.net, without the https:// in front."),
            ("email", "Email", "The account the token was made on."),
            ("token", "API token", "Kept in Happy's database, on this machine."),
        ],
        "hint": "Issues, projects and boards. Make an API token at id.atlassian.com, then paste "
        "your site, the email you made it on, and the token itself.",
    },
    {
        "name": "slack",
        "label": "Slack",
        "folder": "slack",
        "kind": TOKEN,
        "where": "https://api.slack.com/apps",
        "hint": "Needs a user token, the one starting xoxp, from a Slack app of your own. "
        "Somebody who runs the workspace may have to approve the app first.",
    },
]

BY_NAME = {each["name"]: each for each in KNOWN}


def known():
    return list(KNOWN)


def names():
    return [each["name"] for each in KNOWN]


def one(name):
    return BY_NAME.get(name)


def matched(said):
    """THE SERVICE SOMEBODY MEANT, OUT OF WHATEVER THEY HAPPENED TO CALL IT."""
    wanted = plain(said)

    if not wanted:
        return None

    for known in KNOWN:
        if wanted in {known["name"], plain(known["label"]), *known.get("also", ())}:
            return known

    # A SERVICE IS RARELY NAMED ON ITS OWN: "MY GMAIL ACCOUNT" IS STILL GOOGLE. ONLY
    # THE LONGER NAMES ARE LOOKED FOR INSIDE A SENTENCE, BECAUSE "ig" IS IN "configure".
    for known in KNOWN:
        if any(each in wanted for each in inside(known)):
            return known

    return None


def inside(known):
    """THE NAMES FOR THIS SERVICE LONG ENOUGH TO BE SAFE TO FIND INSIDE ANOTHER WORD."""
    return {known["name"]} | {each for each in known.get("also", ()) if len(each) > 3}


def plain(said):
    """A NAME WITH THE SPACES, CAPITALS AND PUNCTUATION TAKEN OFF IT."""
    return "".join(each for each in str(said or "").lower() if each.isalnum())


def label(name):
    found = BY_NAME.get(name)

    return found["label"] if found else str(name).replace("_", " ").title()


def server(name):
    """THE PROGRAM TO RUN FOR THIS SERVICE."""
    found = BY_NAME.get(name)

    if found is None:
        return None

    return OURS / "mcps" / "servers" / found["folder"] / "mcp_server.py"


def signs_in(kind):
    """TRUE WHEN CONNECTING MEANS A BROWSER AND SOMEBODY SAYING YES."""
    return kind == OAUTH
