"""WHAT WRAPS EVERY CALL: WHAT GOES IN, WHAT IS KEPT, AND HOW LONG IT TOOK."""

import collections
import difflib
import json
import re
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

# WHAT SAID NO THIS TURN AND HAS NOT BEEN PUT RIGHT SINCE: {tool name: what it said}. A TOOL
# THAT LATER WORKS TAKES ITS OWN NAME BACK OFF, SO WHAT IS LEFT AT THE END IS ONLY WHAT
# REALLY DID NOT HAPPEN.
refused = {}

# EVERY TOOL THAT HAS RUN THIS TURN, IN ORDER. A TOOL THAT MUST NOT BE THE FIRST THING A
# TURN DOES CAN ASK WHAT CAME BEFORE IT.
ran = []


class Stuck(Exception):
    """ENOUGH TOOLS IN A ROW SAID NO THAT THE NEXT ONE WOULD TOO."""


def fresh():
    """A NEW TURN. THE STREAK IS ABOUT THIS ERRAND, NOT THE LAST ONE."""
    global missed, spend

    missed = 0
    spend = None
    asked.clear()
    tried.clear()
    refused.clear()
    ran.clear()


# EVERY CALL MADE THIS TURN, BY TOOL AND ARGUMENTS, WITH WHAT IT GOT BACK.
asked = {}

# THE TOOLS THAT GO AND LOOK SOMETHING UP, WHERE ASKING AGAIN IN OTHER WORDS IS THE THING A
# MODEL DOES INSTEAD OF ADMITTING IT CANNOT FIND IT.
SEARCHING = {"search_web", "read_page", "find_files"}

# WHAT EACH OF THOSE HAS BEEN ASKED THIS TURN, AS THE GIST RATHER THAN THE WORDING.
tried = collections.defaultdict(list)

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


# HOW MANY TIMES ONE TOOL MAY BE ASKED THE SAME QUESTION IN DIFFERENT WORDS BEFORE IT IS
# CLEAR THE WORDING IS NOT THE PROBLEM. THREE IS ENOUGH TO TRY A REPHRASE AND A NARROWING.
ENOUGH_TRIES = 3

CIRCLING = (
    "You have asked {name} {count} times this turn and it keeps coming back with the same "
    "thing. Rewording the question is not going to change the answer — what is being looked "
    "for is not there. Use the best of what you already have and answer them now, or say "
    "plainly that it could not be found. Do not search again."
)

# THE LITTLE WORDS THAT MAKE TWO SEARCHES LOOK DIFFERENT WITHOUT ASKING ANYTHING DIFFERENT.
NOISE = {"the", "a", "an", "of", "in", "on", "for", "to", "and", "latest", "new", "newest",
         "recent", "video", "videos", "channel", "id", "list", "page", "official", "full"}


def gist(args):
    """WHAT A CALL IS REALLY ASKING, WITH THE WORDING TAKEN OFF. "Barbell latest video" AND
    "Barbell newest video 2026" ARE ONE QUESTION ASKED TWICE, AND COUNTING THEM AS TWO IS HOW
    A TURN GOT TO FOURTEEN SEARCHES."""
    words = " ".join(str(each) for each in args.values()).lower()
    kept = {each for each in re.findall(r"[a-z0-9]+", words) if each not in NOISE and not each.isdigit()}

    return frozenset(kept)


# TWO QUESTIONS SHARING THIS MUCH OF THEIR MEANING ARE THE SAME QUESTION. AN EXACT MATCH WAS
# NO USE: ONE EXTRA WORD MADE "Romanchakam Barbell review" AND "Romanchakam Barbell review
# youtube" COUNT AS TWO, AND A TURN GOT NINE GOES OUT OF THAT.
MOSTLY_SAME = 0.7


def alike(one, other):
    """WHETHER TWO GISTS ARE ASKING THE SAME THING, ALLOWING A WORD EITHER WAY."""
    if not one or not other:
        return one == other

    return len(one & other) / max(len(one), len(other)) >= MOSTLY_SAME


