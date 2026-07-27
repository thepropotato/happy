"""WHERE SEEING HAPPENS: TEXT OFF A PICTURE OR A SCREEN, AND WHERE IT SITS."""

from eyes.finding import where
from eyes.parts import Found, Reading, Row, Shot, VisionError, Word
from eyes.reading import find, look, read, words
from eyes.screen import grab
from eyes.tools import TOOLS

__all__ = [
    "Found",
    "Reading",
    "Row",
    "Shot",
    "TOOLS",
    "VisionError",
    "Word",
    "find",
    "grab",
    "look",
    "read",
    "where",
    "words",
]
