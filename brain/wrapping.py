"""WHAT WRAPS EVERY CALL: WHAT GOES IN, WHAT IS KEPT, AND HOW LONG IT TOOK."""

import collections
import difflib
import json
import re
import time
import uuid

from langchain.agents.middleware import wrap_model_call, wrap_tool_call
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

import memory
from brain import mending, repeats, sourcing
from brain.history import recent
from hands import reasons
from memory import conversation, settings
from sound import earcon

TOOL = "tool"

# THE SAME CALL, SAID BEFORE IT RUNS.
STARTED = "tool.started"

MODEL = "model"

# WHAT ONE ROUND COST, SAID AS SOON AS THE MODEL COMES BACK AND BEFORE ANY TOOL
# IT ASKED FOR HAS RUN.
SPENT = "spent"

# WHAT OLLAMA TIMES ITSELF IN.
NANOSECONDS = 1_000_000_000

# THREE IN A ROW GETTING NOWHERE.
ENOUGH = 3

# HOW THE CALL LIMIT SAYS SO, IN ITS OWN WORDS: "Model call limits exceeded: run
# limit (14/14)". EVERY WORD OF A REPLY IS READ OUT LOUD, AND THAT IS A COUNTER.
LIMIT = "Model call limits exceeded"

NOWHERE = (
    "That is not getting anywhere — three goes in a row came back with nothing. "
    "Tell me a bit more about what you are after and I will try it another way."
)


# HOW MANY GOES ONE OF THOSE GETS BEFORE THE ROUND GIVES UP ON IT.
TRIES = 3



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

# WHETHER THE LAST read_file RESULT WAS CUT SHORT AND THE POSITION TO RESUME FROM. CLEARED
# EACH TURN BY fresh(), UPDATED BY keep_record() WHEN A read_file TOOL COMES BACK.
file_was_cut = False
file_cut_resume = None

# HOW MANY CHARACTERS OF THIS TURN'S WORDS A GUARD HAS TAKEN BACK. THE STREAM SHOWS AND
# SPEAKS A ROUND AS THE MODEL TYPES IT, WHICH IS WHAT MAKES HAPPY FEEL QUICK, AND A GUARD
# ONLY SEES THAT ROUND ONCE IT IS FINISHED — SO THE ANSWER IT TURNS BACK IS ALREADY ON THE
# SCREEN. ASKED ABOUT UNREAD MESSAGES, THE PANEL SHOWED "56 unread" OFF THE MORNING'S
# BACKCHAT, THEN THE TOOL, THEN "56 unread" AGAIN: THE FIRST ONE WAS THE GUESS THE GUARD
# EXISTS TO STOP, AND IT WAS RIGHT ONLY BY LUCK. THE STREAM READS THIS AND DROPS THAT MUCH.
withdrawn = 0

# WHETHER A GUARD IN THIS TURN HAS EVER TURNED A ROUND BACK.
corrected = False


def held(said):
    """WHETHER THIS TURN'S WORDS WAIT FOR THE GUARDS BEFORE THEY ARE DRAWN.

    UNDRAWING IS STILL A FLICKER: THE WORDS WERE ON THE SCREEN, AND THAT IS WHAT WAS SEEN.
    THE ONLY WAY NOT TO SHOW A WRONG ANSWER IS NOT TO DRAW IT, AND WHETHER A TURN IS THE KIND
    THAT GETS CORRECTED IS KNOWN FROM THE QUESTION BEFORE THE MODEL HAS SAID A WORD: A
    QUESTION ABOUT SOMETHING THAT MOVES IS ONE keep_fresh WILL HOLD IF NOTHING IS CALLED.

    THESE ARE THE TURNS THAT TYPE, GET CORRECTED AND TYPE AGAIN. THEY LOSE THE WORD-BY-WORD
    DRAW AND GAIN NEVER SHOWING AN ANSWER NOBODY STANDS BEHIND. EVERY OTHER TURN — WHICH IS
    NEARLY ALL OF THEM — DRAWS AS IT ALWAYS DID."""
    return corrected or asked_fresh((said or "").lower())


