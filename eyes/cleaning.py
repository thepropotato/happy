"""FIXING A PICTURE BEFORE READING IT.

A SCREENSHOT IS THE WRONG SHAPE FOR OCR: THE LETTERS ARE SMALL, THE TEXT SITS IN
CORNERS INSTEAD OF FLOWING DOWN A PAGE, AND HALF THE WORLD RUNS DARK MODE. SO IT
IS GREYED, ENLARGED, EVENED OUT, THRESHOLDED, STRAIGHTENED, FLIPPED IF THE TEXT
IS THE LIGHT PART, AND GIVEN A QUIET BORDER TO SIT IN.

NO ONE RECIPE WINS ON EVERY PICTURE, SO SEVERAL ARE TRIED AND THE BEST WINS.
"""

import cv2
import numpy as np

from eyes.loading import BORDER, enlarged, greyed
from eyes.parts import Recipe

WHITE = 255
MID_GREY = 128

MIN_ANGLE = 0.3
MAX_ANGLE = 15.0
MIN_INK_PIXELS = 50

CLAHE_CLIP = 2.0
CLAHE_GRID = (8, 8)

BILATERAL_DIAMETER = 5  # SMALL, SO IT SMOOTHS THE PAPER AND NOT THE LETTERS.
BILATERAL_COLOUR = 50
BILATERAL_SPACE = 50

SHARPEN_RADIUS = 1.0
SHARPEN_WEIGHT = 1.5

ADAPTIVE_BLOCK = 31  # ODD, AND WIDE ENOUGH TO HOLD A WHOLE LETTER.
ADAPTIVE_BIAS = 15

SPECK = (2, 2)

# THE FIRST USUALLY WINS: TESSERACT'S OWN BINARISER BEATS OURS ON CLEAN INPUT.
RECIPES = [
    Recipe("sharp", sharpen=True),
    Recipe("otsu", even=True, threshold="otsu"),
    Recipe("adaptive", smooth=True, threshold="adaptive", despeckle=True),
]


def evened(grey):
    """LOCAL CONTRAST, SO A WINDOW IN SHADOW READS LIKE ONE IN THE LIGHT."""
    return cv2.createCLAHE(clipLimit=CLAHE_CLIP, tileGridSize=CLAHE_GRID).apply(grey)


def smoothed(grey):
    """NOISE OUT, EDGES KEPT. A PLAIN BLUR WOULD TAKE THE LETTERS WITH IT."""
    return cv2.bilateralFilter(grey, BILATERAL_DIAMETER, BILATERAL_COLOUR, BILATERAL_SPACE)


def sharpened(grey):
    """ANTIALIASED SCREEN TEXT IS SOFT BY DESIGN. THIS PUTS THE EDGE BACK."""
    blurred = cv2.GaussianBlur(grey, (0, 0), SHARPEN_RADIUS)

    return cv2.addWeighted(grey, SHARPEN_WEIGHT, blurred, 1.0 - SHARPEN_WEIGHT, 0)


def otsu(grey):
    """ONE THRESHOLD FOR THE WHOLE PICTURE, CHOSEN BY THE PICTURE ITSELF."""
    _, binary = cv2.threshold(grey, 0, WHITE, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return binary


def adaptive(grey):
    """A THRESHOLD PER NEIGHBOURHOOD, FOR A WINDOW HALF IN THE SUN."""
    return cv2.adaptiveThreshold(
        grey,
        WHITE,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        ADAPTIVE_BLOCK,
        ADAPTIVE_BIAS,
    )


THRESHOLDS = {"otsu": otsu, "adaptive": adaptive}


def upright(binary):
    """DARK TEXT ON LIGHT PAPER, WHICHEVER WAY IT CAME IN. TEXT IS THE MINORITY
    OF THE PIXELS, SO WHICHEVER COLOUR IS RARER IS THE INK."""
    ink = int(np.count_nonzero(binary == 0))
    paper = binary.size - ink

    return cv2.bitwise_not(binary) if ink > paper else binary


def positive(grey):
    """THE SAME FLIP FOR A PICTURE THAT WAS NEVER THRESHOLDED."""
    return cv2.bitwise_not(grey) if np.median(grey) < MID_GREY else grey


def despeckled(binary):
    """CLOSING SWALLOWS THE STRAY DOTS ADAPTIVE THRESHOLDING LEAVES BEHIND. THE
    KERNEL IS TINY: A BIGGER ONE EATS THE DOT OFF AN i."""
    return cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones(SPECK, np.uint8))


def tilt(binary):
    """HOW FAR THE TEXT IS OFF LEVEL, IN DEGREES."""
    ink = cv2.findNonZero(cv2.bitwise_not(binary))

    if ink is None or len(ink) < MIN_INK_PIXELS:
        return 0.0

    angle = cv2.minAreaRect(ink)[-1]

    if angle > 45:  # THE BOX HAS NO TOP, SO NEAR LEVEL COMES BACK AS NEAR 90.
        angle -= 90

    return angle if MIN_ANGLE < abs(angle) < MAX_ANGLE else 0.0


def straightened(binary):
    angle = tilt(binary)

    if not angle:
        return binary

    height, width = binary.shape[:2]
    turn = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)

    return cv2.warpAffine(
        binary,
        turn,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def bordered(binary):
    return cv2.copyMakeBorder(
        binary, BORDER, BORDER, BORDER, BORDER, cv2.BORDER_CONSTANT, value=WHITE
    )


def prepared(picture, recipe, scale):
    """ONE PICTURE, CLEANED THE WAY ONE RECIPE ASKS FOR."""
    image = enlarged(greyed(picture), scale)

    if recipe.even:
        image = evened(image)

    if recipe.smooth:
        image = smoothed(image)

    if recipe.sharpen:
        image = sharpened(image)

    if recipe.threshold:
        image = upright(THRESHOLDS[recipe.threshold](image))
    else:
        image = positive(image)

    if recipe.despeckle:
        image = despeckled(image)

    return bordered(straightened(image))
