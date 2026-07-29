"""THE SERVICES HAPPY KNOWS HOW TO REACH, AND WHAT EACH ONE COSTS TO SIGN INTO.

THE kind IS THE WHOLE STORY OF HOW HARD CONNECTING IS. SOME SERVICES REGISTER
HAPPY AS A CLIENT ON THE SPOT AND ARE ONE BUTTON. THE REST WANT SOMETHING PASTED
IN, AND THE PANEL HAS TO SAY SO PLAINLY RATHER THAN OFFER A BUTTON THAT FAILS.

THE TOOL LISTS ARE HAND WRITTEN BECAUSE A CAP ON ITS OWN PICKS AT RANDOM. THEY
ARE A PREFERENCE AND NOT A DEMAND: A NAME THAT NO LONGER EXISTS COSTS NOTHING,
AND A LIST THAT MATCHES NOTHING AT ALL FALLS BACK TO THE CAP.
"""

# HOW A SERVICE IS SIGNED INTO.
OPEN = "oauth"  # IT REGISTERS US ITSELF. ONE BUTTON, NOTHING TO PASTE.
TOKEN = "token"  # PASTE A TOKEN YOU MADE ON THEIR SITE.
CLIENT = "client"  # MAKE AN OAUTH CLIENT OF YOUR OWN FIRST, THEN SIGN IN.
LOCAL = "local"  # A PROGRAM ON THIS MACHINE, TALKED TO OVER ITS PIPES.

EASY = "One button. Nothing to paste."

# EVERYBODY BRINGS THEIR OWN OAUTH CLIENT FOR THESE, AND HAPPY SHIPS NONE.
#
# A SHARED ONE WOULD BE EASIER FOR THE FIRST HUNDRED PEOPLE AND IMPOSSIBLE AFTER
# THEM: GOOGLE CAPS AN UNVERIFIED APP AT A HUNDRED FOR THE LIFE OF THE PROJECT,
# AND LIFTING THAT FOR GMAIL OR DRIVE MEANS A CASA SECURITY ASSESSMENT EVERY YEAR
# FOR AS LONG AS IT RUNS. A CLIENT PER PERSON HAS NO CEILING AND COSTS NOBODY
# ANYTHING, SO THE SETUP IS THE PRICE AND THE PANEL SAYS SO PLAINLY.
#
# THE ONE THING PEOPLE GET WRONG IS LEAVING THE PROJECT IN TESTING, WHERE GOOGLE
# THROWS THE REFRESH TOKEN AWAY AFTER SEVEN DAYS AND THEY SIGN IN AGAIN WEEKLY.
YOUR_OWN = (
    "Make a Google Cloud project, switch the API on, and add a Desktop app OAuth "
    "client. Publish it — left in testing, Google forgets the sign in every week."
)

# THE ONE THING EVERY BRING YOUR OWN CLIENT SETUP GETS WRONG. IT IS WRITTEN OUT
# IN FULL BECAUSE IT HAS TO BE COPIED EXACTLY INTO SOMEBODY ELSE'S CONSOLE.
SENDS_BACK = "Register http://127.0.0.1:8765/callback as the redirect."

# ONE GOOGLE CLOUD PROJECT COVERS ALL THREE, SO THE CLIENT IS ASKED FOR ONCE AND
# THE OTHER TWO FIND IT. DOING THE SAME FIFTEEN MINUTE ERRAND THREE TIMES WOULD BE
# THE THING THAT MADE SOMEBODY GIVE UP HALFWAY.
GOOGLE_ONE = "google"

GOOGLE = "Google will not register Happy, so this needs a client of your own. " + YOUR_OWN

