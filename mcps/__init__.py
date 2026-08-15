"""SERVICES HAPPY CAN REACH THAT ARE NOT THIS COMPUTER."""

import time

from langchain_core.tools import tool
from mcp.types import Tool

from mcps import binding, bridging, loop, pool, registry, store
from mcps.bridging import whenever
from mcps.joining import connect, disconnect, paste, stir

TOOLS = []

NOTHING = "Nothing is connected."

# NOBODY IS WAITING ON A NAME FOR LONGER THAN THIS, HOWEVER MANY SERVICES ARE ASKED.
PATIENCE = 4

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
    """EVERY TOOL FROM EVERY CONNECTED SERVICE, READY FOR THE GRAPH."""
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
    """WHAT THE TOOLS ON THIS MACHINE ARE CALLED, SO NOTHING REMOTE SHADOWS ONE."""
    import hands

    return {each.name for module in hands.MODULES for each in getattr(module, "TOOLS", [])}


def mention():
    """THE LINE THE SYSTEM PROMPT GAINS, AND ONLY WHILE SOMETHING IS CONNECTED."""
    return MENTION if any(row["tools"] for row in store.every()) else ""


def signed_in():
    """WHAT EVERY CONNECTED SERVICE CALLS THE PERSON WHOSE ACCOUNT IT IS.

    EACH SERVER ANSWERS FOR ITSELF, BECAUSE EACH ONE ALREADY HOLDS ITS OWN SIGN IN AND
    KNOWS WHERE THE NAME SITS IN WHAT IT GETS BACK. THEY ARE ASKED TOGETHER AND WAITED ON
    ONCE: A SERVICE HAVING A BAD DAY COSTS THE OTHERS NOTHING."""
    asking = [row for row in pool.live() if binding.OURS[0] in named(row)]

    if not asking:
        return []

    ends = time.monotonic() + PATIENCE
    sent = [(row, loop.submit(answering(row))) for row in asking]

    return [(said, registry.label(row["name"])) for row, said in gathered(sent, ends) if said]


def named(row):
    return {each.get("name") for each in row["tools"] or []}


async def answering(row):
    return spoken(await pool.session(row).call(binding.OURS[0], {}))


def spoken(result):
    """THE NAME OUT OF ONE ANSWER. A SERVER THAT WOULD NOT SAY IS A SERVER THAT SAID NOTHING."""
    if result.isError:
        return ""

    said = [each.text for each in result.content if getattr(each, "type", None) == "text"]

    return " ".join(said).strip()


def gathered(sent, ends):
    """WHAT CAME BACK BEFORE THE ONE BUDGET RAN OUT, AND NOTHING FROM WHAT DID NOT."""
    found = []

    for row, each in sent:
        try:
            found.append((row, each.result(timeout=max(0.0, ends - time.monotonic()))))
        except Exception:
            # DROPPED AND PUT DOWN: A CALL NOBODY IS WAITING FOR ANY MORE MUST NOT BE LEFT
            # TURNING ON THE ONE LOOP EVERY OTHER CONNECTION SHARES.
            each.cancel()
            found.append((row, ""))

    return found


@tool
def connections() -> str:
    """Say which outside services are connected right now, such as Notion or Google.

    Use this when you are asked what you can reach, or when a service someone
    named does not seem to be there. It says nothing about this computer.
    """
    on = [registry.label(row["name"]) for row in store.every() if row["tools"]]

    return ", ".join(on) if on else NOTHING


def drawn(behind=()):
    """THE WHOLE CONNECTIONS PANEL, FOR SOMETHING THAT HAS TO DRAW IT."""
    from mcps import panel

    return panel.rows(behind)


def start():
    """START WHAT IS CONNECTED, IN THE BACKGROUND."""
    pool.warm()
    bridging.start()


def stop():
    """PUT DOWN EVERY PROCESS HAPPY STARTED."""
    bridging.stop()
    pool.shut()