def circling(name, args):
    """WHY THIS TOOL SHOULD NOT BE ASKED THE SAME THING AGAIN, OR None."""
    if name not in SEARCHING:
        return None

    asking = gist(args)
    same = [each for each in tried[name] if alike(each, asking)]

    return CIRCLING.format(name=name, count=len(same) + 1) if len(same) >= ENOUGH_TRIES else None


def remember(name, args, said):
    asked.setdefault(signature(name, args), []).append(said)

    if name in SEARCHING:
        tried[name].append(gist(args))


def learned():
    """EVERYTHING EVERY TOOL HANDED BACK THIS TURN, AS ONE BLOCK OF TEXT.

    THIS IS THE WHOLE OF WHAT HAPPY HAS ACTUALLY BEEN TOLD SINCE THE PERSON SPOKE. ANYTHING
    IN AN ANSWER OR A FILE THAT IS NOT SOMEWHERE IN HERE CAME OUT OF THE MODEL RATHER THAN
    OUT OF THE WORLD."""
    return "\n".join(said for got in asked.values() for said in got)


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


# WHAT A REPLY IS TOLD WHEN IT WOULD HAVE CLAIMED SOMETHING THAT DID NOT HAPPEN.
DENIED = (
    "Stop. These were asked for this turn and did NOT happen:\n{undone}\n\n"
    "The answer you just wrote says one of them worked. It did not. Either do the thing now "
    "with a tool that will actually do it, or say plainly that it did not happen and why. "
    "Never tell them something is done, saved, created, opened or sent unless a tool this "
    "turn came back saying so."
)

# HOW A REPLY CLAIMS A THING HAPPENED, AND HOW IT OWNS THAT ONE DID NOT. A REPLY THAT OWNS IT
# IS ALLOWED TO ALSO SAY WHAT IT DID MANAGE, SO OWNING IT ALWAYS WINS.
CLAIMS = ("i've ", "i have ", "here's ", "here is ", "it's open", "its open", "saved", "created",
          "made ", "opened", "sent ", "written", "wrote ", "done", "all set", "ready for you")

OWNS = ("could not", "couldn't", "cannot", "can't", "not able", "did not", "didn't", "unable",
        "failed", "no luck", "nothing was", "wasn't able", "was not able", "not there",
        "does not exist", "doesn't exist", "already exists")


# A REFUSAL THAT WAS REALLY AN INSTRUCTION MARKS ITSELF WITH THIS, AND A TURN MAY NOT END
# ON AN APOLOGY WHILE ONE OF THEM IS STILL OUTSTANDING.
CARRY_ON = "not a refusal of it"

# HOW A REPLY GIVES UP: IT IS SORRY, AND IT IS NOT TELLING THEM ANYTHING ELSE.
GIVES_UP = ("i'm sorry", "im sorry", "i am sorry", "sorry,", "i can't", "i cannot", "i can not",
            "unable to", "not able to", "afraid i")

GAVE_UP = (
    "Stop. That was not a refusal, it was the next step, and it told you what to do:\n\n"
    "{undone}\n\n"
    "You have not done it yet and you have just apologised instead. Do it now, in this turn, "
    "with the tools it named, and then finish the job they actually asked for. Do not say "
    "sorry and do not ask them anything."
)


# WHAT A TURN SAYS WHEN IT HAS TALKED ITSELF OUT OF A JOB IT CAN DO, AND THE TOOL THAT DOES
# IT. THE MODEL BELIEVES IT CANNOT MAKE AN OFFICE FILE, BECAUSE MOST MODELS CANNOT; SAYING SO
# IN THE PROMPT DID NOT MOVE IT, SO THE ANSWER IS TURNED BACK HERE INSTEAD.
DISOWNED = {
    "write_document": ("powerpoint", "power point", "presentation", "slide deck", "pptx",
                       "word document", "docx", "spreadsheet", "excel", "xlsx"),
}

