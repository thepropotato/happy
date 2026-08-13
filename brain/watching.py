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

# WHAT ONE ROUND COST, SAID AS SOON AS THE MODEL COMES BACK AND BEFORE ANY TOOL
# IT ASKED FOR HAS RUN.
SPENT = "spent"

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

# WHAT THE ROUND JUST FINISHED COST, WAITING FOR THE TOOL IT ASKED FOR TO CLAIM
# IT. HELD THE SAME WAY AND FOR THE SAME REASON AS missed ABOVE.
spend = None


class Stuck(Exception):
    """ENOUGH TOOLS IN A ROW SAID NO THAT THE NEXT ONE WOULD TOO."""


def fresh():
    """A NEW TURN. THE STREAK IS ABOUT THIS ERRAND, NOT THE LAST ONE."""
    global missed, spend

    missed = 0
    spend = None


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


@wrap_model_call
def keep_count(request, handler):
    """WHAT EACH ROUND COST, COUNTED WHERE THE MODEL ACTUALLY ANSWERS.

    A TURN IS NOT ONE REQUEST. IT IS A ROUND PER TOOL AND ONE MORE TO ANSWER, AND
    EVERY ONE OF THEM SENDS THE STANDING PROMPT AND ALL FIFTY-ODD TOOL SCHEMAS
    AGAIN — WHICH IS THE WHOLE REASON THIS IS WORTH PUTTING ON SCREEN. SO IT IS
    COUNTED PER ROUND AND ADDED UP BY WHOEVER IS SHOWING IT, NOT COUNTED ONCE.
    """
    global spend

    answered = handler(request)
    spend = counted(answered)

    if spend:
        tell(SPENT, None, None, dict(spend))

    return answered


def counted(answered):
    """WHAT ONE ROUND READ AND WROTE, OR None IF THE BACKEND WILL NOT SAY.

    NOT EVERY SERVER BEHIND THE OPENAI SHAPE REPORTS USAGE, AND A COUNT NOBODY
    SENT IS SHOWN AS NOTHING RATHER THAN AS A ZERO.
    """
    said = getattr(answered, "result", None) or answered

    if isinstance(said, list):
        said = said[-1] if said else None

    usage = getattr(said, "usage_metadata", None) or {}

    if not usage.get("input_tokens") and not usage.get("output_tokens"):
        return None

    return {"read": usage.get("input_tokens", 0), "wrote": usage.get("output_tokens", 0)}


def claim():
    """THE ROUND'S COST, ONCE. TWO TOOLS ASKED FOR TOGETHER SHARE ONE ROUND, AND
    CHARGING BOTH OF THEM FOR IT WOULD COUNT THAT ROUND TWICE."""
    global spend

    taken, spend = spend, None

    return taken


@wrap_tool_call
def keep_record(request, handler):
    """EVERY TOOL CALL GOES ON ITS EXCHANGE, WITH ITS REASON, ARGUMENTS AND TIME."""
    call = request.tool_call

    # READ, NOT TAKEN: THE CALL ITSELF GOES ON UNTOUCHED.
    args, why = asking.without(call)
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

        raise

    taken = time.perf_counter() - started

    why = why or reason(request)

    # THE MARK COMES OFF HERE AND NOWHERE ELSE, SO THE MODEL READS THE SENTENCE
    # THE TOOL MEANT TO SAY AND NEVER THE BOOKKEEPING IN FRONT OF IT.
    said, nope = asking.went(text(result))

    missed = missed + 1 if nope else 0

    memory.used(name, args, said, taken, why, failed=nope, spent=cost)

    tell(
        TOOL,
        name,
        taken,
        {"id": which, "why": why, "args": args, "result": memory.brief(said),
         "failed": nope, "spent": cost},
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
    """THE BACKCHAT BEHIND THIS TURN, CUT DOWN, AND THIS TURN WHOLE.

    THE CUT IS ONLY EVER MADE BEHIND THE TURN IN PROGRESS, AND THAT IS THE POINT.
    A WINDOW THAT SLID WITH EVERY TOOL ROUND MOVED THE FIRST TOKEN AFTER THE
    STANDING PROMPT EACH TIME, SO A SERVER THAT HAD ALREADY READ THE PROMPT AND
    THE TOOL LIST — TENS OF THOUSANDS OF TOKENS, THE SAME ONES EVERY REQUEST —
    HAD TO READ THEM ALL AGAIN FOR EVERY ROUND. HELD STILL, THE ROUNDS AFTER THE
    FIRST PAY ONLY FOR THE TOOL RESULT THAT JUST CAME BACK.

    IT ALSO CANNOT CUT A TOOL REPLY AWAY FROM THE CALL THAT ASKED FOR IT, WHICH
    IS WHAT USED TO HAPPEN TO ANY ERRAND LONGER THAN THE WINDOW: NOTHING LEFT IN
    IT WAS A HUMAN MESSAGE, SO THE TRIM CAME BACK EMPTY AND THE MODEL WAS HANDED
    ONE LONE TOOL RESULT WITH NO IDEA WHAT IT HAD BEEN ASKED FOR.
    """
    began = opened(messages)

    return settled(messages[:began]) + messages[began:]


def opened(messages):
    """WHERE THE TURN IN PROGRESS STARTS: THE LAST THING A PERSON SAID."""
    for index in range(len(messages) - 1, -1, -1):
        if getattr(messages[index], "type", "") == "human":
            return index

    return 0


def settled(messages):
    """THE TURNS ALREADY FINISHED, DOWN TO THE LAST STRETCH. COUNTED, NOT
    WEIGHED: A TOKEN COUNT WOULD MEAN A TOKENISER PER MODEL."""
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
