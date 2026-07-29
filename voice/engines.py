"""THE ENGINES THAT MAKE THE SOUND, AND NOTHING ELSE ABOUT THEM.

EACH ONE IS A MODULE WITH A Voice AND AN installed(), IMPORTED ONLY WHEN IT IS
THE ONE CHOSEN, SO AN ENGINE NOBODY USES COSTS NOTHING. TO ADD ONE: WRITE THE
MODULE, PUT IT IN ENGINES, GIVE IT A LABEL IN THE CATALOGUE.
"""

import importlib

from memory import settings
from voice.mute import Mute

PIPER = "piper"

ENGINES = {PIPER: "voice.piper"}

SETTING = "voice.engine"


class VoiceError(Exception):
    pass


def chosen():
    return settings.get(SETTING) or PIPER


def part(engine=None):
    """THE MODULE FOR ONE ENGINE, LOADED THE FIRST TIME IT IS ASKED FOR."""
    engine = engine or chosen()

    if engine not in ENGINES:
        raise VoiceError(f"There is no voice engine called {engine}. There is: {names()}.")

    return importlib.import_module(ENGINES[engine])


def build(engine=None, **kwargs):
    return part(engine).Voice(**kwargs)


def attempt(engine=None, **kwargs):
    """A VOICE, PLUS THE REASON IT IS MUTE WHEN IT IS.

    CATCHES EVERYTHING ON PURPOSE. LOSING THE VOICE IS NOT A REASON TO LOSE THE
    ASSISTANT: HAPPY GOES BACK TO ANSWERING IN WRITING.
    """
    try:
        return build(engine, **kwargs), None
    except Exception as error:
        return Mute(), f"{error}"


def installed(engine=None):
    """THE VOICES THIS ENGINE HAS. NOTHING TO OFFER IS A SHORTER LIST, NOT A FAILURE."""
    try:
        return part(engine).installed()
    except Exception:
        return []


def names():
    return ", ".join(ENGINES)
