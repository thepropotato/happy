"""
THE MODEL, AND WHAT IT IS TOLD BEFORE IT HEARS ANYTHING.

A MODEL IS INFERENCE AND NOTHING MORE HERE. THE FLOW IS LANGGRAPH'S, THE TOOLS
ARE agents/'S, AND WHAT IS LEFT IS A NAME, AN ADDRESS AND A HANDFUL OF SETTINGS.
THEY ARE ALL AT THE TOP OF THIS FILE AND providers.py TURNS THEM INTO WHICHEVER
BACKEND IS ASKED FOR, SO CHANGING PROVIDER IS CHANGING PROVIDER BELOW AND
NOTHING ELSE ANYWHERE.

THE MODELS ARE THE ONES YOU PULLED. NO TAG BUILT ON THE SIDE, NO COPY OF THE
WEIGHTS UNDER ANOTHER NAME: THE CONTEXT LENGTH GOES WITH EVERY REQUEST, WHICH IS
ONE FEWER SETUP STEP TO FORGET AND ONE FEWER THING THAT IS TRUE ONLY ON THE
MACHINE IT WAS BUILT ON.

THE PROMPT LIVES HERE TOO, BECAUSE WHAT THE MODEL IS AND WHAT IT IS TOLD ARE
CHANGED TOGETHER FAR MORE OFTEN THAN EITHER IS CHANGED ALONE.
"""

import os

import providers
from agents import system as machine  # ALIASED, system IS ALREADY A ROLE NAME HERE.

# THE SWAP, IN TWO LINES. ANY BACKEND IN providers.py, AND None FOR THE URL
# TAKES THAT BACKEND'S OWN DEFAULT ADDRESS.
PROVIDER = providers.OLLAMA
URL = None

MODEL = "gpt-oss:20b"

# THE WHOLE WINDOW THE MODEL SUPPORTS, SENT WITH EVERY REQUEST. OLLAMA HANDS OUT
# 4096 UNLESS ASKED OTHERWISE AND FAILS BY QUIETLY FORGETTING THE OLDEST THING IN
# THE CONVERSATION RATHER THAN BY COMPLAINING. ONE READ FILE IS BIGGER THAN 4096
# ON ITS OWN, SO THIS IS NOT A LUXURY.
#
# MEASURED ON AN M SERIES WITH 26 GB: IT LOADS AT 12 GB, STAYS ENTIRELY ON THE
# GPU, AND REPLIES IN 2.18s AGAINST 2.22s AT 4096. IT COSTS NOTHING BECAUSE
# GPT-OSS USES SLIDING WINDOW ATTENTION ON ALTERNATE LAYERS, WHICH KEEPS THE KEY
# VALUE CACHE SMALL. CONFIRM WITH `ollama ps`: THE CONTEXT COLUMN IS THE ONLY
# HONEST ANSWER IN THIS STACK.
CONTEXT = 131072

# THE MODEL THAT CAN SEE. A SECOND ONE, BECAUSE THE TALKING MODEL IS TEXT ONLY.
# IT IS ASKED FOR ONLY WHEN A SCREEN TOOL IS CALLED, AND THE TWO OF THEM DO NOT
# FIT IN MEMORY AT ONCE ON A LAPTOP, SO THE SERVER WILL SWAP ONE OUT FOR THE
# OTHER. THAT COSTS SECONDS ON THE FIRST LOOK AND IS WHY LOOKING IS A LAST
# RESORT RATHER THAN THE FIRST THING TRIED.
VISION_MODEL = "qwen3-vl"

# SMALLER THAN THE TALKING MODEL'S AND STILL FAR ABOVE THE DEFAULT. A SCREENSHOT
# SCALED FOR THE MODEL IS ROUGHLY TWO THOUSAND TOKENS, WHICH LEAVES ALMOST
# NOTHING FOR THE QUESTION AT 4096. IT IS A CEILING RATHER THAN A RESERVATION,
# SO ROOM THAT GOES UNUSED COSTS NOTHING.
VISION_CONTEXT = 32768

# NOTHING TO INVENT WHEN THE ANSWER IS A NUMBER OR A PLACE ON A SCREEN.
VISION_TEMPERATURE = 0

# THINKING OFF, NOT TURNED DOWN. QWEN3-VL THINKS BEFORE IT ANSWERS, AND WHEN THE
# WINDOW IS SHORT IT SPENDS EVERY REMAINING TOKEN DOING IT, GETS CUT OFF AT
# finish_reason "length" AND RETURNS AN EMPTY STRING: NOT AN ERROR, NOT A BAD
# ANSWER, NOTHING AT ALL, AFTER NINETY SECONDS. NEITHER reasoning_effort NOR
# "/no_think" REACHED IT THROUGH THE OPENAI SHAPE, BECAUSE THAT REQUEST HAS
# NOWHERE TO PUT IT. THE NATIVE ONE HAS A FIELD, AND THIS IS IT.
VISION_EFFORT = False

# HOW HARD TO THINK BEFORE ANSWERING: low / medium / high, OR None FOR WHATEVER
# THE MODEL DOES ON ITS OWN. LOW KEEPS ANSWERS CONVERSATIONAL, WHICH IS WHAT
# SPEECH WANTS. A BACKEND THAT DOES NOT KNOW THE SETTING IGNORES IT.
EFFORT = "low"

# NAME OF THE ENVIRONMENT VARIABLE HOLDING THE KEY. NOT NEEDED WHEN THE URL IS
# LOCAL, BUT SOME CLIENTS REFUSE TO START WITHOUT SOMETHING IN THE SLOT.
API_KEY_ENV = "LLM_API_KEY"
NO_KEY = "local"