@wrap_model_call
def keep_opened(request, handler):
    """A BIG SERVICE'S TOOLS ARE NOT SHOWN UNTIL THE TURN HAS ASKED FOR THAT SERVICE.

    LINEAR HANDS OVER SEVENTY-THREE TOOLS AND GOOGLE SIXTEEN. FLAT, THAT IS EIGHTY-NINE
    SCHEMAS IN FRONT OF THE PREFIX CACHE ON EVERY TURN INCLUDING THE ONES ABOUT THE WEATHER,
    AND THE PREFIX CACHE IS THE WHOLE OF WHY AN ANSWER TAKES HALF A SECOND.

    SO THE GRAPH IS BUILT WITH EVERY TOOL — ANY OF THEM MUST BE ABLE TO RUN THE MOMENT IT IS
    ASKED FOR — AND WHAT THE MODEL IS *SHOWN* IS TRIMMED HERE: THE DOOR ALWAYS, AND WHAT IS
    BEHIND IT ONLY ONCE THIS TURN HAS OPENED IT. A TURN THAT NEVER MENTIONS LINEAR NEVER
    PAYS FOR LINEAR."""
    from mcps import opening

    shut = opening.hidden()

    if not shut:
        return handler(request)

    # A SENTENCE NAMING A SERVICE HAS ALREADY SAID WHICH ONE IT MEANS, SO ITS TOOLS ARE
    # THERE FROM THE FIRST ROUND AND NOTHING IS SPENT ASKING. THE DOOR IS FOR THE SENTENCES
    # THAT NAME NO SERVICE AT ALL.
    said = opening.carried(conversation.asking() or "")

    # AND THE DOORS THIS TURN WENT THROUGH ITSELF, OFF THE TOOLS IT HAS ACTUALLY CALLED.
    through = opening.opened(set(ran) | said)
    showing = [each for each in request.tools if each.name not in shut or each.name in through]

    return handler(request.override(tools=showing))


@wrap_model_call
def keep_thinking(request, handler):
    """A MODEL CALL MAY TAKE A WHILE, SO A SMALL PULSE KEEPS SILENCE FROM READING AS A HANG."""
    earcon.start()

    return handler(request)


class Stuck(Exception):
    """ENOUGH TOOLS IN A ROW SAID NO THAT THE NEXT ONE WOULD TOO."""


def fresh():
    """A NEW TURN. THE STREAK IS ABOUT THIS ERRAND, NOT THE LAST ONE."""
    global missed, spend, file_was_cut, file_cut_resume, withdrawn, corrected

    missed = 0
    spend = None
    file_was_cut = False
    file_cut_resume = None
    withdrawn = 0
    corrected = False
    repeats.forget()
    refused.clear()
    ran.clear()


# THE SAME QUESTION TWICE, AND THE SAME QUESTION REWORDED, WHICH IS brain/repeats.py WITH THE
# TWO DICTS IT KEEPS OF ITS OWN.
# A TOOL CALL THAT CAME BACK UNREADABLE, WHICH IS brain/malformed.py.
from brain.malformed import (  # noqa: E402
    AGAIN,
    SHOWN,
    UNPARSED,
    intended,
    minted,
    telling,
    unparsed,
    wanted,
)

from brain.repeats import (  # noqa: E402
    CHANGING,
    CIRCLING,
    ENOUGH_TRIES,
    MOSTLY_SAME,
    NOISE,
    REPEATED,
    SEARCHING,
    UNCHANGED,
    UNMOVED,
    alike,
    asked,
    circling,
    gist,
    learned,
    remember,
    repeated,
    signature,
    tried,
)


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


