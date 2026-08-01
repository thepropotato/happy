"""THE SERVICES HAPPY KNOWS HOW TO REACH, AND WHAT EACH ONE COSTS TO SIGN INTO.

THE kind IS THE WHOLE STORY OF HOW HARD CONNECTING IS. SOME SERVICES REGISTER
HAPPY AS A CLIENT ON THE SPOT AND ARE ONE BUTTON. THE REST WANT SOMETHING PASTED
IN, AND THE PANEL HAS TO SAY SO PLAINLY RATHER THAN OFFER A BUTTON THAT FAILS.

THE TOOL LISTS ARE HAND WRITTEN BECAUSE A CAP ON ITS OWN PICKS AT RANDOM. THEY
ARE A PREFERENCE AND NOT A DEMAND: A NAME THAT NO LONGER EXISTS COSTS NOTHING,
AND A LIST THAT MATCHES NOTHING AT ALL FALLS BACK TO THE CAP.
"""

import sys
from pathlib import Path

from mcps import permission

# THE ONE SERVER HAPPY SHIPS ITSELF. THE PATH IS WORKED OUT RATHER THAN WRITTEN
# DOWN, BECAUSE A CHECKOUT CAN SIT ANYWHERE, AND IT IS RUN BY THE SAME PYTHON
# HAPPY IS RUNNING ON SO IT INHERITS THE VIRTUALENV WITHOUT BEING TOLD.
OURS = Path(__file__).resolve().parents[1]

WHATSAPP = f'"{sys.executable}" "{OURS / "mcps" / "servers" / "whatsapp" / "server.py"}"'

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
# A WEB APPLICATION CLIENT AND NOT A DESKTOP ONE. THE DESKTOP KIND HAS NO
# REDIRECT FIELD AT ALL, WHICH MAKES THE NEXT SENTENCE IMPOSSIBLE TO FOLLOW, AND
# GOOGLE ALLOWS PLAIN http FOR A LOOPBACK ADDRESS ON A WEB CLIENT.
YOUR_OWN = (
    "Make a Google Cloud project, switch the API on, and add a Web application "
    "OAuth client. Publish it — left in testing, Google forgets the sign in every week."
)

# THE ONE THING EVERY BRING YOUR OWN CLIENT SETUP GETS WRONG. IT IS WRITTEN OUT
# IN FULL BECAUSE IT HAS TO BE COPIED EXACTLY INTO SOMEBODY ELSE'S CONSOLE, AND
# IT IS READ OFF THE DOOR ITSELF SO THE TWO CAN NEVER DRIFT APART.
SENDS_BACK = f"Register {permission.expected()} as the redirect."

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
        "address": WHATSAPP,
        # get_status EARNS ITS PLACE AMONG THE READS. THE BRIDGE GOING QUIET
        # LOOKS EXACTLY LIKE A QUIET AFTERNOON, AND A MODEL THAT CAN ASK WHETHER
        # WHATSAPP IS EVEN CONNECTED WILL SAY SO INSTEAD OF ANSWERING FROM
        # WHATEVER IT LAST SAW.
        #
        # THE THREE SENDS ARE HERE ON PURPOSE AND ARE SAFE FOR ONE REASON ONLY:
        # NONE OF THEM STARTS WITH A READING WORD, SO mcps/writing.py STOPS EVERY
        # ONE AND ASKS. WHAT IS ALSO GONE FROM THE SERVER IS THE AUTO REPLY —
        # SENDING NOBODY WAS ASKED ABOUT, ARRIVING WHILE NOBODY IS WATCHING, IS A
        # DIFFERENT THING FROM SENDING SOMEBODY JUST SAID YES TO.
        "allowed": [
            "search_contacts",
            "get_chats",
            "get_messages",
            "query_messages",
            "get_unread_messages",
            "get_status",
            "get_qr_code",
            "send_message",
            "send_group_message",
            "send_media_message",
        ],
        "hint": "Reads your chats and can send, asking first every time. Run "
                "mcps/servers/whatsapp/bridge.py and scan the QR; it has to stay running or "
                "the messages quietly go stale. It links to your account the way WhatsApp Web "
                "does, which their terms do not allow, and sending from an unofficial client "
                "is what gets numbers banned.",
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


def wants(name):
    """EVERY SCOPE THIS SIGN IN HAS TO ASK FOR, IN THE ORDER THEY ARE LISTED.

    ONE CONSENT COVERS A WHOLE FAMILY, SO IT ASKS FOR WHAT ALL OF THEM NEED AT
    ONCE. ASKING FOR MAIL NOW AND CALENDAR LATER IS TWO TRIPS THROUGH THE SAME
    GOOGLE SCREEN FOR THE SAME ACCOUNT, WHICH IS THE THING NOBODY FINISHES.
    """
    found = BY_NAME.get(name)

    if found is None:
        kin = household(name) if name in FAMILIES else []
    else:
        kin = household(found["family"]) if found.get("family") else [found]

    asked = []

    for each in kin:
        for scope in each.get("scopes") or []:
            if scope not in asked:
                asked.append(scope)

    return asked


def relatives(name):
    """THE OTHER SERVICES THAT SHARE THIS ONE'S SIGN IN, IF IT SHARES WITH ANY."""
    family = (BY_NAME.get(name) or {}).get("family")

    if not family:
        return []

    return [each["name"] for each in KNOWN if each.get("family") == family and each["name"] != name]


def signs_in(kind):
    """TRUE WHEN CONNECTING MEANS A BROWSER AND A ROUND TRIP, NOT JUST A SWITCH."""
    return kind in (OPEN, CLIENT)
