"""HEAR IT WITHOUT THE REST OF HAPPY: python -m voice [--engine name] "say this"

GET A VOICE:
    python -m voice --get [hi | te]
"""

import sys

import voice
from voice import engines

argv = sys.argv[1:]

if "--engines" in argv:
    print(engines.names())
    raise SystemExit

engine = None

if "--engine" in argv:
    at = argv.index("--engine")
    engine = argv[at + 1] if at + 1 < len(argv) else None
    del argv[at : at + 2]

if "--voices" in argv:
    print("\n".join(voice.installed(engine)) or "No voices installed.")
    raise SystemExit

if "--get" in argv:
    at = argv.index("--get")
    wanted = argv[at + 1] if at + 1 < len(argv) else None
    print(f"Got it: {engines.part(engine).fetch(wanted)}")
    raise SystemExit

words = " ".join(argv) or (
    "Right, I opened your downloads folder. There are forty one things in it, "
    "and eleven of them are called screenshot. You might want to look at that."
)

speaker, why = voice.create(engine=engine)

if why:
    print(why)

for word in speaker.say(part + " " for part in words.split(" ")):
    print(word, end="", flush=True)

print()
speaker.wait()
speaker.close()
