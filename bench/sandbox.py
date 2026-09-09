"""EVERY TOOL BECOMES A RECORDING STUB SO A BENCHMARK CANNOT TOUCH THE MACHINE."""

import os
import re
from pathlib import Path

DANGEROUS = {"run_command", "system_control", "move_to_trash", "open_app",
             "control_app", "download", "build"}

ADDRESSED = {"open_url", "read_page", "download"}


def throwaway(name="bench.db"):
    """POINT THE DATABASE AT A SCRATCH FILE BEFORE ANY HAPPY MODULE IS IMPORTED."""
    where = Path(__file__).resolve().parent / "runs" / name
    where.parent.mkdir(parents=True, exist_ok=True)
    os.environ["HAPPY_DB"] = str(where)
    return where


def connected(where):
    """THE CONNECTOR ROWS COPIED OFF THE REAL DATABASE, SCHEMAS ONLY, NO SECRETS.

    A SERVICE'S TOOLS ONLY EXIST ONCE IT IS CONNECTED, AND A THROWAWAY DATABASE IS
    CONNECTED TO NOTHING — SO WITHOUT THIS EVERY MCP TOOL IS SIMPLY ABSENT AND A SUITE
    ABOUT WHATSAPP OR GMAIL SCORES A MODEL FOR NOT CALLING A TOOL IT WAS NEVER GIVEN.
    THE BODIES ARE STUBBED LIKE EVERY OTHER TOOL, SO ONLY THE SHAPE CROSSES OVER."""
    import sqlite3

    real = Path(__file__).resolve().parent.parent / "data" / "happy.db"

    if not real.exists():
        return []

    try:
        source = sqlite3.connect(f"file:{real}?mode=ro", uri=True)
        rows = source.execute("SELECT name, tools, state, at FROM connections").fetchall()
        source.close()
    except sqlite3.Error:
        return []

    scratch = sqlite3.connect(where)
    scratch.execute(
        "CREATE TABLE IF NOT EXISTS connections ("
        "name TEXT PRIMARY KEY, tools TEXT, state TEXT, at TEXT NOT NULL)"
    )
    scratch.executemany("INSERT OR REPLACE INTO connections VALUES (?, ?, ?, ?)", rows)
    scratch.commit()
    scratch.close()

    return [row[0] for row in rows]


def stubbed(tool, calls, replies=None):
    """THE SAME SCHEMA AND DOCSTRING, BUT THE BODY ONLY WRITES DOWN THAT IT WAS CALLED.

    A CANNED REPLY IS A STRING, OR A LIST OF {"result", "failed"} HANDED OUT IN ORDER WITH
    THE LAST ONE REPEATING, SO A TURN THAT SEARCHED TWICE GETS BOTH ANSWERS."""
    from langchain_core.tools import StructuredTool

    from hands import reasons
    from hands.web import handed

    def forged(said):
        """AN ADDRESS THE MODEL WROTE, UNLESS ITS SITE IS ONE THE CANNED RESULTS NAME, WHICH
        THE REAL RESOLVER WOULD HAVE TAKEN AS THAT RESULT."""
        said = str(said or "").strip()

        if not said or said.isdigit() or handed.shallow(handed.full(said)):
            return False

        # AN ADDRESS A TOOL ALREADY HANDED OVER IS NOT ONE THE MODEL WROTE. THE REAL RESOLVER
        # LETS THESE THROUGH ON THE SAME SET, AND THIS COPY DID NOT LOOK AT IT AT ALL.
        if handed.full(said) in handed.given:
            return False

        host = handed.urlparse(handed.full(said)).netloc.removeprefix("www.").lower()
        offered = " ".join(each["result"] for each in (replies or {}).get("search_web") or [])

        # THE REAL GUARD ALSO REFUSES AN ADDRESS THAT IS NOT A PLAIN SITE ROOT, WHATEVER THE
        # HOST — A CHANNEL PATH LIKE "/@Someone" IS NOT SOMETHING A SEARCH HANDED OVER. TAKING
        # THE HOST ALONE AS PERMISSION MADE THIS BENCH KINDER THAN THE MACHINE.
        return host not in offered.lower() or not handed.shallow(handed.full(said))

    def body(**kwargs):
        # THE OUTCOME GOES IN TOO, NOT JUST THE NAME. A CALL A GUARD TURNED BACK IS NOT A CALL
        # THE MODEL GOT TO MAKE, AND SCORING IT AS ONE MARKS THE GUARD WORKING AS A FAULT.
        made = {"name": tool.name, "args": kwargs, "refused": False}
        calls.append(made)

        def turned(said):
            made["refused"] = True

            return said

        # THE GUARDS THE REAL TOOLS HAVE THAT THE MODEL MUST STILL MEET HERE. WITHOUT THESE
        # THE BENCH SCORES A TURN AS LOST THAT REAL LIFE WOULD HAVE PUT RIGHT: THE TOOL SAYS
        # NO, NAMES THE TOOL THAT WOULD WORK, AND THE MODEL GOES AND USES IT. A BENCH THAT
        # SKIPS THE REFUSAL IS MEASURING A HAPPY NOBODY RUNS.
        if tool.name in ADDRESSED and forged(kwargs.get("url")):
            return turned(reasons.no(handed.REFUSED.format(said=kwargs.get("url"))))

        blocked = writing(tool.name, kwargs)

        if blocked:
            return turned(blocked)

        # NOT COPIED, CALLED: THE SAME FUNCTION THE REAL LOOP ASKS, SO A PATH THE MODEL
        # INVENTED IS REFUSED HERE EXACTLY WHEN THE MACHINE WOULD REFUSE IT.
        from brain import sourcing

        made_up = sourcing.checked(tool.name, kwargs)

        if made_up:
            return turned(reasons.no(made_up))

        canned = (replies or {}).get(tool.name)

        if canned is None:
            return f"[mocked {tool.name}]"

        if isinstance(canned, str):
            record(tool.name, canned)
            return canned

        given = canned.pop(0) if len(canned) > 1 else canned[0]

        if given.get("failed"):
            return turned(reasons.no(given["result"]))

        record(tool.name, given["result"])

        return given["result"]

    return StructuredTool(
        name=tool.name,
        description=tool.description,
        args_schema=tool.args_schema,
        func=body,
    )


