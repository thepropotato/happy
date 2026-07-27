"""WHAT SEEING IS MADE OF: WORDS AND ROWS OFF A PICTURE, ELEMENTS OFF THE
APPLICATION ITSELF, AND THE SCENE THE TWO OF THEM AGREE ON."""

from typing import NamedTuple

# WHAT COUNTS TOWARDS A RECIPE'S SCORE.
SURE_CONFIDENCE = 60.0


class VisionError(Exception):
    """THE PICTURE COULD NOT BE READ AT ALL."""


class Word(NamedTuple):
    """ONE WORD, WHERE IT SITS IN THE ORIGINAL PICTURE, AND HOW SURE WE ARE."""

    text: str
    confidence: float
    left: int
    top: int
    width: int
    height: int

    @property
    def centre(self):
        return self.left + self.width // 2, self.top + self.height // 2


class Row(NamedTuple):
    """ONE LINE, AS THE WORDS IN IT. IT KEEPS THE WORDS RATHER THAN A STRING SO
    ANYTHING POINTING AT A PHRASE CAN POINT AT THE PART OF THE LINE THAT SAYS
    IT, AND NOT AT THE MIDDLE OF THE WHOLE ROW."""

    words: tuple

    @property
    def text(self):
        return " ".join(word.text for word in self.words)

    @property
    def top(self):
        return min(word.top for word in self.words)

    @property
    def left(self):
        return min(word.left for word in self.words)

    @property
    def right(self):
        return max(word.left + word.width for word in self.words)

    @property
    def height(self):
        return max(word.height for word in self.words)


class Reading(NamedTuple):
    """WHAT ONE RECIPE MADE OF ONE PICTURE."""

    text: str
    confidence: float
    words: list
    lines: list
    recipe: str
    mode: int

    @property
    def score(self):
        """EXPECTED CORRECT CHARACTERS. LENGTH AND CERTAINTY IN ONE NUMBER, SO A
        RECIPE THAT FINDS ONE PERFECT WORD CANNOT BEAT ONE THAT FINDS A PAGE."""
        return sum(
            word.confidence / 100 * len(word.text)
            for word in self.words
            if word.confidence >= SURE_CONFIDENCE
        )


class Recipe(NamedTuple):
    """ONE WAY OF CLEANING A PICTURE UP BEFORE READING IT."""

    name: str
    even: bool = False  # EVEN OUT THE LIGHTING.
    smooth: bool = False  # KILL SENSOR NOISE.
    sharpen: bool = False
    threshold: str = ""  # "", "otsu" OR "adaptive".
    despeckle: bool = False


class Shot(NamedTuple):
    """THE SCREEN AT ONE MOMENT, AND HOW ITS PIXELS RELATE TO THE COORDINATES
    THE POINTER MOVES IN."""

    image: object
    density: float

    def point(self, x, y):
        """A PLACE IN THE PICTURE, AS A PLACE THE POINTER CAN BE SENT TO."""
        return int(x / self.density), int(y / self.density)


class Element(NamedTuple):
    """ONE THING ON THE SCREEN, AS THE APPLICATION HOLDING IT DESCRIBES IT.

    THE BOX IS ALREADY IN THE COORDINATES THE POINTER MOVES IN, BECAUSE THE
    APPLICATION WAS ASKED RATHER THAN PHOTOGRAPHED. NOTHING HERE GOES THROUGH
    Shot.point() AND DOING SO WOULD HALVE EVERY POSITION.
    """

    kind: str
    label: str
    value: str = ""
    left: int = 0
    top: int = 0
    width: int = 0
    height: int = 0
    enabled: bool = True
    focused: bool = False
    ticked: object = None  # True, False, OR None WHEN IT IS NOT THAT SORT OF THING.

    @property
    def centre(self):
        return self.left + self.width // 2, self.top + self.height // 2

    @property
    def said(self):
        """WHAT IT SAYS, FOR MATCHING A SPOKEN TARGET AGAINST IT."""
        return self.label or self.value

    @property
    def state(self):
        """THE PART OF ITS CONDITION THAT A PICTURE COULD NOT HAVE TOLD US.

        focused IS DELIBERATELY NOT HERE. FINDER MARKS EVERY CELL IN A LIST AS
        FOCUSED AT ONCE, SO IT IS NOISE PER ELEMENT; WHAT HAS THE KEYBOARD IS
        ASKED FOR ONCE PER SCENE INSTEAD.
        """
        parts = []

        if self.ticked is not None:
            parts.append("ticked" if self.ticked else "not ticked")

        if not self.enabled:
            parts.append("greyed out")

        return ", ".join(parts)


class Scene(NamedTuple):
    """WHAT IS BELIEVED TRUE ABOUT THE SCREEN AT ONE MOMENT, AND OUT OF WHICH
    SENSES. THE SCREENSHOT IS ONE OBSERVATION OF THIS, NOT THIS."""

    app: str
    window: str
    elements: tuple = ()
    focus: str = ""
    pointer: tuple = (0, 0)
    text: str = ""  # ONLY WHEN THE WORDS WERE ACTUALLY NEEDED. OCR IS NOT FREE.
    mark: str = ""  # THE SCREEN FINGERPRINTED, FOR NOTICING CHANGE WITHOUT OCR.
    senses: tuple = ()
    at: float = 0.0

    @property
    def named(self):
        """THE ELEMENTS WORTH TELLING ANYONE ABOUT."""
        return tuple(each for each in self.elements if each.said)

    @property
    def blind(self):
        """TRUE WHEN NO SENSE ANSWERED AT ALL."""
        return not self.senses


class Found(NamedTuple):
    """SOMETHING ON THE SCREEN, AND WHERE TO PUT THE POINTER TO HIT IT."""

    x: int
    y: int
    label: str
    how: str
    confidence: float = 0.0
    element: object = None  # THE Element IT CAME FROM, WHEN A TREE SUPPLIED IT.