TEMPERATURE = 0.7

# LONG ENOUGH TO LOAD, NOT LONG ENOUGH TO HANG. MEASURED HERE: 74 SECONDS TO
# BRING GPT-OSS IN COLD AND ONE SECOND TO ANSWER ONCE IT IS THERE. THE TWO
# MODELS DO NOT FIT AT ONCE ON A LAPTOP, SO THE FIRST QUESTION AFTER A LOOK AT
# THE SCREEN PAYS FOR AN EVICTION AND A LOAD TOGETHER, AND 120 WAS NOT ENOUGH
# FOR THAT: IT FAILED AS A READ TIMEOUT, WHICH READS LIKE A DEAD SERVER AND IS
# NOT ONE. THIS CEILING IS HERE FOR A SERVER THAT WILL NEVER ANSWER.
TIMEOUT_SECONDS = 300

SYSTEM_PROMPT = (
    "You are Happy, a voice assistant with hands on this computer. You are being "
    "listened to, not read, so answer in one or two spoken sentences. No markdown, "
    "no lists, no code blocks, no emoji. Say numbers the way a person would say "
    "them out loud. If you do not know something, say so plainly.\n\n"
    "When you are asked to do something, do it with your tools rather than "
    "explaining how it would be done. Do not read a command or a file path out "
    "loud unless you are asked to. Say what happened, not how. If a tool tells "
    "you something failed, say that plainly instead of guessing at a reason.\n\n"
    "Use what this computer already does rather than working around it. Anything "
    "that is a web address, a site, a video or a search opens with open_url, which "
    "uses the browser this person already has open and is already signed in to. "
    "Never open a browser application and type into it, and never start a browser "
    "errand for something an address on its own would answer."
)

# WHAT THE MODEL CANNOT GUESS: WHOSE COMPUTER IT IS ANSWERING ABOUT. WITHOUT THIS
# IT INVENTS APPS, OR DENIES ONES THAT ARE SITTING RIGHT THERE.
MACHINE_PROMPT = (
    "Here is what is on the computer you are working on. Treat it as the whole "
    "truth: if an app is not on this list, it is not installed."
)

WARM_UP = "hi"

NOT_FOUND = "not found"


class LLMError(Exception):
    pass


def create(
    model=None,
    provider=None,
    url=None,
    key=None,
    temperature=TEMPERATURE,
    context=None,
    effort=EFFORT,
):
    """THE MODEL, READY TO BE HANDED TOOLS."""
    try:
        return providers.build(
            provider or PROVIDER,
            model or MODEL,
            url=url or URL,
            key=key or credential(),
            temperature=temperature,
            context=CONTEXT if context is None else context,
            effort=effort,
            timeout=TIMEOUT_SECONDS,
        )
    except providers.ProviderError as error:  # ONE ERROR TYPE LEAVES THIS MODULE.
        raise LLMError(str(error))


def eyes(model=None):
    """THE MODEL THAT LOOKS AT PICTURES. SAME BACKEND, SAME SETTINGS SHAPE, AND
    THE ONLY DIFFERENCE THAT MATTERS IS THAT IT WILL ACCEPT AN IMAGE."""
    return create(
        model=model or VISION_MODEL,
        temperature=VISION_TEMPERATURE,
        context=VISION_CONTEXT,
        effort=VISION_EFFORT,  # NOTHING TO REASON ABOUT. IT IS ASKED WHAT IT SEES.
    )


def credential():
    return os.environ.get(API_KEY_ENV) or NO_KEY


def url():
    """WHERE THE MODEL ACTUALLY IS, ONCE THE DEFAULTS ARE FILLED IN."""
    return providers.address(PROVIDER, URL)


def caveat():
    """WHAT THIS BACKEND CANNOT DO, WORTH SAYING AT STARTUP, OR None."""
    return providers.caveat(PROVIDER, MODEL)


def obtain(model=None):
    """HOW TO GET A MODEL THAT IS NOT THERE, IN THIS BACKEND'S OWN TERMS. FOR
    ANYONE WHO HAS TO PUT IT IN A SENTENCE, WHICH IS WHY IT IS NOT A pull."""
    return providers.install(PROVIDER, model or MODEL, URL)


def warm(model):
    """LOAD THE WEIGHTS NOW SO THE FIRST REAL QUESTION DOES NOT PAY FOR IT."""
    try:
        model.invoke(WARM_UP)
    except Exception as error:
        raise LLMError(complaint(error))


def complaint(error):
    """SAY WHICH OF THE TWO LIKELY THINGS WENT WRONG, AND HOW TO FIX THAT ONE."""
    said = reason(error)

    if NOT_FOUND in said.lower():  # THE SERVER IS UP, IT DOES NOT HAVE THE MODEL.
        return f"{MODEL} IS NOT THERE. GET IT WITH:\n  {obtain()}"

    return f"COULD NOT REACH {MODEL} AT {url()}. IS IT RUNNING? ({said})"


def reason(error):
    """THE SHORTEST TRUE THING TO PRINT ABOUT A FAILURE."""
    text = str(error).strip().splitlines()

    return text[0][:200] if text else error.__class__.__name__


def system_prompt():
    """THE STANDING PROMPT PLUS THE FACTS ONLY THIS MACHINE CAN SUPPLY."""
    apps = machine.listing()

    if not apps:  # AN UNKNOWN PLATFORM, OR NOTHING FOUND. HAPPY STILL WORKS.
        return SYSTEM_PROMPT

    return f"{SYSTEM_PROMPT}\n\n{MACHINE_PROMPT}\n\n{apps}"
