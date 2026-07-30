"""HEAR IT WITHOUT THE REST OF HAPPY: python -m ears [some.wav ...] | --get"""

import sys
import time
import wave
from pathlib import Path

from face import silence

silence.configure()

import ears
from ears.microphone import RECORDINGS
from ears.transcribing import GET_IT, MODELS, fetch, whole

if "--get" in sys.argv:
    print(f"Getting the speech model into {MODELS}")
    print(f"Got it: {fetch()}")
    raise SystemExit

if not whole():
    raise SystemExit(GET_IT)

takes = [Path(each) for each in sys.argv[1:]] or sorted(RECORDINGS.glob("*.wav"))

if not takes:
    raise SystemExit(f"Nothing to hear in {RECORDINGS}")


def seconds(path):
    with wave.open(str(path), "rb") as file:
        return file.getnframes() / file.getframerate()


started = time.perf_counter()
ears.warm()
print(f"# warm {time.perf_counter() - started:.2f}s")

heard = 0.0
spent = 0.0

for path in takes:
    length = seconds(path)
    began = time.perf_counter()
    said = ears.transcribe(path)
    took = time.perf_counter() - began

    heard += length
    spent += took

    print(f"{path.name}\t{length:.2f}\t{took:.2f}\t{heard / spent:.1f}x\t{said}", flush=True)

print(f"# total {heard:.1f}s heard in {spent:.1f}s = {heard / spent:.1f}x realtime")
