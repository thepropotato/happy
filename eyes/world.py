"""WHAT HAPPY CURRENTLY BELIEVES IS TRUE ABOUT THE DESKTOP.

ONE PLACE HOLDS THE ANSWER TO "WHAT IS ON THE SCREEN", SO NOTHING HAS TO WORK IT
OUT AGAIN FROM A FRESH SCREENSHOT EVERY TIME IT WONDERS. IT KEEPS THE SCENE
BEFORE THE LAST ONE TOO, BECAUSE EVERY USEFUL QUESTION ABOUT AN ACTION IS A
QUESTION ABOUT THE DIFFERENCE BETWEEN TWO MOMENTS.

THE BELIEF IS NEVER TRUSTED FOR A CLICK. IT IS REFRESHED FIRST, EVERY TIME: A
MENU THAT OPENED HALF A SECOND LATE MAKES EVERY REMEMBERED POSITION A LIE.
"""

from eyes import estimating
from eyes.parts import Scene

MAX_CHARS = 1400
MAX_PER_KIND = 12

# THE ORDER A PERSON WOULD LOOK IN: PRESS, THEN FILL IN, THEN MERELY READ.
GROUPS = (
    ("Buttons", ("button", "menu button", "radio button")),
    ("Checkboxes", ("checkbox", "switch", "expander")),
    ("Text fields", ("text field", "text box")),
    ("Dropdowns", ("dropdown",)),
    ("Links", ("link",)),
    ("Tabs", ("tab", "tabs")),
    ("Menus", ("menu",)),
    ("Menu items", ("menu item",)),
    ("Text", ("text", "list item", "image")),
)

NOTHING = "I cannot see any controls in the window in front."


class World:
    """THE BELIEF. ONE PER PROCESS."""

    def __init__(self):
        self.scene = Scene(app="", window="")
        self.before = self.scene

    def refresh(self, words=False):
        """LOOK AGAIN AND BELIEVE WHAT CAME BACK."""
        return self.update(estimating.scene(words=words))

    def glance(self):
        """LOOK AGAIN THE CHEAP WAY, WITHOUT READING ANY WORDS."""
        return self.update(estimating.glance())

    def update(self, scene):
        self.before, self.scene = self.scene, scene

        return scene

    def changed(self):
        """WHAT THE LAST LOOK FOUND DIFFERENT FROM THE ONE BEFORE IT."""
        return estimating.difference(self.before, self.scene)

    def summary(self):
        """THE SCREEN AS STRUCTURE, FOR A PLANNER THAT SHOULD NOT BE READING
        PIXELS. THIS IS WHAT THE MODEL SEES INSTEAD OF A SCREENSHOT."""
        return listing(self.scene)


world = World()


def current():
    """THE ONE WORLD MODEL. EVERYTHING SHARES IT SO NOTHING LOOKS TWICE."""
    return world


def heading(scene):
    where = f"{scene.app or 'something'}"

    if scene.window and scene.window != scene.app:
        where += f", window {scene.window}"

    lines = [f"In front: {where}"]

    if scene.focus:
        lines.append(f"The keyboard is in: {scene.focus}")

    return lines


def described(element):
    """ONE ELEMENT AS A SHORT PHRASE, WITH THE PART A PICTURE COULD NOT SHOW."""
    said = element.said

    if element.value and element.label and element.value != element.label:
        said = f"{element.label} holding {element.value}"

    return f"{said} ({element.state})" if element.state else said


def listing(scene):
    """EVERY CONTROL WORTH NAMING, GROUPED BY WHAT KIND OF THING IT IS."""
    if scene.blind:
        from eyes import structure

        return structure.readable() or NOTHING

    named = scene.named

    if not named:
        return "\n".join(heading(scene)) + f"\n{NOTHING}"

    lines, taken = heading(scene), set()

    for title, kinds in GROUPS:
        here = [each for each in named if each.kind in kinds]

        if not here:
            continue

        taken.update(kinds)
        shown = [described(each) for each in here[:MAX_PER_KIND]]
        more = f", and {len(here) - len(shown)} more" if len(here) > len(shown) else ""
        lines.append(f"{title}: {' | '.join(shown)}{more}")

    rest = [described(each) for each in named if each.kind not in taken][:MAX_PER_KIND]

    if rest:
        lines.append(f"Other: {' | '.join(rest)}")

    if not scene.text:
        return trimmed("\n".join(lines))

    return trimmed("\n".join(lines) + f"\nWords on the screen:\n{scene.text}")


def trimmed(said):
    return said if len(said) <= MAX_CHARS else said[:MAX_CHARS] + "\n... [cut]"
