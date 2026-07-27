"""WHERE SOMETHING IS ON THE SCREEN.

FOUR WAYS OF ANSWERING, TRIED CHEAPEST AND SUREST FIRST, STOPPING AT THE FIRST
ONE THAT ANSWERS:

    1. THE APPLICATION IS ASKED. IT KNOWS ITS OWN BUTTONS AND THEIR EXACT BOXES,
       COSTS NO PICTURE AND NO MODEL, AND IS THE ONLY SOURCE THAT ALSO KNOWS
       WHETHER THE THING IS GREYED OUT.
    2. THE WORDS. OCR KNOWS EXACTLY WHERE IT READ SOMETHING.
    3. THE MODEL PICKS ONE OF THOSE WORDS, BY NUMBER.
    4. THE MODEL POINTS, FOR WHAT HAS NO TEXT AT ALL.

A MODEL IS NEVER ASKED FOR A COORDINATE UNTIL EVERYTHING ELSE HAS FAILED,
BECAUSE A WRONG COORDINATE IS NOT A WRONG ANSWER, IT IS A THING THAT HAPPENED
SOMEWHERE ON YOUR DESKTOP.
"""

from eyes import structure
from eyes.describing import PICK, POINT, asked, digits, listing, numbers, smaller
from eyes.estimating import PICKED, POINTED, READ, TOLD
from eyes.matching import CLICK_CUTOFF, likeness, middle, span, spot, tidy, typing
from eyes.parts import Found
from eyes.reading import look
from eyes.screen import grab

# THE KINDS A PERSON MEANS WHEN THEY NAME SOMETHING TO CLICK. A LABEL AND THE
# BUTTON UNDER IT OFTEN SAY THE SAME WORD, AND THEY MEAN THE BUTTON.
ACTIONABLE = (
    "button",
    "menu button",
    "checkbox",
    "radio button",
    "link",
    "menu",
    "menu item",
    "tab",
    "dropdown",
    "text field",
    "text box",
    "switch",
    "list item",
)

# THE KINDS YOU CAN ACTUALLY PUT WORDS INTO. WHEN SOMEONE SAYS "FIELD" OR "BOX"
# THESE COME FIRST, AHEAD OF HOW WELL ANYTHING MATCHED, BECAUSE EVERYTHING BEING
# RANKED HAS ALREADY PASSED THE CUTOFF AND ONLY ONE OF THEM CAN BE TYPED IN.
ENTRY = ("text field", "text box", "search field", "combo box", "dropdown")


def told(target, elements=None):
    """THE ELEMENT THE APPLICATION ITSELF SAYS IS target, OR None.

    NO PICTURE AND NO MODEL: THIS IS THE WHOLE ANSWER FOR ANY APPLICATION THAT
    DESCRIBES ITSELF, WHICH IS MOST OF THEM, AND IT COMES BACK IN A SIXTH OF A
    SECOND KNOWING THE EXACT BOX.
    """
    wanted = tidy(target)

    if not wanted:
        return None

    if elements is None:
        elements = structure.tree()

    wants = typing(target)
    best, found = None, None

    for element in elements:
        if not element.said:
            continue

        mark = likeness(wanted, tidy(element.said))

        if mark <= CLICK_CUTOFF:
            continue

        # SOMEWHERE TO TYPE OUTRANKS A BETTER SCORE WHEN THAT IS WHAT WAS ASKED
        # FOR. AFTER THAT A TIE GOES TO THE THING YOU COULD ACTUALLY PRESS, AND
        # THEN TO THE ONE THAT IS NOT GREYED OUT.
        rank = (wants and element.kind in ENTRY, mark, element.kind in ACTIONABLE, element.enabled)

        if best is None or rank > best:
            best, found = rank, element

    if found is None:
        return None

    return Found(*found.centre, found.said, "the application named it", TOLD, found)


def where(target, shot=None, seen=None, ask=True, elements=None):
    """WHERE target IS ON THE SCREEN, AS A POINT FOR THE POINTER, OR None.

    NOTHING HERE TAKES A PICTURE UNTIL ASKING HAS FAILED, SO THE COMMON CASE
    NEVER PAYS FOR ONE.
    """
    found = told(target, elements)

    if found:
        return found

    shot = shot or grab()
    seen = seen or look(shot.image)

    words = spot(seen, target)

    if words:
        label = " ".join(word.text for word in words)

        return Found(*shot.point(*middle(words)), label, "words", READ)

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

    return Found(*shot.point(*middle(words)), line.text, "model picked the words", PICKED)


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

    return Found(*shot.point(x / ratio, y / ratio), target, "model pointed at it", POINTED)
