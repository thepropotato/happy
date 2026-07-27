"""TRYING THE DESKTOP FROM THE TERMINAL, WITHOUT THE MODEL OR THE MICROPHONE.

    python -m hands.desktop                    what is on the screen right now
    python -m hands.desktop click Send         click something by name
    python -m hands.desktop type "hello"       type into whatever has the cursor
    python -m hands.desktop keys cmd+s         one shortcut
    python -m hands.desktop scroll down 3      scroll a few steps
    python -m hands.desktop where Send         find it, and do not touch it
"""

import sys
import time

import eyes
from hands.desktop import acting

# TIME TO LET GO OF THE TERMINAL AND PUT THE WINDOW YOU MEANT IN FRONT.
DELAY_SECONDS = 3


def main(argv):
    if not argv:
        return look()

    what, rest = argv[0], argv[1:]

    if what == "where":
        return find(" ".join(rest))

    print(f"Switch to the window you want in {DELAY_SECONDS} seconds...")
    time.sleep(DELAY_SECONDS)

    if what == "click":
        return say(acting.clicked(" ".join(rest)))

    if what == "type":
        return say(acting.typed(" ".join(rest)))

    if what == "keys":
        return say(acting.pressed(" ".join(rest)))

    if what == "scroll":
        return say(acting.scrolled(rest[0] if rest else "down", int(rest[1]) if len(rest) > 1 else 1))

    print(__doc__)


def look():
    model = eyes.current()
    started = time.perf_counter()
    scene = model.refresh()
    taken = (time.perf_counter() - started) * 1000

    print(model.summary())
    print(f"\n[{len(scene.elements)} elements, senses {', '.join(scene.senses) or 'none'}, {taken:.0f}ms]")


def find(target):
    started = time.perf_counter()
    found = eyes.where(target)
    taken = (time.perf_counter() - started) * 1000

    if found is None:
        print(f"I cannot find {target} on the screen. [{taken:.0f}ms]")

        return

    print(f"{found.label} at {found.x},{found.y} — {found.how} [{taken:.0f}ms]")


def say(done):
    print(done.said)


if __name__ == "__main__":
    main(sys.argv[1:])
