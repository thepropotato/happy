"""WHAT WRAPS EVERY CALL: WHAT GOES IN, WHAT IS KEPT, AND HOW LONG IT TOOK.

THE GRAPH NEXT DOOR IS ABOUT ANSWERING. THIS IS ABOUT EVERYTHING THAT HAPPENS
AROUND ONE ANSWER WITHOUT CHANGING IT — TRIMMING THE BACKCHAT ON THE WAY TO THE
MODEL, WRITING DOWN EVERY TOOL CALL, AND TIMING BOTH FOR THE FACE.
"""

import time

from langchain.agents.middleware import wrap_model_call, wrap_tool_call
from langchain_core.messages import trim_messages

import memory
from hands import asking
from memory import settings

TOOL = "tool"

# THE SAME CALL, SAID BEFORE IT RUNS.
STARTED = "tool.started"

MODEL = "model"

# THREE IN A ROW GETTING NOWHERE. TWO IS A RETRY, WHICH IS OFTEN THE RIGHT MOVE
# AND IS ASKED FOR BY NAME IN THE STANDING PROMPT: THE OTHER SPELLING, THE OTHER
# WORDING, WAIT AND GO AGAIN. THREE IS THE SAME LOCKED DOOR A THIRD TIME.
ENOUGH = 3

NOWHERE = (
    "That is not getting anywhere — three goes in a row came back with nothing. "
    "Tell me a bit more about what you are after and I will try it another way."
)

report = None

# HOW MANY TOOLS IN A ROW HAVE SAID NO. ONE TURN RUNS AT A TIME, HELD BY THE LOCK
# IN main.py, SO THIS IS PER ERRAND WITHOUT HAVING TO BE THREADED THROUGH ONE.
missed = 0


class Stuck(Exception):
    """ENOUGH TOOLS IN A ROW SAID NO THAT THE NEXT ONE WOULD TOO."""


def fresh():
    """A NEW TURN. THE STREAK IS ABOUT THIS ERRAND, NOT THE LAST ONE."""
    global missed

    missed = 0


def watches(handler):
    """BE TOLD HOW LONG EACH PART TOOK. handler(kind, name, seconds, about).

    about IS WHAT A FACE MIGHT SHOW ABOUT ONE CALL, OR None. A DICT AND NOT THREE
    MORE ARGUMENTS, BECAUSE EVERY FACE THAT DOES NOT CARE STILL HAS TO SPELL THEM.
    """
    global report

    report = handler


def tell(kind, name, seconds, about=None):
    if report:
        report(kind, name, seconds, about)


@wrap_model_call
def keep_recent(request, handler):
    """ONLY THE LAST STRETCH OF THE CONVERSATION GOES TO THE MODEL."""
    return handler(request.override(messages=recent(request.messages)))


@wrap_tool_call
def keep_record(request, handler):
    """EVERY TOOL CALL GOES ON ITS EXCHANGE, WITH ITS REASON, ARGUMENTS AND TIME."""
    call = request.tool_call

    # READ, NOT TAKEN: THE CALL ITSELF GOES ON UNTOUCHED.
    args, why = asking.without(call)
    name = call.get("name")

    # THE ID TIES THE STARTED AND FINISHED REPORTS TO THE ONE ROW.
    which = call.get("id") or f"{name}-{id(call)}"

    tell(STARTED, name, None, {"id": which, "args": args})

    started = time.perf_counter()

    global missed

    try:
        result = handler(request)
    except Exception as error:
        taken = time.perf_counter() - started
        gone = {"id": which, "why": why, "args": args, "result": str(error), "failed": True}

        memory.used(name, args, str(error), taken, why, failed=True)
        tell(TOOL, name, taken, gone)

        raise

    taken = time.perf_counter() - started

    why = why or reason(request)

    # THE MARK COMES OFF HERE AND NOWHERE ELSE, SO THE MODEL READS THE SENTENCE
    # THE TOOL MEANT TO SAY AND NEVER THE BOOKKEEPING IN FRONT OF IT.
    said, nope = asking.went(text(result))

    missed = missed + 1 if nope else 0

    memory.used(name, args, said, taken, why, failed=nope)

    tell(
        TOOL,
        name,
        taken,
        {"id": which, "why": why, "args": args, "result": memory.brief(said), "failed": nope},
    )

    if missed >= ENOUGH:
        raise Stuck(NOWHERE)

    return plainly(result, said, nope)


def plainly(result, said, nope):
    """THE ANSWER WITH THE MARK OFF IT, AND THE ORDINARY status FIELD ON INSTEAD.

    status IS WHERE A TOOL RESULT IS SUPPOSED TO SAY IT WENT WRONG, SO ANYTHING
    READING THE CONVERSATION AFTERWARDS GETS IT WITHOUT KNOWING ABOUT ANY OF THIS.
    """
    if not hasattr(result, "model_copy"):
        return said

    changed = {"content": said}

    if nope:
        changed["status"] = "error"

    return result.model_copy(update=changed)


def reason(request):
    """WHY THIS CALL, IN THE MODEL'S OWN WORDS BEFORE IT REACHED FOR THE TOOL.

    THE FALLBACK NOW THAT why IS ASKED FOR OUTRIGHT, FOR THE ONE TOOL IN A HUNDRED
    WHOSE SCHEMA WOULD NOT TAKE IT. None WHEN THE MODEL SAID NOTHING EITHER.
    """
    wanted = request.tool_call.get("id")

    for message in reversed(request.state.get("messages", [])):
        if any(each.get("id") == wanted for each in getattr(message, "tool_calls", None) or []):
            return (message.text or "").strip() or None

    return None


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
