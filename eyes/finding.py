"""WHERE SOMETHING IS ON THE SCREEN.

THE WORDS ARE TRIED FIRST BECAUSE OCR KNOWS EXACTLY WHERE IT READ SOMETHING, AND
A MODEL ASKED FOR A COORDINATE IS GUESSING AT ONE. THE MODEL IS FOR WHAT THE
WORDS CANNOT DO: THE ICON WITH NO LABEL, AND THE NAME A PERSON USED THAT IS
NOWHERE ON THE SCREEN.
"""

import difflib

from eyes.describing import PICK, POINT, asked, digits, listing, numbers, smaller
from eyes.parts import Found
from eyes.reading import look
from eyes.screen import grab

# WORDS A PERSON PUTS AROUND WHAT THEY MEAN. "CLICK THE SEND BUTTON" IS A SCREEN
# THAT SAYS "SEND" AND HAS NEVER ONCE SAID "SEND BUTTON".
NOISE = ("the", "a", "an", "that", "this", "button", "icon", "tab", "menu", "field", "box", "link")

PUNCTUATION = " .,:;!?'\"()[[]{}"

# HOW WELL SOMETHING HAS TO MATCH BEFORE WE WILL CLICK IT. STRICTER THAN FOR APP
# NAMES: OPENING THE WRONG APP IS A SHRUG, CLICKING THE WRONG THING IS ANYTHING.
CLICK_CUTOFF = 0.5


def tidy(words):
    """A TARGET OR A LABEL, REDUCED TO WHAT MATTERS FOR MATCHING IT."""
    said = " ".join(words.lower().split())

    for filler in NOISE:
        said = said.removeprefix(filler + " ").removesuffix(" " + filler)

    return said.strip(PUNCTUATION)


def span(line, wanted):
    """THE RUN OF WORDS INSIDE A LINE THAT SAYS wanted, OR THE WHOLE LINE.

    A BUTTON IS A FEW WORDS IN A ROW THAT MAY ALSO HOLD A LABEL AND A SHORTCUT.
    CLICKING THE MIDDLE OF THE ROW WOULD MISS IT.
    """
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
    """HOW WELL A PIECE OF SCREEN TEXT ANSWERS TO wanted, FROM 0 TO 1.

    CONTAINING THE TARGET IS NOT ENOUGH. A SENTENCE WITH "OUTPUT" BURIED IN IT
    CONTAINS IT AS MUCH AS A TAB LABELLED OUTPUT DOES. SO A MATCH IS WORTH HOW
    MUCH OF THE LABEL IT ACCOUNTS FOR: ALL OF A BUTTON, ALMOST NONE OF A
    PARAGRAPH.
    """
    if not label:
        return 0.0

    if wanted == label:
        return 1.0

    spelling = difflib.SequenceMatcher(None, wanted, label).ratio()

    return max(len(wanted) / len(label), spelling) if wanted in label else spelling


def spot(reading, target):
    """THE WORDS ON SCREEN THAT SAY target, OR None. NO MODEL INVOLVED, WHICH
    MAKES THIS BOTH THE FASTEST ANSWER AND THE ONLY EXACT ONE."""
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


def where(target, shot=None, seen=None, ask=True):
    """WHERE target IS ON THE SCREEN, AS A POINT FOR THE POINTER, OR None."""
    shot = shot or grab()
    seen = seen or look(shot.image)

    words = spot(seen, target)

    if words:
        return Found(*shot.point(*middle(words)), " ".join(w.text for w in words), "words")

    if not ask:
        return None

    return chosen(shot, seen, target) or pointed(shot, target)


def chosen(shot, seen, target):
    """THE MODEL PICKING WHICH PIECE OF READ TEXT IS THE TARGET.

    IT ANSWERS WITH A NUMBER, NEVER A COORDINATE. THE NUMBER INDEXES TEXT OCR
    ALREADY FOUND THE EXACT BOX OF, SO A RIGHT ANSWER IS EXACTLY RIGHT AND A
    WRONG ONE IS STILL SOMEWHERE REAL ON THE SCREEN.
    """
    lines, menu = listing(seen)

    if not lines:
        return None

    number = digits(asked(smaller(shot.image)[0], PICK.format(menu=menu, target=target)))

    if number is None or not 0 <= number < len(lines):
        return None

    line = lines[number]
    words = span(line, tidy(target)) if tidy(target) in tidy(line.text) else line.words

    return Found(*shot.point(*middle(words)), line.text, "model picked the words")


def pointed(shot, target):
    """THE MODEL GIVING A PLACE OUTRIGHT, FOR WHAT HAS NO TEXT TO PICK. THE LEAST
    EXACT OF THE THREE WAYS AND THE LAST TRIED."""
    small, ratio = smaller(shot.image)
    pair = numbers(asked(small, POINT.format(target=target, width=small.width, height=small.height)))

    if not pair:
        return None

    x, y = pair

    if not (0 <= x <= small.width and 0 <= y <= small.height):
        return None

    return Found(*shot.point(x / ratio, y / ratio), target, "model pointed at it")
