"""THE HEARING ENGINES, AND NOTHING ELSE ABOUT THEM."""

import importlib

from memory import settings

PARAKEET = "parakeet"
WHISPER = "whisper"

ENGINES = {PARAKEET: "ears.transcribing", WHISPER: "ears.whisper"}

SETTING = "ears.engine"


class EarsError(Exception):
    pass


def chosen():
    return settings.get(SETTING) or PARAKEET


def part(engine=None):
    """THE MODULE FOR ONE ENGINE, LOADED THE FIRST TIME IT IS ASKED FOR."""
    engine = engine or chosen()

    if engine not in ENGINES:
        raise EarsError(f"There is no ears engine called {engine}. There is: {names()}.")

    return importlib.import_module(ENGINES[engine])


def load_model(engine=None):
    return part(engine).load_model()


def transcribe(audio_file, engine=None):
    return part(engine).transcribe(audio_file)


def warm(engine=None):
    return part(engine).warm()


def fetch(engine=None):
    return part(engine).fetch()


def whole(engine=None):
    return part(engine).whole()


def names():
    return ", ".join(ENGINES)
