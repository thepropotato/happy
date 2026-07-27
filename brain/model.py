"""WHICH MODEL, AT WHICH ADDRESS, WITH WHICH SETTINGS.

A MODEL IS INFERENCE AND NOTHING MORE HERE. WHICH ONE AND WHERE COMES OUT OF THE
SETTINGS TABLE, SO CHANGING PROVIDER IS CHANGING A CONTROL AND NOT A LINE.
"""

import os

from brain import providers
from memory import settings

API_KEY_ENV = "LLM_API_KEY"
NO_KEY = "local"

# NOTHING TO REASON ABOUT AND NOTHING TO INVENT. IT IS ASKED WHAT IT SEES.
VISION_TEMPERATURE = 0

# THINKING OFF, NOT TURNED DOWN. A MODEL THAT SPENDS ITS WINDOW THINKING GETS CUT
# OFF AT finish_reason "length" AND RETURNS AN EMPTY STRING.
OFF = "off"

WARM_UP = "hi"

NOT_FOUND = "not found"


class LLMError(Exception):
    pass


def create(model=None, provider=None, url=None, key=None, temperature=None, context=None, effort=None):
    """THE MODEL, READY TO BE HANDED TOOLS."""
    try:
        return providers.build(
            provider or backend(),
            model or name(),
            url=url or wanted(),
            key=key or credential(),
            temperature=pick(temperature, "brain.temperature"),
            context=pick(context, "brain.context"),
            effort=effort if effort is not None else thinking("brain.effort"),
            timeout=settings.get("brain.timeout"),
        )
    except providers.ProviderError as error:  # ONE ERROR TYPE LEAVES THIS MODULE.
        raise LLMError(str(error))


def sight(model=None):
    """THE MODEL THAT LOOKS AT PICTURES. SAME BACKEND, SAME SETTINGS SHAPE."""
    return create(
        model=model or looking(),
        temperature=VISION_TEMPERATURE,
        context=settings.get("eyes.context"),
        effort=thinking("eyes.effort"),
    )


def pick(given, key):
    return settings.get(key) if given is None else given


def thinking(key):
    """A LEVEL, OR False FOR OFF. None WOULD LEAVE THE MODEL TO ITS OWN HABITS."""
    chosen = settings.get(key)

    return False if chosen in (OFF, "", None) else chosen


def name():
    return settings.get("brain.model")


def looking():
    return settings.get("eyes.model")


def backend():
    return settings.get("brain.provider")


def wanted():
    """THE ADDRESS ASKED FOR, OR None TO LET THE BACKEND USE ITS OWN."""
    return settings.get("brain.url") or None


def credential():
    return os.environ.get(API_KEY_ENV) or NO_KEY


def url():
    """WHERE THE MODEL ACTUALLY IS, ONCE THE DEFAULTS ARE FILLED IN."""
    return providers.address(backend(), wanted())


def caveat():
    """WHAT THIS BACKEND CANNOT DO, WORTH SAYING AT STARTUP, OR None."""
    return providers.caveat(backend(), name())


def obtain(model=None):
    """HOW TO GET A MODEL THAT IS NOT THERE, IN THIS BACKEND'S OWN TERMS."""
    return providers.install(backend(), model or name(), wanted())


def offered():
    """EVERY MODEL THIS BACKEND ALREADY HAS, FOR SOMETHING DRAWING A LIST."""
    return providers.offered(backend(), wanted())


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
        return f"{name()} IS NOT THERE. GET IT WITH:\n  {obtain()}"

    return f"COULD NOT REACH {name()} AT {url()}. IS IT RUNNING? ({said})"


def reason(error):
    """THE SHORTEST TRUE THING TO PRINT ABOUT A FAILURE."""
    text = str(error).strip().splitlines()

    return text[0][:200] if text else error.__class__.__name__
