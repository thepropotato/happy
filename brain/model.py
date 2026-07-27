"""WHICH MODEL, AT WHICH ADDRESS, WITH WHICH SETTINGS.

A MODEL IS INFERENCE AND NOTHING MORE HERE. CHANGING PROVIDER IS CHANGING THE
TWO LINES BELOW AND NOTHING ELSE ANYWHERE.
"""

import os

from brain import providers

PROVIDER = providers.OLLAMA
URL = None

MODEL = "gpt-oss:20b"

# THE WHOLE WINDOW THE MODEL SUPPORTS, SENT WITH EVERY REQUEST. OLLAMA HANDS OUT
# 4096 UNLESS ASKED AND THEN FORGETS THE OLDEST THING WITHOUT COMPLAINING. ONE
# READ FILE IS BIGGER THAN 4096 ON ITS OWN. CONFIRM WITH `ollama ps`.
CONTEXT = 131072

# THE MODEL THAT CAN SEE. THE TALKING MODEL IS TEXT ONLY, AND THE TWO DO NOT FIT
# IN MEMORY AT ONCE ON A LAPTOP, SO LOOKING COSTS AN EVICTION AND A LOAD.
VISION_MODEL = "qwen3-vl"
VISION_CONTEXT = 32768
VISION_TEMPERATURE = 0

# THINKING OFF, NOT TURNED DOWN. QWEN3-VL SPENDS A SHORT WINDOW THINKING, GETS
# CUT OFF AT finish_reason "length" AND RETURNS AN EMPTY STRING.
VISION_EFFORT = False

# HOW HARD TO THINK BEFORE ANSWERING: low / medium / high, OR None. LOW KEEPS
# ANSWERS CONVERSATIONAL, WHICH IS WHAT SPEECH WANTS.
EFFORT = "low"

API_KEY_ENV = "LLM_API_KEY"
NO_KEY = "local"

TEMPERATURE = 0.7

# LONG ENOUGH TO LOAD, NOT LONG ENOUGH TO HANG. A COLD LOAD PLUS AN EVICTION IS
# MORE THAN 120 SECONDS, AND THAT FAILS AS A READ TIMEOUT, WHICH READS LIKE A
# DEAD SERVER AND IS NOT ONE.
TIMEOUT_SECONDS = 300

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


def sight(model=None):
    """THE MODEL THAT LOOKS AT PICTURES. SAME BACKEND, SAME SETTINGS SHAPE."""
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
    """HOW TO GET A MODEL THAT IS NOT THERE, IN THIS BACKEND'S OWN TERMS."""
    return providers.install(PROVIDER, model or MODEL, URL)


def warm(model):
    """LOAD THE WEIGHTS NOW SO THE FIRST REAL QUESTION DOES NOT PAY FOR IT."""
    try:
        model.invoke(WARM_UP)
    except Exception as error:
        raise LLMError(complaint(error))


def complaint(error):
    """WHICH OF THE TWO LIKELY THINGS WENT WRONG, AND HOW TO FIX THAT ONE."""
    said = reason(error)

    if NOT_FOUND in said.lower():  # THE SERVER IS UP, IT DOES NOT HAVE THE MODEL.
        return f"{MODEL} IS NOT THERE. GET IT WITH:\n  {obtain()}"

    return f"COULD NOT REACH {MODEL} AT {url()}. IS IT RUNNING? ({said})"


def reason(error):
    """THE SHORTEST TRUE THING TO PRINT ABOUT A FAILURE."""
    text = str(error).strip().splitlines()

    return text[0][:200] if text else error.__class__.__name__
