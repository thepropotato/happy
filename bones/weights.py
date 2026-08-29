"""THE MODELS, FETCHED WITH THE ENVIRONMENT'S OWN PYTHON RATHER THAN THIS ONE."""

from bones import packages, systems

# WHAT THE SETTINGS ASK FOR BEFORE ANYBODY HAS CHANGED THEM, AND ROUGHLY HOW BIG.
THINKING = ("gpt-oss:20b", "13 GB")
LOOKING = ("qwen3-vl", "6 GB")

# EACH ONE KNOWS HOW TO GET ITSELF, AND SAYS SO THE SAME WAY.
FETCHES = (
    ("Speech model", "ears", "1 GB"),
    ("Voice model", "voice", "330 MB"),
)

# THE MEMORY MODEL HAS NO COMMAND LINE OF ITS OWN, SO IT IS ASKED FOR DIRECTLY.
MEMORY = "from memory import embedding; embedding.fetch()"


def fetch(module):
    """python -m <module> --get, INSIDE THE ENVIRONMENT WHERE THE WHEELS ARE."""
    return systems.run([str(packages.python()), "-m", module, "--get"], quiet=False)


def memory():
    return systems.run([str(packages.python()), "-c", MEMORY], quiet=False)


def held(module):
    """TRUE WHERE THAT MODEL IS ALREADY WHOLE ON THIS MACHINE."""
    asked = HELD.get(module)

    return systems.run([str(packages.python()), "-c", asked]) if asked else False


# A VOICE THAT IS NOT THERE THROWS RATHER THAN ANSWERING FALSE, SO IT IS CAUGHT.
VOICE = """
import sys, voice
try:
    sys.exit(0 if voice.engines.part().find() else 1)
except Exception:
    sys.exit(1)
"""

HELD = {
    "ears": "import sys; from ears import engines; sys.exit(0 if engines.whole() else 1)",
    "voice": VOICE,
    "memory": "import sys; from memory import embedding; sys.exit(0 if embedding.whole() else 1)",
}