# THE VOCABULARY EVERY REPLY GUARD BELOW JUDGES BY, WHICH LIVES IN brain/words.py NOW: THREE
# HUNDRED LINES OF WORD LISTS THAT TOUCH NOTHING THIS FILE KEEPS. THEY ARE READ BACK IN HERE
# UNDER THEIR OWN NAMES BECAUSE brain/guarding.py AND bench/guarding.py BOTH REACH FOR THEM
# THROUGH THIS MODULE, AND A GUARD'S WORDING IS NOT WORTH A ROUND OF RENAMING TO MOVE.
from brain.words import (  # noqa: E402
    ANNOUNCED,
    ANNOUNCING,
    ASKED_AGAIN,
    ASKED_FRESH,
    ASKED_TOLD,
    BACKED,
    CARRY_ON,
    CLAIMS,
    COURTESIES,
    DENIED,
    DISCLAIMS,
    DISOWNED,
    DISOWNED_TOLD,
    DOINGS,
    FINISHED,
    GAVE_UP,
    GIVES_UP,
    HANDBACK,
    HANDED_BACK,
    LOOKERS,
    NOTHING_RAN,
    ON_SCREEN,
    OWNS,
    POINTED,
    READERS,
    TURNED_BACK,
    UNASKED_ALOUD,
    UNBACKED,
    UNLOOKED_ALOUD,
    UNREAD_ALOUD,
    asked_fresh,
    disowning,
    unbacked,
)

# AND WHETHER AN ANSWER IS THIS MOMENT'S OR AN OLD SITTING'S, WHICH IS brain/staleness.py.
from brain.staleness import (  # noqa: E402
    DOING,
    MOVING,
    SAME,
    about,
    instructing,
    moving,
    stale_answer,
    stale_moving,
    subjects,
)


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


def announced(words):
    """WHETHER THESE WORDS END ON WHAT IS ABOUT TO HAPPEN RATHER THAN WHAT DID.

    JUDGED ON THE LAST SENTENCE, NOT THE WHOLE REPLY. "THE SITE IS UP, LET ME PULL UP THE
    PROJECT" REPORTS A REAL THING AND THEN LEAVES THE JOB HANGING, AND IT IS THE HANGING HALF
    THAT THE PERSON IS LEFT WAITING ON. "I OPENED IT, LET ME KNOW IF YOU WANT MORE" ALSO SAYS
    BOTH AND IS FINISHED, BECAUSE WHAT IT ENDS ON IS THEIRS TO ANSWER AND NOT HAPPY'S TO DO."""
    last = ending(words)

    if not last:
        return False

    if any(each in last for each in COURTESIES):
        return False

    return any(each in last for each in ANNOUNCING) and not any(
        each in last for each in FINISHED
    )


def ending(words):
    """THE LAST REAL SENTENCE OF A REPLY, LOWERCASED, OR "" IF THERE IS NONE."""
    said = [each.strip() for each in re.split(r"[.!?\n]+", (words or "").lower())]
    said = [each for each in said if each]

    return said[-1] if said else ""


def announcing(answered):
    """WHETHER THIS ROUND ENDS THE TURN ON WHAT IT IS ABOUT TO DO RATHER THAN WHAT IT DID."""
    said = getattr(answered, "result", None) or answered

    if isinstance(said, list):
        said = said[-1] if said else None

    # STILL REACHING FOR A TOOL, SO IT IS MID-JOB AND MAY SAY WHATEVER IT LIKES.
    if getattr(said, "tool_calls", None):
        return False

    return announced((getattr(said, "text", "") or "").lower())


def handing_back(answered):
    """WHETHER THIS REPLY TELLS THEM TO GO AND CLICK SOMETHING THEY CANNOT SEE."""
    said = getattr(answered, "result", None) or answered

    if isinstance(said, list):
        said = said[-1] if said else None

    if getattr(said, "tool_calls", None):
        return False

    words = (getattr(said, "text", "") or "").lower()

    return bool(words.strip()) and any(each in words for each in HANDBACK)


