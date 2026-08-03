"""SERVICES HAPPY CAN REACH THAT ARE NOT THIS COMPUTER.

EVERYTHING ELSE UNDER hands/ IS PYTHON SITTING BESIDE THE MODEL. THESE ARE NOT:
THEY ARE MCP SERVERS TALKED TO OVER A PIPE, WHICH IS WHY THIS FOLDER IS NAMED
FOR WHAT THEY LITERALLY ARE RATHER THAN FOR A PART OF A PERSON.

HAPPY SHIPS EVERY ONE OF THEM. THEY LIVE IN mcps/servers/, THEY ARE LISTED IN
mcps/registry.py, AND EACH ONE READS ITS OWN CREDENTIALS OUT OF data/happy.db.
NOTHING CAN BE ADDED FROM THE PANEL, SO THERE IS NO SUCH THING HERE AS A SERVER
NOBODY VETTED WITH THE MODEL'S HANDS ON IT.

NOTHING IS CONNECTED UNTIL SOMEBODY CONNECTS IT, SO A PERSON WHO NEVER OPENS THE
PANEL HAS EXACTLY THE TOOLS THIS COMPUTER ALWAYS HAD.
"""

from langchain_core.tools import tool
from mcp.types import Tool

from mcps import binding, pool, registry, store, whatsapp
from mcps.joining import connect, disconnect, paste, stir
from mcps.whatsapp import whenever

TOOLS = []

NOTHING = "Nothing is connected."

# THIS USED TO END "THEY ARE SLOWER THAN THE ONES ON THIS MACHINE, SO WHEN EITHER
# WOULD DO, USE THE LOCAL ONE", WHICH WAS TRUE OF SOMEBODY ELSE'S MCP ENDPOINT
# BEHIND AN OAUTH ROUND TRIP AND IS NOT TRUE OF THESE. WHAT IT ACTUALLY BOUGHT
# WAS A MODEL THAT OPENED MAIL, SCREENSHOTTED IT AND READ THE PIXELS FOR A MINUTE
# AND A HALF RATHER THAN CALLING google_search_emails, AND THEN ANSWERED OUT OF
# WHATEVER THE OCR HAPPENED TO CATCH.
MENTION = (
    "Some of your tools reach a service this person has connected rather than this "
    "computer. They are named after the service they belong to, like "
    "google_search_emails or notion_search.\n\n"
    "When something lives inside one of those services, ask the service. Mail, "
    "calendar entries, files, chats, pages and issues are all answered by the tool "
    "that owns them, in one call, exactly. Do not open the app for it, do not look "
    "at the screen for it, and do not read it out of a browser: that is slower, it "
    "is guesswork, and it is wrong as often as it is right. Use the screen only for "
    "what no connected service can answer."
)


def offering():
    """EVERY TOOL FROM EVERY CONNECTED SERVICE, READY FOR THE GRAPH.

    BUILT OUT OF WHAT EACH SERVER SAID LAST TIME, NOT OUT OF ASKING IT NOW. THIS
    RUNS WHILE HAPPY IS STARTING AND MUST NEVER WAIT ON A PROCESS COMING UP.
    """
    found = []
    taken = local_names()

    for row in store.every():
        if not row["tools"]:
            continue

        built = binding.bind(
            registry.label(row["name"]),
            pool.session(row),
            remembered(row["tools"]),
            taken=taken,
        )

        taken.update(each.name for each in built)
        found.extend(built)

    return found + [connections] if found else found


def remembered(kept):
    """THE STORED TOOL LISTS BACK AS TOOLS. ONE THAT NO LONGER PARSES IS DROPPED."""
    found = []

    for each in kept:
        try:
            found.append(Tool(**each))
        except Exception:
            continue

    return found


def local_names():
    """WHAT THE TOOLS ON THIS MACHINE ARE CALLED, SO NOTHING REMOTE SHADOWS ONE.

    READ STRAIGHT OFF THE OTHER MODULES RATHER THAN THROUGH hands.tools(), WHICH
    WOULD COME BACK ROUND TO THIS FUNCTION AND NEVER STOP.
    """
    import hands

    return {each.name for module in hands.MODULES for each in getattr(module, "TOOLS", [])}


def mention():
    """THE LINE THE SYSTEM PROMPT GAINS, AND ONLY WHILE SOMETHING IS CONNECTED."""
    return MENTION if any(row["tools"] for row in store.every()) else ""


@tool
def connections() -> str:
    """Say which outside services are connected right now, such as Notion or Google.

    Use this when you are asked what you can reach, or when a service someone
    named does not seem to be there. It says nothing about this computer.
    """
    on = [registry.label(row["name"]) for row in store.every() if row["tools"]]

    return ", ".join(on) if on else NOTHING


def drawn(behind=()):
    """THE WHOLE CONNECTIONS PANEL, FOR SOMETHING THAT HAS TO DRAW IT.

    behind IS THE PANEL'S OWN HANDFUL OF SETTINGS. THEY COME BACK FOLDED AWAY AT
    THE BOTTOM RATHER THAN AT THE TOP, BECAUSE NOBODY OPENS THIS PANEL TO MOVE A
    TIMEOUT AND TWO SLIDERS IN FRONT OF THE SERVICES READ AS THE POINT OF IT.
    """
    from mcps import panel

    return panel.rows(behind)


def start():
    """START WHAT IS CONNECTED, IN THE BACKGROUND. SAFE TO CALL WHEN NOTHING IS.

    THE WHATSAPP BRIDGE COMES UP HERE TOO. IT IS NOT AN MCP SERVER AND HAPPY DOES
    NOT SPEAK TO IT DIRECTLY, BUT IT IS THE PROCESS EVERY WHATSAPP TOOL ACTUALLY
    ANSWERS OUT OF, AND LEAVING IT FOR A PERSON TO REMEMBER MEANT A CONNECTION
    THAT LOOKED FINE AND WAS HOURS STALE.
    """
    pool.warm()
    whatsapp.start()


def stop():
    """PUT DOWN EVERY PROCESS HAPPY STARTED.

    CALLED BY HAND RATHER THAN LEFT TO atexit, BECAUSE QUITTING FROM THE WINDOW
    GOES THROUGH os._exit AND atexit NEVER RUNS — WHICH USED TO LEAVE A SERVER
    PER CONNECTED SERVICE BEHIND, EVERY TIME.
    """
    whatsapp.stop()
    pool.shut()