ADDRESS = re.compile(r"https?://[^\s\"'<>)]+")

# A PATH IN A CANNED LISTING, WHICH IS WRITTEN "/somewhere/a file.pdf (88 KB, 23 Jun)" OR
# "/somewhere/a folder/ (a folder holding 3 things)". THE NAME MAY HOLD SPACES AND EVEN
# BRACKETS — "image (2).png" IS A REAL DOWNLOAD — SO IT RUNS UP TO THE SIZE OR THE FOLDER
# NOTE THAT CLOSES THE LINE, AND ONLY THOSE.
PATHS = re.compile(
    r"(/(?:[^\s/(][^/(\n]*?/)*[^/\n]*?)\s*(?:\((?:\d[\d.]*\s*(?:KB|MB|GB|B)\b|a folder)|$)",
    re.M,
)


def record(name, result):
    """AN ADDRESS OR A PATH A MOCK JUST NAMED BACK IS ONE A TOOL GAVE, SO THE NEXT CALL MAY
    USE IT.

    THE REAL open_url REGISTERS WHAT IT OPENED AND THE REAL describe() REGISTERS EVERY PATH
    IT LISTS; THE STUB NEVER RUNS EITHER BODY, SO THE SAME THING IS DONE HERE FROM THE CANNED
    RESULT, OR THE BENCH REFUSES A LINE IT HANDED OVER."""
    from hands.files import held
    from hands.web import handed

    for found in PATHS.findall(str(result or "")):
        held.offer(found.rstrip(".,"))

    if name not in ("open_url", "current_activity", "already_open", "download_images"):
        return

    for found in ADDRESS.findall(str(result or "")):
        handed.offer(found.rstrip(".,"))


def writing(name, kwargs):
    """WHAT A REAL WRITING TOOL WOULD SAY NO TO, WITHOUT WRITING ANYTHING.

    THE CHECKS ARE NOT COPIED HERE, THEY ARE CALLED: A SECOND COPY OF A GUARD IS A GUARD THAT
    GOES STALE, AND THIS ONE DID — IT KEPT REFUSING ON ONE STRAY FACT AFTER THE REAL TOOL HAD
    LEARNED TO DROP THE LINE AND CARRY ON. WHAT THE BENCH ENFORCES IS NOW WHATEVER
    hands.files.making ENFORCES, WHICH IS THE ONLY WAY THE TWO STAY THE SAME."""
    from pathlib import Path as Where

    from hands import reasons
    from hands.files import making

    if name in ("write_file", "edit_file"):
        where = Where(str(kwargs.get("path") or "")).expanduser()
        sort = making.SEALED.get(where.suffix.lower())

        if not sort:
            return None

        return reasons.no(making.NOT_TEXT.format(
            name=where.name, kind=where.suffix.lstrip("."),
            doing="write" if name == "write_file" else "change", sort=sort))

    if name != "write_document":
        return None

    from brain import wrapping
    from memory import conversation

    said = conversation.asking() or ""

    pointing = any(each in said.lower() for each in making.POINTED)

    if pointing and not wrapping.already(*making.LOOKERS):
        return reasons.no(making.UNLOOKED.format(said=said))

    # THE HALF THIS COPY HAD LOST. THE REAL TOOL TURNS BACK A DECK ABOUT A SUBJECT THAT WAS
    # ONLY POINTED AT WHEN NOTHING HAS GONE AND READ ABOUT IT, AND WITHOUT IT THE BENCH
    # SCORED A HOUSE OF THE DRAGON DECK WRITTEN STRAIGHT OFF THE WEIGHTS AS A TURN THE
    # MACHINE WOULD HAVE ALLOWED, WHICH IT WOULD NOT.
    if pointing and not wrapping.already(*making.READERS):
        return reasons.no(making.UNREAD.format(said=said))

    made_up = making.unsourced(str(kwargs.get("text") or ""), str(kwargs.get("title") or ""))

    # THE SAME LINE THE REAL TOOL DRAWS: BUILT OUT OF NOTHING IS TURNED BACK, WRONG IN A
    # DETAIL IS WRITTEN WITHOUT IT. THE STUB WRITES NOTHING EITHER WAY, SO ONLY THE REFUSAL
    # HALF CAN BE ACTED ON HERE.
    if len(made_up) >= making.MOSTLY_INVENTED:
        return reasons.no(making.UNSOURCED.format(
            much="much of what you were about to put",
            made_up="\n".join(f"- {each}" for each in made_up)))

    return None


def harness(replies=None):
    """EVERY REAL TOOL, SCHEMA INTACT, BODY REPLACED. RETURNS THE TOOLS AND THE CALL LOG."""
    import hands

    calls = []
    tools = [stubbed(each, calls, replies) for each in hands.tools()]
    return tools, calls


def assert_no_real_tools(tools):
    """A STUB THAT IS NOT A STUB IS A BUG WE REFUSE TO RUN WITH."""
    from langchain_core.tools import StructuredTool

    for each in tools:
        if not isinstance(each, StructuredTool) or each.func.__module__ != __name__:
            raise SystemExit(f"REFUSING TO RUN: {each.name} is not mocked")

    return True
