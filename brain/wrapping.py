"""WHAT WRAPS EVERY CALL: WHAT GOES IN, WHAT IS KEPT, AND HOW LONG IT TOOK."""

import difflib
import json
import time

from langchain.agents.middleware import wrap_model_call, wrap_tool_call
from langchain_core.messages import HumanMessage, ToolMessage

import memory
from brain.history import recent
from hands import reasons
from memory import settings

TOOL = "tool"

# THE SAME CALL, SAID BEFORE IT RUNS.
STARTED = "tool.started"

MODEL = "model"

# WHAT ONE ROUND COST, SAID AS SOON AS THE MODEL COMES BACK AND BEFORE ANY TOOL
# IT ASKED FOR HAS RUN.
SPENT = "spent"

# THREE IN A ROW GETTING NOWHERE.
ENOUGH = 3

# HOW THE CALL LIMIT SAYS SO, IN ITS OWN WORDS: "Model call limits exceeded: run
# limit (14/14)". EVERY WORD OF A REPLY IS READ OUT LOUD, AND THAT IS A COUNTER.
LIMIT = "Model call limits exceeded"

NOWHERE = (
    "That is not getting anywhere — three goes in a row came back with nothing. "
    "Tell me a bit more about what you are after and I will try it another way."
)

# HOW THE BACKEND SAYS THE MODEL WROTE SOMETHING IN A TOOL CALL THAT IS NOT JSON.
UNPARSED = ("error parsing tool call", "invalid tool call", "failed to parse tool")

# HOW MANY GOES ONE OF THOSE GETS BEFORE THE ROUND GIVES UP ON IT.
TRIES = 3

# TEMPERATURE IS USUALLY 0, SO AN UNCHANGED REQUEST WOULD COME BACK WORD FOR WORD
# THE SAME. NAMING THE MISTAKE IS WHAT MAKES THE NEXT GO DIFFERENT.
AGAIN = (
    "Your last tool call could not be read: {trouble}. Tool arguments must be "
    "finished JSON values and never expressions — write the whole string out in "
    'full instead of anything like "hello" * 100 or "a" + "b". Make the call again.'
)

# WHAT A CALL IS TOLD WHEN THE TOOL BEHIND IT THREW INSTEAD OF ANSWERING.
BROKEN = "That tool did not run: {trouble}"

report = None

# HOW THE FACE IS SHOWN THE RAW DETAIL OF A FAILURE HAPPY WILL ONLY SUMMARISE ALOUD.
shown = None

# AND HOW IT IS TOLD WHAT IS BEING STARTED, IN TIME TO SAY SO ABOVE IT.
noted = None

# HOW MANY TOOLS IN A ROW HAVE SAID NO.
missed = 0

# WHAT THE ROUND JUST FINISHED COST, WAITING FOR THE TOOL IT ASKED FOR TO CLAIM IT.
spend = None


class Stuck(Exception):
    """ENOUGH TOOLS IN A ROW SAID NO THAT THE NEXT ONE WOULD TOO."""


def fresh():
    """A NEW TURN. THE STREAK IS ABOUT THIS ERRAND, NOT THE LAST ONE."""
    global missed, spend

    missed = 0
    spend = None
    asked.clear()


# EVERY CALL MADE THIS TURN, BY TOOL AND ARGUMENTS, WITH WHAT IT GOT BACK.
asked = {}

REPEATED = (
    "You already called this with exactly these arguments this turn, and the answer is above. "
    "Use it, or change the arguments or the tool."
)

# A TOOL THAT READS A CHANGING THING MAY HONESTLY BE ASKED TWICE: THE SCREEN MOVES, A BUILD
# FINISHES. EVERYTHING ELSE ANSWERS THE SAME WAY TO THE SAME QUESTION WITHIN ONE TURN.
CHANGING = {"current_activity", "screen", "list_open_windows",
            "already_open", "build", "play_pause", "list_controls", "file_in_front",
            "reminder", "system_control"}


def signature(name, args):
    return name, json.dumps(args, sort_keys=True, default=str)


UNMOVED = (
    "You have looked at this twice this turn and it has not changed, so looking again will not "
    "either. Use what it said, or ask a different tool."
)


def repeated(name, args):
    """WHY THIS EXACT CALL SHOULD NOT RUN AGAIN THIS TURN, OR None. A TOOL THAT READS SOMETHING
    THAT MOVES MAY BE ASKED TWICE, BUT TWICE THE SAME ANSWER MEANS IT IS NOT MOVING."""
    got = asked.get(signature(name, args)) or []

    if not got:
        return None

    if name not in CHANGING:
        return REPEATED

    return UNMOVED if len(got) >= 2 and got[-1] == got[-2] else None