KNOWN = [
    {
        "name": "notion",
        "label": "Notion",
        "kind": OPEN,
        "address": "https://mcp.notion.com/mcp",
        "allowed": ["search", "fetch", "create-pages", "update-page", "get-comments"],
        "hint": EASY,
    },
    {
        "name": "linear",
        "label": "Linear",
        "kind": OPEN,
        "address": "https://mcp.linear.app/mcp",
        "allowed": [
            "list_issues",
            "get_issue",
            "create_issue",
            "update_issue",
            "list_projects",
        ],
        "hint": EASY,
    },
    {
        "name": "github",
        "label": "GitHub",
        "kind": TOKEN,
        "address": "https://api.githubcopilot.com/mcp/",
        "allowed": [
            "search_repositories",
            "get_file_contents",
            "list_issues",
            "create_issue",
            "list_pull_requests",
        ],
        "hint": "Needs a personal access token from github.com/settings/tokens.",
    },
    {
        "name": "slack",
        "label": "Slack",
        "kind": CLIENT,
        "address": "https://mcp.slack.com/mcp",
        "allowed": [
            "conversations_history",
            "conversations_search_messages",
            "channels_list",
            "chat_post_message",
        ],
        "hint": "Needs a Slack app of your own, and an admin to approve it. " + SENDS_BACK,
    },
    {
        "name": "gmail",
        "label": "Gmail",
        "short": "Gmail",
        "kind": CLIENT,
        "address": "https://gmailmcp.googleapis.com/mcp/v1",
        "allowed": [],
        "family": GOOGLE_ONE,
        "scopes": [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.compose",
        ],
        "hint": GOOGLE,
    },
    {
        "name": "calendar",
        "label": "Google Calendar",
        "short": "Calendar",
        "kind": CLIENT,
        "address": "https://calendarmcp.googleapis.com/mcp/v1",
        "allowed": [],
        "family": GOOGLE_ONE,
        "scopes": ["https://www.googleapis.com/auth/calendar"],
        "hint": GOOGLE,
    },
    {
        "name": "drive",
        "label": "Google Drive",
        "short": "Drive",
        "kind": CLIENT,
        "address": "https://drivemcp.googleapis.com/mcp/v1",
        "allowed": [],
        "family": GOOGLE_ONE,
        "scopes": ["https://www.googleapis.com/auth/drive.readonly"],
        "hint": GOOGLE,
    },
    {
        "name": "whatsapp",
        "label": "WhatsApp",
        "kind": LOCAL,
        "address": "uv run --directory ~/whatsapp-mcp/whatsapp-mcp-server main.py",
        "allowed": [
            "search_contacts",
            "list_chats",
            "list_messages",
            "send_message",
            "send_file",
        ],
        # NOT MADE BY WHATSAPP, AND SIGNING IN WITH IT CAN GET THE NUMBER BANNED.
        # HAPPY ALREADY SENDS WHATSAPP MESSAGES BY DRIVING THE APP ON THE SCREEN,
        # WHICH IS SLOWER AND COSTS NOBODY THEIR ACCOUNT.
        "hint": "Unofficial, and needs its bridge running. Your account may be banned.",
        "care": "Unofficial · your account may be banned",
    },
]

# A SIGN IN THAT COVERS SEVERAL SERVICES, LISTED AS THE ONE THING IT IS. THE
# ERRAND BEHIND GOOGLE IS FIFTEEN MINUTES AND WAS PRINTED THREE TIMES, WHICH READ
# AS THREE ERRANDS AND WAS WHERE PEOPLE PUT THE PANEL DOWN.
FAMILIES = {
    GOOGLE_ONE: {
        "name": GOOGLE_ONE,
        "label": "Google",
        "kind": CLIENT,
        "hint": GOOGLE + " " + SENDS_BACK,
    }
}

BY_NAME = {each["name"]: each for each in KNOWN}


def known():
    return list(KNOWN)


def household(family):
    """EVERY SERVICE COVERED BY ONE SIGN IN, IN THE ORDER THEY ARE LISTED."""
    return [each for each in KNOWN if each.get("family") == family]


def find(name):
    return BY_NAME.get(name)


def label(name):
    """WHAT TO CALL A SERVICE IN FRONT OF A PERSON, KNOWN OR NOT."""
    found = BY_NAME.get(name)

    return found["label"] if found else str(name).replace("_", " ").title()


def relatives(name):
    """THE OTHER SERVICES THAT SHARE THIS ONE'S SIGN IN, IF IT SHARES WITH ANY."""
    family = (BY_NAME.get(name) or {}).get("family")

    if not family:
        return []

    return [each["name"] for each in KNOWN if each.get("family") == family and each["name"] != name]


def signs_in(kind):
    """TRUE WHEN CONNECTING MEANS A BROWSER AND A ROUND TRIP, NOT JUST A SWITCH."""
    return kind in (OPEN, CLIENT)
