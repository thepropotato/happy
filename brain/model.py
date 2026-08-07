"""WHICH MODEL, AT WHICH ADDRESS, WITH WHICH SETTINGS.

A MODEL IS INFERENCE AND NOTHING MORE HERE. WHICH ONE AND WHERE COMES OUT OF THE
SETTINGS TABLE, SO CHANGING PROVIDER IS CHANGING A CONTROL AND NOT A LINE.
"""

import os

from langchain_core.messages import HumanMessage, SystemMessage

from brain import providers
from memory import settings

API_KEY_ENV = "LLM_API_KEY"
NO_KEY = "local"

VISION_TEMPERATURE = 0

# WHAT OLLAMA CALLS "DO NOT UNLOAD THIS", AND WHAT 0 MINUTES MEANS HERE.
FOREVER = -1

# WHAT THE EYES ASK FOR INSTEAD: WHATEVER THE BACKEND DOES ON ITS OWN. THE
# SETTING IS ABOUT THE MODEL WHOSE PROMPT IS READ ON EVERY SINGLE REQUEST, AND
# HOLDING A SECOND BIG ONE BESIDE IT FOR GOOD IS HOW A MACHINE RUNS OUT OF MEMORY.
BACKEND = "backend"

# OFF, NOT LOW: A MODEL THAT THINKS ITS WHOLE WINDOW RETURNS AN EMPTY STRING.
OFF = "off"

WARM_UP = "hi"

NOT_FOUND = "not found"


class LLMError(Exception):
    pass


def create(model=None, provider=None, url=None, key=None, temperature=None, context=None,
           effort=None, resident=None):
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
            resident=None if resident == BACKEND else residency(),
        )
    except providers.ProviderError as error:
        raise LLMError(str(error))


def sight(model=None):
    """THE MODEL THAT LOOKS AT PICTURES. SAME BACKEND, SAME SETTINGS SHAPE."""
    return create(
        model=model or looking(),
        temperature=VISION_TEMPERATURE,
        context=settings.get("eyes.context"),
        effort=thinking("eyes.effort"),
        resident=BACKEND,
    )


def pick(given, key):
    return settings.get(key) if given is None else given


def thinking(key):
    """A LEVEL, OR False FOR OFF. None WOULD LEAVE THE MODEL TO ITS OWN HABITS."""
    chosen = settings.get(key)

    return False if chosen in (OFF, "", None) else chosen


def residency():
    """HOW LONG THE BACKEND SHOULD HOLD THE MODEL AFTER AN ANSWER, IN ITS TERMS.

    THE WEIGHTS ARE THE HALF OF THIS THAT SHOWS. THE OTHER HALF IS WHAT THE SERVER
    WORKED OUT ABOUT THE STANDING PROMPT AND THE TOOL LIST, WHICH GOES WHEN THE
    MODEL DOES — SO A DEFAULT THAT LETS GO AFTER FIVE QUIET MINUTES MAKES EVERY
    QUESTION ASKED AFTER A COFFEE PAY FOR ALL OF IT AGAIN.
    """
    minutes = settings.get("brain.resident")

    return FOREVER if not minutes else f"{minutes:g}m"


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


def warm(model, prompt=None, tools=None):
    """LOAD THE WEIGHTS NOW SO THE FIRST REAL QUESTION DOES NOT PAY FOR IT.

    AND THE STANDING PROMPT AND THE TOOL LIST WITH THEM, WHICH IS THE LARGER HALF
    OF THE WAIT. THEY ARE THE SAME TENS OF THOUSANDS OF TOKENS AT THE FRONT OF
    EVERY SINGLE REQUEST, SO A SERVER THAT READS THEM ONCE HERE HAS THEM READY
    FOR EVERY QUESTION AFTER — AND IT READS THEM WHILE HAPPY IS STARTING UP
    RATHER THAN WHILE SOMEBODY IS STOOD THERE WAITING FOR AN ANSWER.

    THE REPLY IS THROWN AWAY. IT IS THE READING THAT WAS WANTED, NOT THE ANSWER.
    """
    try:
        ready(model, tools).invoke(opening(prompt))
    except Exception as error:
        raise LLMError(complaint(error))


def ready(model, tools):
    """THE MODEL AS THE GRAPH WILL ACTUALLY CALL IT. THE TOOLS ARE MOST OF WHAT
    IS BEING WARMED, SO WARMING WITHOUT THEM WARMS THE WRONG PROMPT."""
    return model.bind_tools(tools) if tools else model


def opening(prompt):
    """THE SHORTEST REAL REQUEST: THE STANDING PROMPT, THEN A HELLO."""
    if not prompt:
        return WARM_UP

    return [SystemMessage(prompt), HumanMessage(WARM_UP)]


def complaint(error):
    """WHICH OF THE TWO LIKELY THINGS WENT WRONG, AND HOW TO FIX THAT ONE."""
    said = reason(error)

    if NOT_FOUND in said.lower():
        return f"{name()} IS NOT THERE. GET IT WITH:\n  {obtain()}"

    return f"COULD NOT REACH {name()} AT {url()}. IS IT RUNNING? ({said})"


def reason(error):
    """THE SHORTEST TRUE THING TO PRINT ABOUT A FAILURE."""
    text = str(error).strip().splitlines()

    return text[0][:200] if text else error.__class__.__name__
