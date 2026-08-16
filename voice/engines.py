"""THE ENGINES THAT MAKE THE SOUND, AND NOTHING ELSE ABOUT THEM."""

import importlib

from memory import settings
from voice.mute import Mute

KOKORO = "kokoro"
PIPER = "piper"

ENGINES = {KOKORO: "voice.kokoro", PIPER: "voice.piper"}

# KOKORO HAS NO TELUGU VOICE, AND ITS HINDI ONES READ TELUGU'S SOUNDS AS NONSENSE HOWEVER
# WELL THEY SURVIVE ITS ALPHABET, SO THAT ONE LANGUAGE IS READ BY PIPER. THIS IS A NAMED
# EXCEPTION FOR A LANGUAGE, NOT A FALLBACK PATH FOR WHATEVER GOES WRONG.
ELSEWHERE = {"te": PIPER}

SETTING = "voice.engine"


class VoiceError(Exception):
    pass


def chosen():
    return settings.get(SETTING) or KOKORO


def part(engine=None):
    """THE MODULE FOR ONE ENGINE, LOADED THE FIRST TIME IT IS ASKED FOR."""
    engine = engine or chosen()

    if engine not in ENGINES:
        raise VoiceError(f"There is no voice engine called {engine}. There is: {names()}.")

    return importlib.import_module(ENGINES[engine])


def build(engine=None, **kwargs):
    return part(engine).Voice(**kwargs)


def attempt(engine=None, **kwargs):
    """A VOICE, PLUS THE REASON IT IS MUTE WHEN IT IS."""
    try:
        return build(engine, **kwargs), None
    except Exception as error:
        return Mute(), f"{error}"


def pinned(name, engine=None):
    """THE VOICE ONE NAME OFF THE LIST STANDS FOR. ONLY THE ENGINE HOLDING IT KNOWS WHAT ITS
    OWN NAMES MEAN, SO ONLY THE ENGINE IS ASKED."""
    return part(engine).pinned(name)


def installed(engine=None):
    """THE VOICES THIS ENGINE HAS. NOTHING TO OFFER IS A SHORTER LIST, NOT A FAILURE."""
    try:
        return part(engine).installed()
    except Exception:
        return []


def target_language():
    """THE LANGUAGE THIS MACHINE IS SET TO, WHICH IS THE ONE A VOICE IS FETCHED FOR."""
    return (settings.get("ears.language") or "auto").strip().lower()


def names():
    return ", ".join(ENGINES)
