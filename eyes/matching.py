"""MATCHING WHAT SOMEONE SAID AGAINST WHAT IS WRITTEN ON THE SCREEN."""

import difflib


# "CLICK THE SEND BUTTON" IS A SCREEN THAT SAYS "SEND", NEVER "SEND BUTTON".
NOISE = ("the", "a", "an", "that", "this", "button", "icon", "tab", "menu", "field", "box", "link")

PUNCTUATION = " .,:;!?'\"()[[]{}"

# STRICTER THAN FOR APP NAMES: CLICKING THE WRONG THING IS NOT A SHRUG.
CLICK_CUTOFF = 0.5

# "ATTACHMENT" SPELLS SIXTY PER CENT LIKE "ENTERTAINMENT" AND MEANS NOTHING LIKE IT.
SPELLING_CUTOFF = 0.75

# NOISE FOR SCORING A LABEL, BUT THE WHOLE ANSWER WHEN TWO THINGS BOTH MATCH:
# "THE MESSAGE FIELD" SCORES BEST AGAINST WHATSAPP'S *VOICE MESSAGE* BUTTON.
TYPING = ("field", "box", "input", "bar")


def tidy(words):
    """A TARGET OR A LABEL, REDUCED TO WHAT MATTERS FOR MATCHING IT."""
    said = " ".join(words.lower().split())

    for filler in NOISE:
        said = said.removeprefix(filler + " ").removesuffix(" " + filler)

    return said.strip(PUNCTUATION)


def typing(target):
    """TRUE WHEN THE PERSON NAMED SOMEWHERE TO TYPE RATHER THAN SOMETHING TO PRESS."""
    return any(word.strip(PUNCTUATION) in TYPING for word in target.lower().split())


def span(line, wanted):
    """THE RUN OF WORDS INSIDE A LINE THAT SAYS wanted, OR THE WHOLE LINE."""
    for start in range(len(line.words)):
        for stop in range(start + 1, len(line.words) + 1):
            run = line.words[start:stop]

            if wanted in tidy(" ".join(word.text for word in run)):
                return run

    return line.words


def middle(words):
    """THE CENTRE OF A RUN OF WORDS, IN THE PICTURE'S OWN PIXELS."""
    left = min(word.left for word in words)
    top = min(word.top for word in words)
    right = max(word.left + word.width for word in words)
    bottom = max(word.top + word.height for word in words)

    return (left + right) // 2, (top + bottom) // 2


def likeness(wanted, label):
    """HOW WELL A PIECE OF SCREEN TEXT ANSWERS TO wanted, FROM 0 TO 1."""
    if not label:
        return 0.0

    if wanted == label:
        return 1.0

    spelling = difflib.SequenceMatcher(None, wanted, label).ratio()

    if wanted in label:
        return max(len(wanted) / len(label), spelling)

    if apart(wanted) & apart(label):
        return spelling

    return spelling if spelling >= SPELLING_CUTOFF else 0.0


def apart(said):
    """THE WHOLE WORDS IN SOMETHING, FOR ASKING WHETHER TWO THINGS SHARE ONE."""
    return {word for word in (part.strip(PUNCTUATION) for part in said.split()) if word}


def spot(reading, target):
    """THE WORDS ON SCREEN THAT SAY target, OR None."""
    wanted = tidy(target)

    if not wanted:
        return None

    best, found = CLICK_CUTOFF, None

    for line in reading.lines:
        mark = likeness(wanted, tidy(line.text))

        if mark > best:
            best, found = mark, span(line, wanted)

    for word in reading.words:  # A SINGLE WORD BEATS THE LINE IT SITS IN ON TIES.
        mark = likeness(wanted, tidy(word.text))

        if mark > best:
            best, found = mark, [word]

    return found
