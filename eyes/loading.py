"""GETTING A PICTURE IN, AND UP TO A SIZE WORTH READING."""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from eyes.parts import VisionError

# UI TEXT IS AROUND THIRTEEN PIXELS TALL AND TESSERACT WANTS ABOUT THIRTY. A
# RETINA GRAB IS ALREADY BIG AND IS LEFT ALONE.
TARGET_WIDTH = 3000
MAX_SCALE = 3.0

# TESSERACT READS A LETTER TOUCHING THE BORDER AS A LETTER CUT IN HALF.
BORDER = 20


def load(image):
    """A PATH, A PIL IMAGE OR AN ARRAY, ALL ARRIVING AS ONE THING."""
    if isinstance(image, np.ndarray):
        return image

    if isinstance(image, Image.Image):
        return cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)

    path = Path(image).expanduser()

    if not path.exists():
        raise VisionError(f"There is no picture at {path}.")

    # NOT cv2.imread: IT GOES THROUGH THE C LOCALE AND LOSES ANY PATH WITH A NON
    # ENGLISH LETTER IN IT, WHICH ON WINDOWS IS MOST HOME FOLDERS.
    try:
        raw = np.fromfile(str(path), dtype=np.uint8)
    except OSError as error:
        raise VisionError(f"Could not open {path}: {error}")

    picture = cv2.imdecode(raw, cv2.IMREAD_COLOR)

    return picture if picture is not None else opened(path)


def opened(path):
    """WHAT OPENCV WOULD NOT DECODE, TRIED AGAIN WITH PILLOW."""
    try:
        with Image.open(path) as picture:
            return cv2.cvtColor(np.array(picture.convert("RGB")), cv2.COLOR_RGB2BGR)
    except (OSError, ValueError):
        raise VisionError(f"{path.name} is not a picture I can read.")


def greyed(picture):
    if picture.ndim == 2:
        return picture

    if picture.shape[2] == 4:  # A ROUNDED CORNER MEANS AN ALPHA CHANNEL.
        return cv2.cvtColor(picture, cv2.COLOR_BGRA2GRAY)

    return cv2.cvtColor(picture, cv2.COLOR_BGR2GRAY)


def factor(width):
    """HOW MUCH TO ENLARGE. NEVER SHRINKS, NEVER RUNS AWAY."""
    return min(MAX_SCALE, max(1.0, TARGET_WIDTH / max(width, 1)))


def enlarged(grey, scale):
    if scale <= 1.0:
        return grey

    size = (int(grey.shape[1] * scale), int(grey.shape[0] * scale))

    # CUBIC: A LETTER GROWN WITH NEAREST NEIGHBOUR GETS STAIRCASE EDGES, AND
    # TESSERACT READS STAIRCASES AS PUNCTUATION.
    return cv2.resize(grey, size, interpolation=cv2.INTER_CUBIC)