@wrap_model_call
def keep_opening(request, handler):
    """A TURN MAY NOT END BY TELLING THEM WHICH LINK TO CLICK.

    THE RESULTS ARE NUMBERED FOR THE MODEL AND SHOWN TO NOBODY: THE PERSON HEARS THE ANSWER
    AND SEES NO LIST AT ALL. ASKED TO PULL UP ONE PROJECT'S PAGE, A TURN SEARCHED, FOUND IT,
    AND SAID "click the first link" — WHICH IS THE WHOLE JOB HANDED STRAIGHT BACK, ABOUT A
    LIST THAT DOES NOT EXIST ON THEIR SCREEN."""
    answered = handler(request)

    if not handing_back(answered):
        return answered

    told = request.override(messages=list(request.messages) + [HumanMessage(HANDED_BACK)])

    return handler(told)


@wrap_model_call
def keep_finishing(request, handler):
    """A TURN MAY NOT END ON WHAT IT IS ABOUT TO DO.

    ASKED TO OPEN ONE PROJECT'S PAGE, A TURN OPENED THE SITE'S FRONT PAGE, SAID "THE SITE IS
    UP, LET ME PULL UP THE PROJECT", AND STOPPED. THAT PAGE WAS NEVER OPENED. THE WORDS ARE THE TELL
    AND NOT THE FAULT: THE MODEL TOOK THE FIRST STEP FOR THE WHOLE JOB, AND THE ONE PLACE THAT
    IS CATCHABLE FOR EVERY TOOL AT ONCE IS THE ANSWER ON ITS WAY OUT.

    IT IS SENT BACK ONCE, WHICH IS ENOUGH: WHAT COMES BACK EITHER GOES AND DOES THE THING OR
    SAYS PLAINLY THAT IT DID NOT, AND BOTH OF THOSE ARE HONEST ENDINGS."""
    answered = handler(request)

    if not announcing(answered):
        return answered

    told = request.override(messages=list(request.messages) + [HumanMessage(ANNOUNCED)])

    return handler(told)


@wrap_model_call
def keep_looking(request, handler):
    """A TURN MAY NOT ANSWER A QUESTION ABOUT WHAT IS IN FRONT OF THEM OUT OF ITS OWN MEMORY.

    THE WRITING TOOLS HAVE HELD THIS LINE FOR A WHILE, AND THEY HOLD IT ONLY FOR THEMSELVES:
    THE CHECK LIVES IN write_document'S ARGUMENTS, SO A TURN THAT ENDS IN A PLAIN SENTENCE
    NEVER TOUCHES IT. ASKED "how many episodes does this show have", A TURN CALLED NOTHING,
    TOOK THE SHOW'S NAME OFF A current_activity RESULT FROM NINETY MINUTES EARLIER, AND SAID
    "ten" OFF THE WEIGHTS. EVERY PART OF THAT WAS WRONG AND NONE OF IT WAS CATCHABLE ANYWHERE
    BUT HERE, WHICH IS THE ONE PLACE A SPOKEN ANSWER PASSES THROUGH BEFORE IT IS SAID.

    IT IS SENT BACK ONCE. WHAT COMES BACK EITHER CALLS THE TOOLS IT WAS TOLD TO OR ANSWERS
    ANYWAY, AND A SECOND TURNING BACK WOULD ONLY SPEND ANOTHER ROUND ON THE SAME REPLY."""
    answered = handler(request)
    said = conversation.asking() or ""

    if not answering(answered):
        return answered

    pointed = any(each in said.lower() for each in POINTED)

    # THE QUESTION POINTS AT THE SCREEN, OR THE ANSWER DOES. "Oh yeah." POINTS AT NOTHING AND
    # MATCHED NOTHING HERE, AND THE REPLY WAS STILL "You're watching House of the Dragon" —
    # TAKEN OFF A current_activity RESULT FROM SEVEN HOURS EARLIER, WITH NO TOOL CALLED. WHAT
    # MAKES THAT A LIE IS THE CLAIM, NOT THE WORDING OF THE QUESTION, SO THE CLAIM IS READ TOO.
    if not pointed and not pointing(answered):
        return answered

    # LOOKING FIRST, THEN READING: THE TWO ARE ASKED FOR IN THE ORDER THEY HAVE TO HAPPEN, SO
    # A TURN THAT HAS LOOKED IS NOT SENT BACK TO LOOK AGAIN.
    if not already(*LOOKERS):
        # THE QUESTION IS QUOTED BACK WHEN THE QUESTION IS WHAT POINTED. WHEN IT WAS THE
        # ANSWER THAT POINTED, QUOTING "Oh yeah." AT THE MODEL EXPLAINS NOTHING.
        return again(request, handler, answered,
                     UNLOOKED_ALOUD.format(said=said) if pointed else UNASKED_ALOUD)

    # NOBODY ASKED ANYTHING, SO THE LOOKING IS THE WHOLE OF IT. NAMING WHAT IS IN FRONT OF THEM
    # IS EXACTLY WHAT current_activity ANSWERS, AND SENDING THAT OFF TO READ SOMETHING TOO SAYS
    # "go and search the web about this show" TO A TURN THAT WAS ONLY EVER SAYING HELLO BACK.
    if not pointed:
        return answered

    # A QUESTION THE SCREEN ITSELF ANSWERS IS DONE NOW. ANYTHING ELSE — A COUNT, A YEAR, A
    # RUNTIME — IS NOT ON THE SCREEN AND HAS TO BE READ UP BEFORE IT IS SAID.
    if not already(*READERS) and not any(each in said.lower() for each in ON_SCREEN):
        return again(request, handler, answered, UNREAD_ALOUD.format(said=said))

    return answered


