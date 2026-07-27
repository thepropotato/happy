"""WHAT A READING IS MADE OF: WORDS, ROWS, AND THE RECIPE THAT PRODUCED THEM."""

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


class Found(NamedTuple):
    """SOMETHING ON THE SCREEN, AND WHERE TO PUT THE POINTER TO HIT IT."""

    x: int
    y: int
    label: str
    how: str
