"""WHAT WRAPS EVERY CALL: WHAT GOES IN, WHAT IS KEPT, AND HOW LONG IT TOOK."""

import time

from langchain.agents.middleware import wrap_model_call, wrap_tool_call
from langchain_core.messages import HumanMessage, ToolMessage, trim_messages

import memory
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

# WHAT A CALL IS TOLD WHEN THE RUN THAT ASKED FOR IT STOPPED BEFORE IT CAME BACK.
UNFINISHED = "That call was never finished."

report = None

# HOW THE FACE IS SHOWN THE RAW DETAIL OF A FAILURE HAPPY WILL ONLY SUMMARISE ALOUD.
shown = None

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

    # THE ROUND THAT ASKED FOR THIS CALL, AND WHAT READING THE WHOLE PROMPT AGAIN
    # TO ASK FOR IT COST. TAKEN ON THE WAY IN SO THE FIRST TOOL OF A ROUND GETS IT.
    cost = claim()

    tell(STARTED, name, None, {"id": which, "args": args})

    started = time.perf_counter()

    global missed

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


def recent(messages):
    """THE BACKCHAT BEHIND THIS TURN, CUT DOWN, AND THIS TURN WHOLE."""
    began = opened(messages)

    return answered(settled(messages[:began]) + messages[began:])


def answered(messages):
    """EVERY TOOL CALL WITH A REPLY BEHIND IT. A RUN THAT STOPPED BETWEEN ASKING FOR A TOOL
    AND HEARING BACK LEAVES ONE WITHOUT, AND A BACKEND REFUSES THE WHOLE CONVERSATION OVER
    IT — NOT JUST THAT TURN BUT EVERY TURN AFTER IT."""
    whole = []

    for index, message in enumerate(messages):
        whole.append(message)

        whole += [
            ToolMessage(content=UNFINISHED, tool_call_id=each)
            for each in unreplied(message, messages[index + 1:])
        ]

    return whole


def unreplied(message, after):
    """THE CALLS THIS MESSAGE ASKED FOR THAT NOTHING AFTER IT ANSWERS."""
    wanted = [each.get("id") for each in getattr(message, "tool_calls", None) or []]

    if not wanted:
        return []

    replied = {getattr(each, "tool_call_id", None) for each in after}

    return [each for each in wanted if each and each not in replied]


def opened(messages):
    """WHERE THE TURN IN PROGRESS STARTS: THE LAST THING A PERSON SAID."""
    for index in range(len(messages) - 1, -1, -1):
        if getattr(messages[index], "type", "") == "human":
            return index

    return 0


def settled(messages):
    """THE TURNS ALREADY FINISHED, DOWN TO THE LAST STRETCH."""
    if not messages:
        return []

    return trim_messages(
        messages,
        token_counter=len,
        max_tokens=settings.get("brain.history"),
        strategy="last",
        start_on="human",  # NEVER OPEN ON A TOOL REPLY WHOSE CALL WAS TRIMMED.
        include_system=False,
        allow_partial=False,
    )
