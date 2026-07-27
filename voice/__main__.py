"""HEAR IT WITHOUT THE REST OF HAPPY: python -m voice "say this out loud" """

import sys

from voice import MODELS, SUFFIX, create
from voice.piper import GET_THEM

if "--voices" in sys.argv:
    print("\n".join(str(path.stem) for path in sorted(MODELS.glob(SUFFIX))) or GET_THEM)
    raise SystemExit

words = " ".join(sys.argv[1:]) or (
    "Right, I opened your downloads folder. There are forty one things in it, "
    "and eleven of them are called screenshot. You might want to look at that."
)

speaker, why = create()

if why:
    print(why)

# FED A WORD AT A TIME, THE WAY THE MODEL ACTUALLY DELIVERS AN ANSWER.
for word in speaker.say(part + " " for part in words.split(" ")):
    print(word, end="", flush=True)

print()
speaker.wait()
speaker.close()
