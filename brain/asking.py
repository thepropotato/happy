"""THE ONE PLACE A SIGNATURE IS ASKED, POINTED AT THE SAME MODELS AS EVERYTHING ELSE.

DSPy KEEPS ITS OWN NOTION OF WHICH MODEL IT IS TALKING TO, SET GLOBALLY. HAPPY ALREADY HAS
ONE OF THOSE IN settings, AND TWO ANSWERS TO "WHICH MODEL" IS ONE MORE THAN ANY CODEBASE
SHOULD HAVE, SO THE SETTINGS ARE READ AND DSPy IS TOLD. IT IS TOLD AGAIN WHENEVER THEY MOVE."""

import threading

import dspy

from memory import settings

# DSPy NAMES A MODEL PROVIDER-FIRST, THE WAY LITELLM DOES.
NAMING = {"ollama": "ollama_chat", "openai": "openai"}

THINKING = "brain"

LOOKING = "eyes"

# HOW LONG AN ANSWER MAY RUN, WHICH IS NOT THE CONTEXT WINDOW: A THINKING SIGNATURE WANTS A
# WORD OR A NUMBER, AND HANDING THE WHOLE WINDOW OVER AS A BUDGET LETS A REASONING MODEL
# SPEND MINUTES ON "SHOW OR READ". THE LOOKING MODEL GETS MORE, BECAUSE A DESCRIPTION OF A
# SCREEN IS A SENTENCE AND 512 CUTS IT OFF PART-WAY.
ROOM = {THINKING: 512, LOOKING: 2048}

# WHAT THE LOOKING MODEL IS ASKED AT, WHICH IS NOT WHAT THE THINKING MODEL IS ASKED AT: A
# DESCRIPTION OF A SCREEN IS A READING AND NEVER AN INVENTION.
VISION_TEMPERATURE = 0

# WHAT WAS LAST BUILT FOR EACH KIND OF MODEL, SO A SETTING THAT HAS NOT MOVED REBUILDS
# NOTHING. THE THINKING MODEL AND THE LOOKING MODEL ARE SEPARATE SETTINGS AND MAY BE
# SEPARATE MODELS, SO THEY ARE HELD APART HERE TOO.
built = {}

lock = threading.Lock()

# WHY THE LAST SIGNATURE COULD NOT BE ANSWERED, FOR A CALLER THAT NEEDS THE DIFFERENCE
# BETWEEN A MODEL THAT IS NOT INSTALLED AND ONE THAT SIMPLY SAID NOTHING.
trouble = None




def guarded(kind):
    """THE MODEL CLASS ONE KIND IS BUILT FROM: THE THINKING ONE CARRIES THE GUARDS.

    A LOOKING MODEL ANSWERS ONE QUESTION ABOUT ONE PICTURE AND CALLS NOTHING, SO THERE IS NO
    TURN FOR A GUARD TO HOLD; THE THINKING ONE RUNS THE ERRAND AND NEEDS EVERY ONE OF THEM."""
    from brain.guarding import Guarded  # LATE: guarding READS wrapping, WHICH READS memory.

    return Guarded if kind == THINKING else dspy.LM


def facts(kind):
    """THE SETTINGS ONE KIND OF MODEL IS BUILT OUT OF."""
    if kind == LOOKING:
        # THE LOOKING MODEL IS ITS OWN MODEL AND ITS OWN EFFORT, ON THE SAME BACKEND.
        return (
            settings.get("brain.provider"),
            settings.get("eyes.model"),
            settings.get("brain.url"),
            VISION_TEMPERATURE,
            settings.get("eyes.effort"),
        )

    return (
        settings.get("brain.provider"),
        settings.get("brain.model"),
        settings.get("brain.url"),
        settings.get("brain.temperature"),
        settings.get("brain.effort"),
    )


def ready(kind=THINKING):
    """THE MODEL THE SETTINGS NAME, BUILT ONCE AND AGAIN WHENEVER THEY MOVE."""
    now = facts(kind)
    held = built.get(kind)

    if held and held[0] == now:
        return held[1]

    with lock:
        held = built.get(kind)

        if held and held[0] == now:
            return held[1]

        provider, model, url, temperature, effort = now

        # EFFORT IS SENT ONLY WHEN IT IS SET, AND NAMED THE WAY THE BACKEND WANTS IT.
        extra = {"reasoning_effort": effort} if effort not in ("", None, False, "off") else {}

        made = guarded(kind)(
            f"{NAMING.get(provider, provider)}/{model}",
            api_base=url or "http://localhost:11434",
            api_key="",
            temperature=temperature or 0,
            max_tokens=ROOM[kind],
            **extra,
        )

        built[kind] = (now, made)

        return made


def forget():
    """FORGET WHAT WAS BUILT, FOR WHEN THE SETTINGS BEHIND IT MOVE."""
    built.clear()


def asked(signature, kind=THINKING, **inputs):
    """ONE SIGNATURE ANSWERED, OR None IF THE MODEL COULD NOT BE REACHED.

    A SIGNATURE THAT CANNOT BE ANSWERED IS NEVER AN EXCEPTION OUT OF HERE: EVERY CALLER HAS
    ITS OWN ANSWER FOR WHAT TO DO WITH SILENCE, AND THEY ARE NOT THE SAME ANSWER. WHY IT
    FAILED IS PUT ON trouble FOR THE ONE CALLER THAT TELLS TWO FAILURES APART."""
    global trouble

    trouble = None

    try:
        return dspy.Predict(signature)(lm=ready(kind), **inputs)
    except Exception as error:
        trouble = str(error)

        return None


def picture(image):
    """A PIL PICTURE AS THE FIELD A SIGNATURE WANTS."""
    return dspy.Image.from_PIL(image)


def looked(signature, **inputs):
    """THE SAME, ASKED OF THE MODEL THAT LOOKS AT PICTURES."""
    return asked(signature, kind=LOOKING, **inputs)
