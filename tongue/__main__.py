"""WHAT LANGUAGE, WITHOUT THE REST OF HAPPY: python -m tongue [some.wav ...] | --get | --export"""

import sys
from pathlib import Path

from face import silence

silence.configure()

import tongue
from tongue import sound

if "--export" in sys.argv:
    from tongue.exporting import export

    export()
    raise SystemExit

if "--get" in sys.argv:
    print("Getting the language detector")
    print(f"Got it: {sound.fetch()}")
    raise SystemExit

if not sound.whole():
    raise SystemExit(
        f"No language detector in {sound.MODELS}. Get it with:\n  python -m tongue --get"
    )

takes = [Path(each) for each in sys.argv[1:] if not each.startswith("--")]

if not takes:
    raise SystemExit("Name a wav or two to listen to.")

for path in takes:
    print(f"{path.name}\t{tongue.aloud(path) or '?'}")