@wrap_model_call
def keep_fresh(request, handler):
    """A QUESTION ABOUT SOMETHING THAT MOVES MAY NOT BE ANSWERED WITH NOTHING CALLED.

    THE OTHER HALF OF keep_looking, FOR THE THINGS THAT CHANGE WHERE NOBODY IS LOOKING: A
    MAILBOX, A CHAT, A CALENDAR. ASKED "are there any unread messages on whatsapp" AT TEN AND
    AGAIN AT THREE, THE MORNING'S ANSWER SITS IN THE BACKCHAT IN THE EXACT SHAPE A FRESH ONE
    HAS, AND IT WAS READ BACK OUT — TWICE, WITH NOT ONE TOOL CALLED EITHER TIME.

    keep_looking WILL NOT CATCH IT: THAT ONE ASKS WHETHER THE QUESTION POINTS AT THE SCREEN,
    AND A MAILBOX IS NOT THE SCREEN. SENT BACK ONCE, THE SAME AS EVERY OTHER GUARD HERE."""
    answered = handler(request)

    # A ROUND THAT ASKED FOR A TOOL IS ALREADY GOING TO LOOK, WHICH IS THE WHOLE POINT.
    if not answering(answered):
        return answered

    # SOMETHING RAN THIS TURN, SO THE ANSWER HAS A SOURCE THAT IS NOT MEMORY.
    if ran:
        return answered

    said = conversation.asking() or ""

    if not said:
        return answered

    # THE LIST ABOVE, OR THE BACKSTOP UNDER IT. A LIST OF PHRASINGS ALWAYS HAS HOLES, AND THE
    # HOLES ARE WHERE THIS FAILS: THE ONE THING THAT IS TRUE OF EVERY FAILURE, WHATEVER THE
    # WORDS, IS THAT THE ONLY MATERIAL FOR THE ANSWER CAME OUT OF A SITTING THAT IS OVER.
    if not asked_fresh(said.lower()) and not stale_answer(request.messages, said.lower()):
        return answered

    return again(request, handler, answered, ASKED_TOLD.format(said=said))


