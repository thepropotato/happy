"""EVERY TOOL BECOMES A RECORDING STUB SO A BENCHMARK CANNOT TOUCH THE MACHINE."""

import os
from pathlib import Path

DANGEROUS = {"run_command", "power_control", "move_to_trash", "open_app", "click_on",
             "type_text", "press_keys", "download", "build", "network_control"}


def throwaway(name="bench.db"):
    """POINT THE DATABASE AT A SCRATCH FILE BEFORE ANY HAPPY MODULE IS IMPORTED."""
    where = Path(__file__).resolve().parent / "runs" / name
    where.parent.mkdir(parents=True, exist_ok=True)
    os.environ["HAPPY_DB"] = str(where)
    return where


def stubbed(tool, calls, replies=None):
    """THE SAME SCHEMA AND DOCSTRING, BUT THE BODY ONLY WRITES DOWN THAT IT WAS CALLED."""
    from langchain_core.tools import StructuredTool

    def body(**kwargs):
        calls.append({"name": tool.name, "args": kwargs})
        canned = (replies or {}).get(tool.name)
        return canned if canned is not None else f"[mocked {tool.name}]"

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
