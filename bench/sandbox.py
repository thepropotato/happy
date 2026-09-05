"""EVERY TOOL BECOMES A RECORDING STUB SO A BENCHMARK CANNOT TOUCH THE MACHINE."""

import os
from pathlib import Path

DANGEROUS = {"run_command", "power_control", "move_to_trash", "open_app", "click_on",
             "type_text", "press_keys", "download", "build", "network_control"}

ADDRESSED = {"open_url", "read_page", "download"}


def throwaway(name="bench.db"):
    """POINT THE DATABASE AT A SCRATCH FILE BEFORE ANY HAPPY MODULE IS IMPORTED."""
    where = Path(__file__).resolve().parent / "runs" / name
    where.parent.mkdir(parents=True, exist_ok=True)
    os.environ["HAPPY_DB"] = str(where)
    return where


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

        host = handed.urlparse(handed.full(said)).netloc.removeprefix("www.").lower()
        offered = " ".join(each["result"] for each in (replies or {}).get("search_web") or [])

        return host not in offered.lower()

    def body(**kwargs):
        calls.append({"name": tool.name, "args": kwargs})

        # THE ONE GUARD THE REAL TOOLS HAVE THAT THE MODEL MUST STILL MEET HERE: AN ADDRESS IT
        # WROTE ITSELF IS REFUSED, AND IT IS TOLD TO USE THE NUMBER, THE SAME AS IN REAL LIFE.
        if tool.name in ADDRESSED and forged(kwargs.get("url")):
            return reasons.no(handed.REFUSED.format(said=kwargs.get("url")))

        canned = (replies or {}).get(tool.name)

        if canned is None:
            return f"[mocked {tool.name}]"

        if isinstance(canned, str):
            return canned

        given = canned.pop(0) if len(canned) > 1 else canned[0]

        return reasons.no(given["result"]) if given.get("failed") else given["result"]

    return StructuredTool(
        name=tool.name,
        description=tool.description,
        args_schema=tool.args_schema,
        func=body,
    )


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