# HOW IT SAYS IT CANNOT, AS OPPOSED TO SAYING IT DID NOT.
DISCLAIMS = ("can't create", "cannot create", "can not create", "can't make", "cannot make",
             "unable to create", "unable to make", "can't generate", "cannot generate",
             "don't have the ability", "do not have the ability", "not able to create",
             "copy it into", "copy into a presentation", "paste it into")

DISOWNED_TOLD = (
    "That is not true and you have the tool for it. {name} makes a real {kind} on their disk "
    "that opens in the app that owns it, and it is bound to you right now. Do not offer them "
    "text to copy out by hand. Find out what it is about with the tools that look, then call "
    "{name} and actually make the file."
)


def disowning(words):
    """THE TOOL AND THE THING A REPLY HAS JUST SAID IT CANNOT MAKE, OR None."""
    if not any(each in words for each in DISCLAIMS):
        return None

    for name, kinds in DISOWNED.items():
        for kind in kinds:
            if kind in words:
                return name, kind

    return None


@wrap_model_call
def keep_able(request, handler):
    """A TURN MAY NOT SAY IT CANNOT DO A THING IT HAS A TOOL FOR.

    THIS IS NOT THE SAME AS GIVING UP AFTER A REFUSAL: NOTHING REFUSED, NOTHING WAS EVEN
    TRIED. THE MODEL DECLINED THE JOB OUT OF A BELIEF ABOUT ITSELF THAT IS WRONG HERE, AND
    THE ONE PLACE THAT CAN BE CAUGHT IS THE ANSWER ON ITS WAY OUT."""
    answered = handler(request)
    said = getattr(answered, "result", None) or answered

    if isinstance(said, list):
        said = said[-1] if said else None

    if getattr(said, "tool_calls", None):
        return answered

    words = (getattr(said, "text", "") or "").lower()
    found = disowning(words) if words.strip() else None

    if not found:
        return answered

    name, kind = found
    told = request.override(
        messages=list(request.messages) + [HumanMessage(DISOWNED_TOLD.format(name=name, kind=kind))]
    )

    return handler(told)


@wrap_model_call
def keep_at_it(request, handler):
    """A TURN MAY NOT GIVE UP WHILE A TOOL IS STILL HOLDING THE DOOR OPEN FOR IT.

    A GUARD THAT SAYS "GO AND LOOK, THEN CALL ME AGAIN" IS A STEP OF THE ERRAND. THE MODEL AT
    LOW EFFORT READS ANY REFUSAL AS THE END AND ANSWERS "I can't create that presentation",
    WHICH IS HONEST AND STILL LEAVES THE JOB UNDONE. TELLING IT SO IN THE TOOL'S OWN WORDS DID
    NOT WORK; BEING SENT BACK ONCE DOES."""
    answered = handler(request)

    waiting = [said for said in refused.values() if CARRY_ON in said]

    if not waiting or not surrendering(answered):
        return answered

    told = request.override(
        messages=list(request.messages) + [HumanMessage(GAVE_UP.format(undone="\n\n".join(waiting)))]
    )

    return handler(told)


def surrendering(answered):
    """WHETHER THESE WORDS ARE AN APOLOGY FOR NOT DOING IT RATHER THAN AN ANSWER."""
    said = getattr(answered, "result", None) or answered

    if isinstance(said, list):
        said = said[-1] if said else None

    if getattr(said, "tool_calls", None):
        return False

    words = (getattr(said, "text", "") or "").lower()

    return bool(words.strip()) and any(each in words for each in GIVES_UP)