def remember(name, args, said):
    asked.setdefault(signature(name, args), []).append(said)


def watches(handler):
    """BE TOLD HOW LONG EACH PART TOOK."""
    global report

    report = handler


def tell(kind, name, seconds, about=None):
    if report:
        report(kind, name, seconds, about)


def troubles(handler):
    """BE SHOWN WHAT WENT WRONG, IN THE BACKEND'S OWN WORDS."""
    global shown

    shown = handler


def amiss(said):
    if shown:
        shown(said)


def doings(handler):
    """BE TOLD WHAT IS BEING STARTED, FOR PUTTING A LINE OVER THE TOOLS IT IS ABOUT TO USE."""
    global noted

    noted = handler


def doing(said):
    if noted:
        noted(said)


@wrap_model_call
def keep_recent(request, handler):
    """ONLY THE LAST STRETCH OF THE CONVERSATION GOES TO THE MODEL."""
    return handler(request.override(messages=recent(request.messages)))


@wrap_model_call
def keep_trying(request, handler):
    """A TOOL CALL THE BACKEND COULD NOT READ IS A MISTAKE TO NAME, NOT THE END OF A TURN."""
    for left in range(TRIES - 1, -1, -1):
        try:
            return handler(request)
        except Exception as error:
            said = str(error)

            if not left or not unparsed(said):
                raise

            amiss(said)

            # THE MODEL'S BAD ANSWER NEVER MADE IT ONTO THE CONVERSATION, SO THE
            # CORRECTION GOES ON AS THE NEXT THING SAID TO IT.
            request = request.override(
                messages=list(request.messages) + [HumanMessage(AGAIN.format(trouble=said))]
            )


def unparsed(said):
    """WHETHER A FAILURE IS THE MODEL WRITING A BAD TOOL CALL, WHICH IS WORTH ANOTHER GO."""
    lowered = said.lower()

    return any(each in lowered for each in UNPARSED)


# HOW CLOSE A MISSPELT TOOL NAME HAS TO BE TO THE REAL ONE TO BE TAKEN AS IT.
CLOSE = 0.75


@wrap_model_call
def keep_named(request, handler):
    """A TOOL NAME THE MODEL GOT NEARLY RIGHT IS PUT RIGHT BEFORE IT IS LOOKED UP. A FAILED
    LOOKUP COSTS A WHOLE ROUND, AND openApp OR open_app_tool MEANS open_app TO ANYBODY."""
    answered = handler(request)
    message = getattr(answered, "result", None) or answered

    if isinstance(message, list):
        message = message[-1] if message else None

    calls = getattr(message, "tool_calls", None) or []
    known = [each.name for each in request.tools or []]

    for call in calls:
        fixed = nearest(call.get("name") or "", known)

        if fixed and fixed != call.get("name"):
            amiss(f"tool {call.get('name')} taken as {fixed}")
            call["name"] = fixed

    return answered


def nearest(name, known):
    """THE REAL TOOL A NAME MEANS, OR None WHEN IT IS RIGHT ALREADY OR NOTHING IS CLOSE."""
    if not known or name in known:
        return None

    plain = name.lower().replace("-", "_").removesuffix("_tool").removeprefix("functions.")
    snake = "".join(f"_{c.lower()}" if c.isupper() else c for c in plain).strip("_")

    for candidate in (plain, snake):
        if candidate in known:
            return candidate

    close = difflib.get_close_matches(snake, known, n=1, cutoff=CLOSE)

    return close[0] if close else None


@wrap_model_call
def keep_count(request, handler):
    """WHAT EACH ROUND COST, COUNTED WHERE THE MODEL ACTUALLY ANSWERS."""
    global spend

    answered = handler(request)
    spend = counted(answered)

    if spend:
        tell(SPENT, None, None, dict(spend))

    return answered


def counted(answered):
    """WHAT ONE ROUND READ AND WROTE, OR None IF THE BACKEND WILL NOT SAY."""
    said = getattr(answered, "result", None) or answered

    if isinstance(said, list):
        said = said[-1] if said else None

    usage = getattr(said, "usage_metadata", None) or {}

    if not usage.get("input_tokens") and not usage.get("output_tokens"):
        return None

    return {"read": usage.get("input_tokens", 0), "wrote": usage.get("output_tokens", 0)}


def claim():
    """THE ROUND'S COST, ONCE."""
    global spend

    taken, spend = spend, None

    return taken