def again(request, handler, answered, telling):
    """THE ROUND RUN AGAIN WITH THE TELLING ON THE END OF IT, OR THE FIRST ANSWER BACK IF THAT
    CAME TO NOTHING.

    A SENT-BACK ROUND USUALLY GOES OFF TO CALL THE TOOL IT WAS TOLD TO, WHICH IS THE POINT. NOW
    AND THEN IT COMES BACK EMPTY, AND HANDING THAT UP THE CHAIN ENDS THE TURN ON THE "I got
    tangled up" FALLBACK — SILENCE, WHICH IS WORSE THAN THE ANSWER IT WAS BEING CORRECTED FOR.
    SO NOTHING IS ONLY EVER TRADED FOR SOMETHING."""
    global withdrawn, corrected

    # WHAT THE ROUND BEING TURNED BACK ALREADY PUT ON THE SCREEN. NOT NAMED taken: THAT IS
    # THE FUNCTION THE STREAM READS THIS BACK WITH, AND A LOCAL OF THAT NAME MAKES EVERY
    # MENTION OF IT IN HERE LOCAL TOO.
    shown = len(wording(answered))

    told = handler(request.override(messages=list(request.messages) + [HumanMessage(telling)]))
    said = getattr(told, "result", None) or told

    if isinstance(said, list):
        said = said[-1] if said else None

    if getattr(said, "tool_calls", None) or (getattr(said, "text", "") or "").strip():
        # THE ANSWER THAT WAS SHOWN IS NOT THE ANSWER ANY MORE, SO THE STREAM UNSAYS IT,
        # AND FROM HERE ON IT HOLDS EACH ROUND RATHER THAN DRAWING ANOTHER ONE TO UNDRAW.
        withdrawn += shown
        corrected = True

        return told

    return answered


def taken():
    """HOW MANY CHARACTERS A GUARD HAS JUST TAKEN BACK, AND ZERO EVERY TIME AFTER.

    READ ONCE BY THE STREAM AND CLEARED, SO ONE WITHDRAWAL IS UNSAID ONCE."""
    global withdrawn

    given, withdrawn = withdrawn, 0

    return given


def wording(answered):
    """THE WORDS IN A ROUND'S ANSWER, WHATEVER SHAPE IT CAME BACK IN.

    NOT text(): THAT NAME IS ALREADY TAKEN IN HERE, BY THE ONE THAT UNWRAPS A TOOL RESULT.
    DEFINING IT TWICE MEANT THE SECOND QUIETLY REPLACED THE FIRST AND EVERY TOOL IN THE
    SUITE STOPPED BEING READ."""
    said = getattr(answered, "result", None) or answered

    if isinstance(said, list):
        said = said[-1] if said else None

    return str(getattr(said, "text", "") or "")


# HOW A REPLY STATES, AS A FACT, WHAT IS IN FRONT OF THEM THIS MOMENT. THESE ARE CLAIMS ABOUT
# THE SCREEN AND NOTHING ELSE: A TURN THAT SAYS ONE OF THEM HAS EITHER JUST LOOKED, OR IS
# READING A TITLE OUT OF A CONVERSATION THAT HAS MOVED ON SINCE.
CLAIMED = ("you're watching", "youre watching", "you are watching",
           "you're listening to", "youre listening to", "you are listening to",
           "you're on", "youre on", "you are on",
           "you're reading", "youre reading", "you are reading",
           "currently watching", "currently playing", "currently open",
           "is playing right now", "is open right now", "on your screen right now")


def pointing(answered):
    """WHETHER THIS REPLY STATES WHAT IS IN FRONT OF THEM RIGHT NOW AS A FACT."""
    said = getattr(answered, "result", None) or answered

    if isinstance(said, list):
        said = said[-1] if said else None

    # str() FIRST: .text IS AN ACCESSOR OBJECT ON THESE MESSAGES, NOT A STRING, AND `in` AGAINST
    # IT SILENTLY MATCHES NOTHING.
    words = str(getattr(said, "text", "") or "").lower()

    return any(each in words for each in CLAIMED)


