"""WHAT WRAPS EVERY CALL: WHAT GOES IN, WHAT IS KEPT, AND HOW LONG IT TOOK.

THE GRAPH NEXT DOOR IS ABOUT ANSWERING. THIS IS ABOUT EVERYTHING THAT HAPPENS
AROUND ONE ANSWER WITHOUT CHANGING IT — TRIMMING THE BACKCHAT ON THE WAY TO THE
MODEL, WRITING DOWN EVERY TOOL CALL, AND TIMING BOTH FOR THE FACE.
"""

import time

from langchain.agents.middleware import wrap_model_call, wrap_tool_call
from langchain_core.messages import trim_messages

import memory
from memory import settings

TOOL = "tool"
MODEL = "model"

report = None


def watches(handler):
    """BE TOLD HOW LONG EACH PART TOOK. handler(kind, name, seconds)."""
    global report

    report = handler


def tell(kind, name, seconds):
    if report:
        report(kind, name, seconds)


@wrap_model_call
def keep_recent(request, handler):
    """ONLY THE LAST STRETCH OF THE CONVERSATION GOES TO THE MODEL."""
    return handler(request.override(messages=recent(request.messages)))


@wrap_tool_call
def keep_record(request, handler):
    """EVERY TOOL CALL GOES IN THE CONVERSATION, WITH ITS ARGUMENTS AND ITS TIME."""
    started = time.perf_counter()
    result = handler(request)
    taken = time.perf_counter() - started

    call = request.tool_call
    memory.used(call.get("name"), call.get("args"), text(result), taken)
    tell(TOOL, call.get("name"), taken)

    return result


def text(result):
    """WHAT A TOOL ACTUALLY SAID, OUT OF WHATEVER WRAPPER IT CAME BACK IN."""
    return getattr(result, "content", result)


def recent(messages):
    """ONLY THE LAST STRETCH. COUNTED, NOT WEIGHED: A TOKEN COUNT WOULD MEAN A
    TOKENISER PER MODEL."""
    kept = trim_messages(
        messages,
        token_counter=len,
        max_tokens=settings.get("brain.history"),
        strategy="last",
        start_on="human",  # NEVER OPEN ON A TOOL REPLY WHOSE CALL WAS TRIMMED.
        include_system=False,
        allow_partial=False,
    )

    return kept or messages[-1:]
