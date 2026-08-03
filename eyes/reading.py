"""THE BEST READING OF A PICTURE, OUT OF SEVERAL TRIES.

TESSERACT SCORES ITS OWN CONFIDENCE PER WORD, WHICH MAKES "BEST" SOMETHING WE
CAN MEASURE INSTEAD OF GUESS. A CLEAN SCREENSHOT USUALLY WINS ON THE FIRST TRY
AND THE REST ARE SKIPPED, BECAUSE THIS SITS IN FRONT OF SOMEONE WAITING.
"""

import numpy as np

from eyes.cleaning import RECIPES, prepared
from eyes.loading import BORDER, factor, load
from eyes.parts import Reading, Row, VisionError, Word
from eyes.tesseract import LANGUAGE, MODES, scan, use

# BELOW THIS A "WORD" IS USUALLY AN ICON EDGE THAT LOOKED LIKE AN L.
KEEP_CONFIDENCE = 40.0

# GOOD ENOUGH TO STOP TRYING: THIS MANY CHARACTERS READ THIS WELL.
ENOUGH_CONFIDENCE = 85.0
ENOUGH_CHARACTERS = 40

# NEAR TIES GO TO WHATEVER WAS TRIED FIRST.
MARGIN = 1.05

PARAGRAPH = "\n\n"

# HOW MANY TIMES THE USUAL LINE SPACING COUNTS AS A GAP WORTH A BLANK LINE.
BREAK = 1.8

# IN LETTER HEIGHTS: HOW CLOSE TO BE ONE ROW, AND HOW CLOSE TO BE ONE SENTENCE.
SAME_ROW = 0.5
SNUG = 1.5


def harvest(found, scale):
    """THE TABLE AS WORDS, EACH WITH THE LINE IT CAME FROM, AND THE BOXES PUT
    BACK IN THE ORIGINAL PICTURE'S COORDINATES."""
    words = []

    for index, raw in enumerate(found["text"]):
        text = raw.strip()

        if not text:
            continue

        try:
            confidence = float(found["conf"][index])
        except (TypeError, ValueError):
            continue

        if confidence < KEEP_CONFIDENCE:
            continue

        where = (found["block_num"][index], found["par_num"][index], found["line_num"][index])

        words.append(
            (
                where,
                Word(
                    text=text,
                    confidence=confidence,
                    left=int((found["left"][index] - BORDER) / scale),
                    top=int((found["top"][index] - BORDER) / scale),
                    width=int(found["width"][index] / scale),
                    height=int(found["height"][index] / scale),
                ),
            )
        )

    return words


def rows(harvested):
    """THE WORDS GATHERED BACK INTO THE LINES THEY CAME FROM."""
    lines, line, where = [], [], None

    for here, word in harvested:
        if line and here != where:
            lines.append(Row(tuple(line)))
            line = []

        where = here
        line.append(word)

    if line:
        lines.append(Row(tuple(line)))

    return lines


def seam(step, usual, before, line):
    """WHAT BELONGS BETWEEN TWO LINES: A SPACE, A NEW LINE, OR A BLANK ONE."""
    if not usual or abs(step) < SAME_ROW * usual:
        # TOUCHING MEANS ONE SENTENCE THAT CHANGED COLOUR; FAR APART MEANS A SIDEBAR.
        return " " if line.left - before.right < SNUG * before.height else "\n"

    # A STEP THAT GOES BACK UP IS THE NEXT COLUMN STARTING.
    return PARAGRAPH if step <= 0 or step > BREAK * usual else "\n"


def laid_out(lines):
    """THE LINES AS TEXT THAT STILL READS LIKE THE SCREEN LOOKED.

    WHAT COUNTS AS A BIG GAP IS MEASURED AGAINST THIS PICTURE'S OWN LINE
    SPACING, SINCE A LIST OF MAIL AND A PARAGRAPH ARE SPACED NOTHING ALIKE.
    """
    if not lines:
        return ""

    steps = [later.top - earlier.top for earlier, later in zip(lines, lines[1:])]
    rises = [step for step in steps if step > 0]
    usual = float(np.median(rises)) if rises else 0.0

    out = [lines[0].text]

    for step, before, line in zip(steps, lines, lines[1:]):
        out.append(seam(step, usual, before, line) + line.text)

    return "".join(out).strip()


def certainty(words):
    return sum(word.confidence for word in words) / len(words) if words else 0.0


def attempt(picture, recipe, mode, scale, language):
    """ONE RECIPE READ ONE WAY."""
    found = scan(prepared(picture, recipe, scale), mode, language)

    if found is None:
        return None

    harvested = harvest(found, scale)
    words = [word for _, word in harvested]
    lines = rows(harvested)

    return Reading(
        text=laid_out(lines),
        confidence=certainty(words),
        words=words,
        lines=lines,
        recipe=recipe.name,
        mode=mode,
    )


def enough(reading):
    """TRUE WHEN A READING IS GOOD ENOUGH THAT TRYING HARDER IS JUST DELAY."""
    return (
        reading.confidence >= ENOUGH_CONFIDENCE
        and sum(len(word.text) for word in reading.words) >= ENOUGH_CHARACTERS
    )


def look(image, language=LANGUAGE, recipes=None, modes=MODES, thorough=False):
    """EVERY RECIPE THE PICTURE NEEDS, AND THE BEST READING OF IT."""
    use()

    picture = load(image)
    scale = factor(picture.shape[1])
    best = None

    for recipe in recipes or RECIPES:
        for mode in modes:
            reading = attempt(picture, recipe, mode, scale, language)

            if reading is None:
                continue

            if best is None or reading.score > best.score * MARGIN:
                best = reading

            if not thorough and enough(reading):
                return best

    if best is None:
        raise VisionError("Tesseract could not get through this picture.")

    return best


def read(image, language=LANGUAGE, **how):
    """THE TEXT IN A PICTURE, AS A STRING."""
    return look(image, language=language, **how).text


def words(image, language=LANGUAGE, **how):
    """THE SAME READING AS WORDS WITH BOXES."""
    return look(image, language=language, **how).words


def find(image, phrase, language=LANGUAGE, **how):
    """EVERY WORD MATCHING A PHRASE, CASE INSENSITIVE."""
    wanted = phrase.strip().lower()

    return [word for word in words(image, language=language, **how) if wanted in word.text.lower()]