def answering(answered):
    """WHETHER THIS ROUND IS THE ANSWER ITSELF RATHER THAN A STEP ON THE WAY TO ONE.

    A ROUND THAT ASKED FOR A TOOL IS ABOUT TO GO AND LOOK, WHICH IS THE THING BEING ASKED FOR,
    AND TURNING IT BACK WOULD INTERRUPT THE VERY BEHAVIOUR THIS IS HERE TO GET."""
    said = getattr(answered, "result", None) or answered

    if isinstance(said, list):
        said = said[-1] if said else None

    if getattr(said, "tool_calls", None):
        return False

    return bool((getattr(said, "text", "") or "").strip())


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
    """A REPLY MAY NOT SAY A THING HAPPENED WHEN NO TOOL THIS TURN DID IT — BECAUSE THE ONE
    THAT WOULD HAVE SAID NO, OR BECAUSE NONE WAS EVER CALLED.

    THIS IS THE ONE PLACE IT CAN BE CAUGHT FOR EVERY TOOL AT ONCE. THE MODEL HAS ALREADY BEEN
    TOLD, IN THE TOOL'S OWN WORDS, THAT IT FAILED; WHAT THIS ADDS IS THAT IT CANNOT THEN GO ON
    TO SAY OTHERWISE. IT IS SENT BACK ONCE, WHICH IS ENOUGH — IT EITHER DOES THE THING OR SAYS
    IT DID NOT HAPPEN, AND BOTH OF THOSE ARE HONEST ANSWERS."""
    answered = handler(request)

    if not claiming(answered):
        return answered

    # A TURN THAT RAN NOTHING HAS NO REFUSAL TO POINT AT, WHICH IS WHY THIS WAS MISSED: THE
    # CLAIM IS THE WHOLE OF THE EVIDENCE, AND IT IS ENOUGH.
    if not ran:
        told = request.override(messages=list(request.messages) + [HumanMessage(NOTHING_RAN)])

        return handler(told)

    # AND THE HALF-WAY CASE: SOMETHING RAN, BUT NOTHING THAT COULD HAVE DONE WHAT WAS CLAIMED.
    missing = unbacked(claimed(answered), ran)

    if missing:
        told = request.override(messages=list(request.messages) + [HumanMessage(
            UNBACKED.format(claim=" and ".join(missing), ran=", ".join(dict.fromkeys(ran)))
        )])

        return handler(told)

    if not refused:
        return answered

    told = request.override(
        messages=list(request.messages) + [HumanMessage(DENIED.format(undone="\n".join(unfinished())))]
    )

    return handler(told)


def claimed(answered):
    """THE WORDS OF A REPLY, LOWERCASED, FOR THE CHECKS THAT READ THEM."""
    said = getattr(answered, "result", None) or answered

    if isinstance(said, list):
        said = said[-1] if said else None

    return (getattr(said, "text", "") or "").lower()


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
    """A TOOL CALL THE BACKEND COULD NOT READ IS MENDED WHERE THERE IS ONLY ONE WAY TO READ
    IT, AND OTHERWISE NAMED AS A MISTAKE. NEITHER IS THE END OF A TURN."""
    for left in range(TRIES - 1, -1, -1):
        try:
            return handler(request)
        except Exception as error:
            said = str(error)

            if not unparsed(said):
                raise

            amiss(said)

            meant = intended(said, request.tools)

            # PUNCTUATION IS NOT WORTH A WHOLE ROUND: A CALL THAT COULD ONLY HAVE MEANT ONE
            # THING IS MADE AS THAT THING.
            if meant:
                name, args = meant
                amiss(f"{name} mended and run as {json.dumps(args)}")

                return AIMessage(
                    content="",
                    tool_calls=[{"name": name, "args": args, "id": minted(), "type": "tool_call"}],
                )

            if not left:
                raise

            # THE MODEL'S BAD ANSWER NEVER MADE IT ONTO THE CONVERSATION, SO THE
            # CORRECTION GOES ON AS THE NEXT THING SAID TO IT.
            request = request.override(
                messages=list(request.messages) + [HumanMessage(telling(said))]
            )

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

    return {"read": usage.get("input_tokens", 0), "wrote": usage.get("output_tokens", 0),
            "prefill": prefill(said)}


