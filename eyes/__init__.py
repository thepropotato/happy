"""WHERE SEEING HAPPENS.

TWO WAYS OF SEEING, AND WHICH ONE ANSWERS MATTERS MORE THAN ANYTHING ELSE HERE.
THE APPLICATION CAN BE *ASKED* WHAT IT DREW, WHICH IS FAST, EXACT, AND THE ONLY
SOURCE THAT KNOWS A THING'S KIND AND STATE. FAILING THAT IT CAN BE *LOOKED AT*,
WHICH WORKS ON ANYTHING AND COSTS TEN TIMES AS MUCH. ASKING IS THE DEFAULT AND
PIXELS ARE THE FALLBACK, NEVER THE OTHER WAY AROUND.
"""

from eyes.estimating import difference, glance, meddling, moved, scene
from eyes.finding import told, where
from eyes.parts import Element, Found, Reading, Row, Scene, Shot, VisionError, Word
from eyes.reading import find, look, read, words
from eyes.screen import grab
from eyes.structure import readable, tree
from eyes.tools import TOOLS
from eyes.world import current

__all__ = [
    "Element",
    "Found",
    "Reading",
    "Row",
    "Scene",
    "Shot",
    "TOOLS",
    "VisionError",
    "Word",
    "current",
    "difference",
    "find",
    "glance",
    "grab",
    "look",
    "meddling",
    "moved",
    "read",
    "readable",
    "scene",
    "told",
    "tree",
    "where",
    "words",
]
