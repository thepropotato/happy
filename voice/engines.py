"""THE ENGINES THAT MAKE THE SOUND, AND NOTHING ELSE ABOUT THEM."""

import importlib

from memory import settings
from voice.mute import Mute

KOKORO = "kokoro"

ENGINES = {KOKORO: "voice.kokoro"}

# THE ONE THAT NEEDS NOTHING BUT THE FILES ALREADY HERE, SO IT IS WHAT SPEAKS WHEN THE PICKED
# ENGINE CANNOT.
FALLBACK = KOKORO

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
    """A VOICE, PLUS THE REASON IT IS NOT THE ONE THAT WAS ASKED FOR."""
    try:
        return build(engine, **kwargs), None
    except Exception as error:
        # A VOICE THAT WILL NOT LOAD IS NOT A REASON TO GO SILENT WHILE ANOTHER ONE WORKS.
        if (engine or chosen()) != FALLBACK:
            try:
                return build(FALLBACK, **kwargs), f"{error} Speaking with the {FALLBACK} voice."
            except Exception:
                pass

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


def names():
    return ", ".join(ENGINES)