@wrap_model_call
def keep_honest(request, handler):
    """A REPLY MAY NOT SAY A THING HAPPENED WHEN THE TOOL THAT WOULD HAVE DONE IT SAID NO.

    THIS IS THE ONE PLACE IT CAN BE CAUGHT FOR EVERY TOOL AT ONCE. THE MODEL HAS ALREADY BEEN
    TOLD, IN THE TOOL'S OWN WORDS, THAT IT FAILED; WHAT THIS ADDS IS THAT IT CANNOT THEN GO ON
    TO SAY OTHERWISE. IT IS SENT BACK ONCE, WHICH IS ENOUGH — IT EITHER DOES THE THING OR SAYS
    IT DID NOT HAPPEN, AND BOTH OF THOSE ARE HONEST ANSWERS."""
    answered = handler(request)

    if not refused or not claiming(answered):
        return answered

    told = request.override(
        messages=list(request.messages) + [HumanMessage(DENIED.format(undone="\n".join(unfinished())))]
    )

    return handler(told)


def claiming(answered):
    """WHETHER THESE WORDS TELL SOMEBODY A THING WAS DONE WITHOUT OWNING THAT IT WAS NOT."""
    said = getattr(answered, "result", None) or answered

    if isinstance(said, list):
        said = said[-1] if said else None

    # A ROUND THAT ASKED FOR MORE TOOLS IS NOT THE ANSWER YET, SO THERE IS NOTHING TO CHECK.
    if getattr(said, "tool_calls", None):
        return False

    words = (getattr(said, "text", "") or "").lower()

    if not words.strip():
        return False

    return any(each in words for each in CLAIMS) and not any(each in words for each in OWNS)


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
    # AND THE SAME QUESTION IN NEW WORDS, WHICH IS THE SHAPE THE OTHER HALF OF THEM TAKE: A
    # TURN ONCE PUT THE SAME SEARCH THROUGH FOURTEEN REWORDINGS AND THEN GAVE UP ANYWAY.
    refusal = repeated(name, args) or circling(name, args)

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

    ran.append(name)

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

        noting(name, str(error), True)
        missed += 1

        # A TOOL THAT THREW IS A TOOL THAT SAID NO, NOT THE END OF THE TURN: THE CALL
        # STILL GETS ITS REPLY, BECAUSE ONE LEFT UNANSWERED BREAKS EVERY TURN AFTER IT.
        return crashed(call, name, str(error))

    taken = time.perf_counter() - started

    why = why or reason(request)

    # THE MARK COMES OFF HERE AND NOWHERE ELSE, SO THE MODEL READS THE SENTENCE
    # THE TOOL MEANT TO SAY AND NEVER THE BOOKKEEPING IN FRONT OF IT.
    said, nope = reasons.went(text(result))

    # A GUARD THAT TURNED A CALL BACK AND TOLD IT WHAT TO DO NEXT IS NOT A TOOL THAT FAILED.
    # COUNTING THOSE TOWARDS "ENOUGH SAID NO, STOP THE TURN" WOULD END A TURN THAT IS BEING
    # CORRECTED THREE TIMES ON ITS WAY TO GETTING THE JOB RIGHT, WHICH IS THE OPPOSITE OF WHAT
    # THEY ARE FOR.
    missed = 0 if (not nope or CARRY_ON in said) else missed + 1
    noting(name, said, nope)
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


def noting(name, said, nope):
    """WHAT THIS TOOL JUST DID, KEPT ONLY WHILE IT IS STILL UNDONE.

    A TOOL THAT SAYS NO AND IS THEN MADE TO WORK HAS NOT FAILED THE TURN, SO ITS NAME COMES
    STRAIGHT BACK OFF. WHAT IS LEFT WHEN THE TURN ENDS IS THE THING THAT NEVER HAPPENED."""
    if nope:
        refused[name] = said
    else:
        refused.pop(name, None)


def already(*names):
    """WHETHER ANY OF THESE HAS ALREADY RUN THIS TURN."""
    return any(name in ran for name in names)


def unfinished():
    """WHAT WAS ASKED FOR THIS TURN AND DID NOT HAPPEN, AS ONE LINE EACH, NEWEST LAST."""
    return [f"{name}: {said}" for name, said in refused.items()]


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