@wrap_tool_call
def keep_record(request, handler):
    """EVERY TOOL CALL GOES ON ITS EXCHANGE, WITH ITS REASON, ARGUMENTS AND TIME."""
    call = request.tool_call

    # READ, NOT TAKEN: THE CALL ITSELF GOES ON UNTOUCHED.
    args, why = reasons.without(call)
    name = call.get("name")

    # THE ID TIES THE STARTED AND FINISHED REPORTS TO THE ONE ROW.
    which = call.get("id") or f"{name}-{id(call)}"

    # THE SAME TOOL WITH THE SAME ARGUMENTS GIVES THE SAME ANSWER, AND ASKING TWICE IN ONE TURN
    # IS THE SHAPE EVERY STUCK RUN TAKES. THE ANSWER IT ALREADY HAS IS POINTED AT INSTEAD.
    refusal = repeated(name, args)

    if refusal is not None:
        global missed

        missed += 1
        memory.used(name, args, refusal, 0.0, why, failed=True, spent=claim())
        tell(TOOL, name, 0.0, {"id": which, "why": why, "args": args, "result": refusal,
                               "failed": True, "spent": None})

        return ToolMessage(content=refusal, name=name, tool_call_id=call.get("id") or "", status="error")

    # THE ROUND THAT ASKED FOR THIS CALL, AND WHAT READING THE WHOLE PROMPT AGAIN
    # TO ASK FOR IT COST. TAKEN ON THE WAY IN SO THE FIRST TOOL OF A ROUND GETS IT.
    cost = claim()

    tell(STARTED, name, None, {"id": which, "args": args})

    started = time.perf_counter()

    try:
        result = handler(request)
    except Exception as error:
        taken = time.perf_counter() - started
        gone = {"id": which, "why": why, "args": args, "result": str(error),
                "failed": True, "spent": cost}

        memory.used(name, args, str(error), taken, why, failed=True, spent=cost)
        tell(TOOL, name, taken, gone)

        missed += 1

        # A TOOL THAT THREW IS A TOOL THAT SAID NO, NOT THE END OF THE TURN: THE CALL
        # STILL GETS ITS REPLY, BECAUSE ONE LEFT UNANSWERED BREAKS EVERY TURN AFTER IT.
        return crashed(call, name, str(error))

    taken = time.perf_counter() - started

    why = why or reason(request)

    # THE MARK COMES OFF HERE AND NOWHERE ELSE, SO THE MODEL READS THE SENTENCE
    # THE TOOL MEANT TO SAY AND NEVER THE BOOKKEEPING IN FRONT OF IT.
    said, nope = reasons.went(text(result))

    missed = missed + 1 if nope else 0
    remember(name, args, said)

    memory.used(name, args, said, taken, why, failed=nope, spent=cost)

    tell(
        TOOL,
        name,
        taken,
        {"id": which, "why": why, "args": args, "result": memory.brief(said),
         "failed": nope, "spent": cost},
    )

    return plainly(result, said, nope)


@wrap_model_call
def keep_going(request, handler):
    """ENOUGH TOOLS IN A ROW SAID NO, SO THE TURN ENDS BEFORE THE MODEL IS ASKED FOR ANOTHER
    ONE. STOPPING HERE AND NOT PART WAY THROUGH A TOOL IS WHAT LEAVES THE CALL ALREADY MADE
    WITH THE REPLY THE CONVERSATION NEEDS IT TO HAVE."""
    if missed >= ENOUGH:
        raise Stuck(NOWHERE)

    return handler(request)


def crashed(call, name, trouble):
    """THE REPLY THAT STANDS IN FOR A TOOL THAT THREW."""
    return ToolMessage(
        content=BROKEN.format(trouble=trouble),
        name=name,
        tool_call_id=call.get("id") or "",
        status="error",
    )


def plainly(result, said, nope):
    """THE ANSWER WITH THE MARK OFF IT, AND THE ORDINARY status FIELD ON INSTEAD."""
    if not hasattr(result, "model_copy"):
        return said

    changed = {"content": said}

    if nope:
        changed["status"] = "error"

    return result.model_copy(update=changed)


def reason(request):
    """WHY THIS CALL, IN THE MODEL'S OWN WORDS BEFORE IT REACHED FOR THE TOOL."""
    wanted = request.tool_call.get("id")

    for message in reversed(request.state.get("messages", [])):
        if any(each.get("id") == wanted for each in getattr(message, "tool_calls", None) or []):
            return (message.text or "").strip() or None

    return None


def text(result):
    """WHAT A TOOL ACTUALLY SAID, OUT OF WHATEVER WRAPPER IT CAME BACK IN."""
    return getattr(result, "content", result)

