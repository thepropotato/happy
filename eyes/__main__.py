"""READ A PICTURE FROM THE COMMAND LINE: python -m eyes <picture> [--thorough]"""

import sys

from eyes.cleaning import RECIPES
from eyes.loading import factor, load
from eyes.reading import LANGUAGE, MODES, attempt, look
from eyes.tesseract import complaint

problem = complaint()

if problem:
    sys.exit(problem)

if len(sys.argv) < 2:
    sys.exit("Usage: python -m eyes <picture> [--thorough]")

every = "--thorough" in sys.argv

if every:
    source = load(sys.argv[1])
    size = factor(source.shape[1])

    for choice in RECIPES:
        for way in MODES:
            got = attempt(source, choice, way, size, LANGUAGE)
            print(
                f"{choice.name:>9} psm {way:<3} "
                f"score {got.score:8.1f}  confidence {got.confidence:5.1f}  "
                f"{len(got.words)} words"
            )

    print()

best = look(sys.argv[1], thorough=every)

print(f"[{best.recipe}, psm {best.mode}, {best.confidence:.0f}% sure]\n")
print(best.text)
