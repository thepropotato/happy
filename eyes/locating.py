"""WHERE SOMETHING IS ON THE SCREEN."""

from eyes import masking
from eyes.agreeing import PICKED, POINTED, READ, TOLD
from eyes.deciphering import look
from eyes.describing import PICK, POINT, asked, digits, listing, numbers, smaller
from eyes.elements import tree
from eyes.matching import CLICK_CUTOFF, likeness, middle, span, spot, tidy, typing
from eyes.screen import grab
from eyes.shapes import Found

# A LABEL AND THE BUTTON UNDER IT OFTEN SAY THE SAME WORD, AND THEY MEAN THE BUTTON.
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

# THE KINDS YOU CAN PUT WORDS INTO. THESE COME FIRST WHEN SOMEONE SAYS "FIELD".
ENTRY = ("text field", "text box", "search field", "combo box", "dropdown")


def told(target, elements=None):
    """THE ELEMENT THE APPLICATION ITSELF SAYS IS target, OR None."""
    wanted = tidy(target)

    if not wanted:
        return None

    if elements is None:
        elements = tree()

    wants = typing(target)
    worth = []

    for element in elements:
        if not element.said:
            continue

        mark = likeness(wanted, tidy(element.said))

        if mark <= CLICK_CUTOFF:
            continue

        # SOMEWHERE TO TYPE OUTRANKS A BETTER SCORE WHEN THAT IS WHAT WAS ASKED FOR.
        worth.append(((wants and element.kind in ENTRY, mark), element))

    if not worth:
        return None

    found, rivals = decided(worth)

    return Found(*found.centre, found.said, "the application named it", TOLD, found, rivals)


def area(element):
    return element.width * element.height


def overlapping(one, other):
    """TRUE WHEN TWO BOXES SHARE ANY GROUND AT ALL."""
    return (
        one.left < other.left + other.width
        and other.left < one.left + one.width
        and one.top < other.top + other.height
        and other.top < one.top + one.height
    )


def decided(worth):
    """THE ONE MEANT, AND ANYTHING ELSE ANSWERING TO THE SAME NAME."""
    top = max(rank for rank, _ in worth)
    tied = [element for rank, element in worth if rank == top]

    if len(tied) == 1:
        return tied[0], ()

    if all(overlapping(tied[0], other) for other in tied[1:]):
        return max(tied, key=lambda each: (each.enabled, each.kind in ACTIONABLE, area(each))), ()

    found = max(tied, key=lambda each: (each.enabled, area(each)))

    return found, tuple(each for each in tied if each is not found)


def where(target, shot=None, seen=None, ask=True, elements=None):
    """WHERE target IS ON THE SCREEN, AS A POINT FOR THE POINTER, OR None."""
    found = told(target, elements)

    if found:
        return found

    shot = shot or grab()

    # HAPPY'S OWN TRANSCRIPT IS ON THE SCREEN AND ANSWERS TO WHATEVER WAS JUST
    # SAID TO HIM: "resume game of thrones" BEAT EVERY REAL THING CALLED THAT.
    seen = masking.elsewhere(seen or look(shot.image), shot.density)

    words = spot(seen, target)

    if words:
        label = " ".join(word.text for word in words)

        return Found(*shot.point(*middle(words)), label, "words", READ)

    if not ask:
        return None

    return chosen(shot, seen, target) or pointed(shot, target)


def chosen(shot, seen, target):
    """THE MODEL PICKING WHICH PIECE OF READ TEXT IS THE TARGET."""
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
    """THE MODEL GIVING A PLACE OUTRIGHT, FOR WHAT HAS NO TEXT TO PICK."""
    small, ratio = smaller(shot.image)
    pair = numbers(asked(small, POINT.format(target=target, width=small.width, height=small.height)))

    if not pair:
        return None

    x, y = pair

    if not (0 <= x <= small.width and 0 <= y <= small.height):
        return None

    return Found(*shot.point(x / ratio, y / ratio), target, "model pointed at it", POINTED)