def prefill(said):
    """HOW LONG THE BACKEND SPENT RE-READING THE PROMPT, IN SECONDS.

    A PREFIX IT ALREADY HOLDS COSTS ALMOST NOTHING; ONE IT HAS TO READ AGAIN COSTS THE WHOLE
    CONTEXT AT A FEW HUNDRED TOKENS A SECOND. THE GAP BETWEEN THOSE TWO IS MOST OF A SLOW
    TURN, AND NOTHING ELSE ON THE SPENT LINE SHOWS IT."""
    taken = (getattr(said, "response_metadata", None) or {}).get("prompt_eval_duration")

    return None if taken is None else taken / NANOSECONDS


def claim():
    """THE ROUND'S COST, ONCE."""
    global spend

    taken, spend = spend, None

    return taken


@wrap_tool_call
def keep_record(request, handler):
    """EVERY TOOL CALL GOES ON ITS EXCHANGE, WITH ITS REASON, ARGUMENTS AND TIME."""
    earcon.start()
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
    refusal = repeated(name, args) or circling(name, args) or sourcing.checked(name, args)

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

    # TRACK WHETHER read_file LEFT TEXT UNREAD, SO THE MODEL CANNOT ANSWER WITHOUT GETTING IT.
    if name == "read_file":
        check_file_cut(said)

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


def check_file_cut(said):
    """WHETHER THIS read_file RESULT WAS CUT SHORT AND WHAT THE NEXT start= IS."""
    global file_was_cut, file_cut_resume

    # THE CUT MARKER SAYS "[...cut. Call this again with start={next} to read on..."
    # SO IF SAID ENDS WITH IT, EXTRACT THAT next VALUE.
    if "[...cut" not in said or "start=" not in said:
        file_was_cut = False
        file_cut_resume = None
        return

    # EXTRACT THE start= VALUE FROM THE CUT MARKER.
    match = re.search(r"start=(\d+)", said)

    if match:
        file_was_cut = True
        file_cut_resume = int(match.group(1))
    else:
        file_was_cut = False
        file_cut_resume = None


UNREAD_FILE = (
    "That file was cut short. You read only part of it. Call read_file again with the exact "
    "start={start} it named, and keep reading until nothing is cut, before you answer or "
    "summarise — a summary made from only the first chunk is not a summary of the whole file."
)


@wrap_model_call
def keep_reading(request, handler):
    """A TURN MAY NOT ANSWER ABOUT A FILE WITHOUT READING ALL OF IT.

    read_file RETURNS TEXT IN CHUNKS FOR LONG FILES AND SAYS IN THE RETURNED TEXT ITSELF
    EXACTLY WHAT TO CALL IT WITH TO GET THE NEXT CHUNK. THE MODEL OFTEN READS ONE CHUNK
    AND ANSWERS OUT OF THAT ALONE, IGNORING THE INSTRUCTION. STOPPING HERE CATCHES THAT:
    IF THE LAST read_file WAS CUT SHORT AND THE MODEL'S ANSWER DID NOT CALL IT AGAIN,
    THE ANSWER IS SENT BACK WITH AN INSTRUCTION TO FINISH READING FIRST.

    IT IS SENT BACK ONCE. WHAT COMES BACK EITHER CALLS read_file OR ANSWERS ANYWAY, AND A
    SECOND TURNING BACK WOULD ONLY SPEND ANOTHER ROUND ON THE SAME REPLY."""
    answered = handler(request)

    # ONLY CHECK FINAL ANSWERS, NOT ROUNDS ASKING FOR ANOTHER TOOL.
    if not answering(answered):
        return answered

    # IF NO FILE WAS CUT, OR IF IT WAS BUT WAS ALREADY FOLLOWED UP, NOTHING TO CORRECT.
    if not file_was_cut or file_cut_resume is None:
        return answered

    # IF THE ANSWER ASKED FOR ANOTHER TOOL, LET IT GO — THE TOOL MIGHT BE read_file.
    # A SECOND CHECK WOULD ONLY INTERRUPT THE CORRECTION.
    return again(request, handler, answered,
                 UNREAD_FILE.format(start=file_cut_resume))