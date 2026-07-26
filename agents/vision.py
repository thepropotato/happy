"""
READING THE TEXT INSIDE A PICTURE OF A SCREEN.

TESSERACT IS GOOD AT A SCANNED PAGE AND ONLY FAIR AT A SCREENSHOT, BECAUSE A
SCREENSHOT IS THE WRONG SHAPE FOR IT: THE LETTERS ARE SMALL, THE TEXT IS SCATTERED
IN CORNERS INSTEAD OF FLOWING DOWN A PAGE, AND HALF THE WORLD RUNS DARK MODE,
WHICH IS WHITE ON BLACK, THE EXACT OPPOSITE OF WHAT IT EXPECTS. SO THE PICTURE IS
FIXED BEFORE IT IS READ: GREYED, ENLARGED, EVENED OUT, THRESHOLDED, STRAIGHTENED,
FLIPPED IF THE TEXT IS THE LIGHT PART, AND GIVEN A QUIET BORDER TO SIT IN.

NO ONE RECIPE WINS ON EVERY PICTURE, SO SEVERAL ARE TRIED AND THE BEST READING
WINS. TESSERACT SCORES ITS OWN CONFIDENCE PER WORD, WHICH MAKES "BEST" SOMETHING
WE CAN MEASURE INSTEAD OF GUESS. A CLEAN SCREENSHOT USUALLY WINS ON THE FIRST
TRY AND THE REST ARE SKIPPED, BECAUSE THIS SITS IN FRONT OF SOMEONE WAITING.

NEEDS THE TESSERACT PROGRAM ITSELF, WHICH IS NOT A PYTHON PACKAGE:
    MAC      brew install tesseract
    WINDOWS  winget install UB-Mannheim.TesseractOCR

files.py READS EVERY OTHER KIND OF FILE AND HANDS PICTURES HERE, SO "READ THAT
SCREENSHOT" WORKS WHICHEVER TOOL THE MODEL REACHES FOR FIRST.
"""

import base64
import difflib
import io
import os
import re
import shutil
import sys
from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np
import pytesseract
from langchain_core.tools import tool
from PIL import Image

MACOS = "darwin"
WINDOWS = "win32"

PROGRAM = "tesseract"

# WHERE THE INSTALLERS PUT IT WHEN IT IS NOT ON THE PATH. THE WINDOWS ONE NEVER
# ADDS ITSELF, WHICH IS THE SINGLE MOST COMMON REASON THIS MODULE LOOKS BROKEN.
GUESSES = {
    MACOS: ["/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract"],
    WINDOWS: [
        r"%PROGRAMFILES%\Tesseract-OCR\tesseract.exe",
        r"%PROGRAMFILES(X86)%\Tesseract-OCR\tesseract.exe",
        r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe",
    ],
}

INSTALL = {
    MACOS: "brew install tesseract",
    WINDOWS: "winget install UB-Mannheim.TesseractOCR",
}

LANGUAGE = "eng"

# LSTM ONLY. THE OLD PATTERN MATCHER IS STILL IN THERE AND IS WORSE AT EVERYTHING.
ENGINE = 3

# HOW TESSERACT IS TOLD TO READ THE PAGE, WHICH MATTERS MORE THAN ANY AMOUNT OF
# PREPROCESSING. A SCREEN IS NOT A PAGE: IT IS LABELS IN CORNERS, A SIDEBAR, A
# MENU BAR, AND WHATEVER THE WINDOW ITSELF SAYS.
SPARSE = 11  # TEXT WHEREVER IT IS. THE ONLY ONE THAT SUITS A SCREEN.
PAGE = 3  # FIND THE COLUMNS FIRST, THEN READ. GOOD FOR A WINDOW OF PROSE.
BLOCK = 6  # ONE UNIFORM BLOCK, AS IF EVERYTHING WERE ONE PARAGRAPH.

# BLOCK IS LEFT OUT ON PURPOSE. IT READS STRAIGHT ACROSS THE SCREEN AND STAPLES
# THE SIDEBAR ONTO THE END OF A SENTENCE IN THE MAIN WINDOW, AND IT DOES IT WITH
# THE SAME CONFIDENCE AS A CORRECT READING, SO NOTHING DOWNSTREAM CAN TELL.
MODES = (SPARSE, PAGE)

# A STUCK BINARY WOULD BE A VOICE ASSISTANT THAT NEVER SPEAKS AGAIN.
TIMEOUT_SECONDS = 30

# UI TEXT IS AROUND THIRTEEN PIXELS TALL AND TESSERACT WANTS ABOUT THIRTY, SO
# EVERYTHING SMALL GETS ENLARGED TOWARDS THIS WIDTH. A RETINA GRAB IS ALREADY
# BIG AND IS LEFT ALONE, SINCE ENLARGING A BLURRY LETTER ONLY MAKES IT BIGGER.
TARGET_WIDTH = 3000
MAX_SCALE = 3.0

# WHITE SPACE AROUND THE EDGE. TESSERACT READS A LETTER TOUCHING THE BORDER AS
# A LETTER CUT IN HALF.
BORDER = 20
WHITE = 255

MID_GREY = 128

# HOW FAR OFF LEVEL BEFORE ROTATING IS WORTH THE BLUR IT COSTS. A SCREENSHOT IS
# ALREADY SQUARE TO THE WORLD AND NEVER TRIPS THIS. A PHONE PHOTO OF A MONITOR
# ALWAYS DOES.
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

# BELOW THIS A "WORD" IS USUALLY AN ICON EDGE THAT LOOKED LIKE AN L.
KEEP_CONFIDENCE = 40.0

# WHAT COUNTS TOWARDS A RECIPE'S SCORE.
SURE_CONFIDENCE = 60.0

# GOOD ENOUGH TO STOP TRYING: THIS MANY CHARACTERS READ THIS WELL.
ENOUGH_CONFIDENCE = 85.0
ENOUGH_CHARACTERS = 40

# HOW MUCH BETTER A LATER READING HAS TO BE TO REPLACE AN EARLIER ONE. TWO
# READINGS OF THE SAME WORDS DIFFERING ONLY IN HOW THEY GROUPED THE LINES SCORE
# WITHIN A WHISKER OF EACH OTHER, AND THE SCORE CANNOT SEE THE DIFFERENCE. THE
# ORDER BELOW CAN, SO NEAR TIES GO TO WHATEVER WAS TRIED FIRST.
MARGIN = 1.05

PARAGRAPH = "\n\n"

# A SCREEN HOLDS A FEW HUNDRED WORDS. THIS ONLY CATCHES A SCAN OF SOMETHING VAST.
MAX_CHARS = 20000

# CAPTURE NEEDS PERMISSION ON BOTH SYSTEMS AND IS REFUSED SILENTLY ON ONE OF
# THEM, SO THE FIX IS SPELLED OUT RATHER THAN THE FAILURE REPORTED.
BLIND = (
    "I cannot see the screen. Screen recording has to be allowed for whatever "
    "runs Happy: on macOS in System Settings, Privacy and Security, Screen and "
    "System Audio Recording, then start Happy again. On Windows it is Settings, "
    "Privacy and security, Camera and screen."
)

# WORDS A PERSON PUTS AROUND WHAT THEY ACTUALLY MEAN. "CLICK THE SEND BUTTON"
# IS A SCREEN THAT SAYS "SEND" AND HAS NEVER ONCE SAID "SEND BUTTON".
NOISE = ("the", "a", "an", "that", "this", "button", "icon", "tab", "menu", "field", "box", "link")

PUNCTUATION = " .,:;!?'\"()[[]{}"

# HOW WELL SOMETHING HAS TO MATCH BEFORE WE WILL CLICK IT. STRICTER THAN THE
# CUTOFF FOR APP NAMES IN system.py, BECAUSE OPENING THE WRONG APP IS A SHRUG
# AND CLICKING THE WRONG THING CAN BE ANYTHING AT ALL. BELOW THIS THE MODEL IS
# ASKED, WHICH IS SLOWER AND BETTER THAN A CONFIDENT WRONG CLICK.
CLICK_CUTOFF = 0.5

# HOW WIDE THE PICTURE GOES TO THE LOOKING MODEL.
VLM_WIDTH = 1512

# HOW MANY LINES OF SCREEN TEXT THE MODEL IS OFFERED AT ONCE. A BUSY SCREEN HAS
# HUNDREDS AND THE LIST IS THE EXPENSIVE PART OF THE PROMPT.
MAX_LABELS = 150

PICK = (
    "This is a screenshot. Every piece of text on it was read by OCR and "
    "numbered:\n\n{menu}\n\n"
    "Which number is: {target}\n"
    "Answer with the number on its own. If none of them is it, answer NONE."
)

POINT = (
    "This is a screenshot, {width} pixels wide and {height} tall. "
    "Find: {target}\n"
    "Answer with the centre of it as two numbers, x and y, in pixels of this "
    "image, like 412,300. Nothing else. If it is not on the screen, answer NONE."
)

MISSING_EYES = (
    "I can read the screen but I cannot look at it yet, {model} is not "
    "installed. Get it with: {how}"
)

SCREEN_QUESTION = (
    "This is the screen of the computer you are working on. Answer the question "
    "about it in one or two plain sentences, as if saying them out loud.\n\n"
    "The text below was read off the same screen by OCR. Trust it over your own "
    "reading of the letters, and trust your own eyes for everything it cannot "
    "see: icons, pictures, colours, which window is in front, what is where.\n\n"
    "{text}\n\nQuestion: {question}"
)

# HOW MANY TIMES THE USUAL LINE SPACING COUNTS AS A GAP WORTH A BLANK LINE.
BREAK = 1.8

# HOW CLOSE IN HEIGHT TWO PIECES HAVE TO BE TO COUNT AS THE SAME ROW, AND HOW
# CLOSE ACROSS, IN LETTER HEIGHTS, TO BE THE SAME SENTENCE.
SAME_ROW = 0.5
SNUG = 1.5


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
    THAT ANYTHING POINTING AT A PHRASE CAN POINT AT THE PART OF THE LINE THAT
    SAYS IT, AND NOT AT THE MIDDLE OF THE WHOLE ROW."""

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


# TRIED IN THIS ORDER, AND THE FIRST IS THE ONE THAT USUALLY WINS: A SCREENSHOT
# IS ALREADY PERFECTLY CLEAN, AND TESSERACT'S OWN BINARISER BEATS OURS ON CLEAN
# INPUT. THE OTHERS ARE FOR SCREENS THAT WERE PHOTOGRAPHED, COMPRESSED, OR SIT
# ON A GRADIENT WALLPAPER.
RECIPES = [
    Recipe("sharp", sharpen=True),
    Recipe("otsu", even=True, threshold="otsu"),
    Recipe("adaptive", smooth=True, threshold="adaptive", despeckle=True),
]


def located():
    """THE TESSERACT PROGRAM, OR None. THE PATH IS ALWAYS ON THE MACHINE, THE
    PATH VARIABLE IS NOT."""
    found = shutil.which(PROGRAM)

    if found:
        return found

    for guess in GUESSES.get(sys.platform, []):
        expanded = Path(os.path.expandvars(guess))

        if "%" not in str(expanded) and expanded.exists():
            return str(expanded)

    return None


def ready():
    return located() is not None


def complaint():
    """WHY READING WILL FAIL, OR None WHEN IT WILL NOT."""
    if ready():
        return None

    how = INSTALL.get(sys.platform, "install tesseract for your system")

    return f"Tesseract is not installed. Install it with: {how}"


def use():
    """POINT PYTESSERACT AT THE PROGRAM. LOOKED UP EACH TIME AND NOT ONCE AT
    IMPORT, SO INSTALLING TESSERACT DOES NOT MEAN RESTARTING HAPPY."""
    found = located()

    if not found:
        raise VisionError(complaint())

    pytesseract.pytesseract.tesseract_cmd = found

    return found


def load(image):
    """A PATH, A PIL IMAGE OR AN ARRAY, ALL ARRIVING AS ONE THING."""
    if isinstance(image, np.ndarray):
        return image

    if isinstance(image, Image.Image):
        return cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)

    path = Path(image).expanduser()

    if not path.exists():
        raise VisionError(f"There is no picture at {path}.")

    # NOT cv2.imread: IT GOES THROUGH THE C LOCALE AND LOSES ANY PATH WITH A
    # NON ENGLISH LETTER IN IT, WHICH ON WINDOWS IS MOST HOME FOLDERS.
    try:
        raw = np.fromfile(str(path), dtype=np.uint8)
    except OSError as error:
        raise VisionError(f"Could not open {path}: {error}")

    picture = cv2.imdecode(raw, cv2.IMREAD_COLOR)

    return picture if picture is not None else opened(path)


def opened(path):
    """WHAT OPENCV WOULD NOT DECODE, TRIED AGAIN WITH PILLOW, WHICH KNOWS A FEW
    FORMATS IT DOES NOT."""
    try:
        with Image.open(path) as picture:
            return cv2.cvtColor(np.array(picture.convert("RGB")), cv2.COLOR_RGB2BGR)
    except (OSError, ValueError):
        raise VisionError(f"{path.name} is not a picture I can read.")


def greyed(picture):
    """COLOUR CARRIES NO LETTERS, AND EVERY STEP AFTER THIS IS THREE TIMES
    CHEAPER WITHOUT IT."""
    if picture.ndim == 2:
        return picture

    channels = picture.shape[2]

    if channels == 4:  # A SCREENSHOT WITH A ROUNDED CORNER HAS AN ALPHA CHANNEL.
        return cv2.cvtColor(picture, cv2.COLOR_BGRA2GRAY)

    return cv2.cvtColor(picture, cv2.COLOR_BGR2GRAY)


def factor(width):
    """HOW MUCH TO ENLARGE. NEVER SHRINKS, NEVER RUNS AWAY."""
    return min(MAX_SCALE, max(1.0, TARGET_WIDTH / max(width, 1)))


def enlarged(grey, scale):
    if scale <= 1.0:
        return grey

    size = (int(grey.shape[1] * scale), int(grey.shape[0] * scale))

    # CUBIC, BECAUSE A LETTER GROWN WITH NEAREST NEIGHBOUR GETS STAIRCASE EDGES
    # AND TESSERACT READS STAIRCASES AS PUNCTUATION.
    return cv2.resize(grey, size, interpolation=cv2.INTER_CUBIC)


def evened(grey):
    """LOCAL CONTRAST, SO A WINDOW IN SHADOW READS LIKE ONE IN THE LIGHT."""
    return cv2.createCLAHE(clipLimit=CLAHE_CLIP, tileGridSize=CLAHE_GRID).apply(grey)


def smoothed(grey):
    """NOISE OUT, EDGES KEPT. A PLAIN BLUR WOULD TAKE THE LETTERS WITH IT."""
    return cv2.bilateralFilter(grey, BILATERAL_DIAMETER, BILATERAL_COLOUR, BILATERAL_SPACE)


def sharpened(grey):
    """UNSHARP MASK. ANTIALIASED SCREEN TEXT IS SOFT BY DESIGN AND THIS PUTS THE
    EDGE BACK ON EVERY STROKE."""
    blurred = cv2.GaussianBlur(grey, (0, 0), SHARPEN_RADIUS)

    return cv2.addWeighted(grey, SHARPEN_WEIGHT, blurred, 1.0 - SHARPEN_WEIGHT, 0)


def otsu(grey):
    """ONE THRESHOLD FOR THE WHOLE PICTURE, CHOSEN BY THE PICTURE ITSELF."""
    _, binary = cv2.threshold(grey, 0, WHITE, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return binary


def adaptive(grey):
    """A THRESHOLD PER NEIGHBOURHOOD, FOR A WINDOW HALF IN THE SUN OR A DIALOG
    SITTING ON A GRADIENT."""
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
    """DARK TEXT ON LIGHT PAPER, WHICHEVER WAY IT CAME IN.

    TEXT IS THE MINORITY OF THE PIXELS ON ANY REAL PAGE, SO WHICHEVER COLOUR IS
    RARER IS THE INK. DARK MODE COMES OUT OF ANY THRESHOLD BACKWARDS AND THIS IS
    WHAT PUTS IT RIGHT."""
    ink = int(np.count_nonzero(binary == 0))
    paper = binary.size - ink

    return cv2.bitwise_not(binary) if ink > paper else binary


def positive(grey):
    """THE SAME FLIP FOR A PICTURE THAT WAS NEVER THRESHOLDED, DECIDED ON
    OVERALL BRIGHTNESS INSTEAD OF ON A PIXEL COUNT."""
    return cv2.bitwise_not(grey) if np.median(grey) < MID_GREY else grey


def despeckled(binary):
    """CLOSING SWALLOWS THE STRAY DARK DOTS ADAPTIVE THRESHOLDING LEAVES BEHIND.
    THE KERNEL IS TINY ON PURPOSE, A BIGGER ONE EATS THE DOT OFF AN i."""
    return cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones(SPECK, np.uint8))


def tilt(binary):
    """HOW FAR THE TEXT IS OFF LEVEL, IN DEGREES, FROM THE TIGHTEST BOX THAT
    HOLDS EVERY DARK PIXEL."""
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
    centre = (width / 2, height / 2)
    turn = cv2.getRotationMatrix2D(centre, angle, 1.0)

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


def settings(mode, language):
    return f"--oem {ENGINE} --psm {mode} -l {language}"


def scan(image, mode, language):
    """ONE PASS OF TESSERACT, AS A TABLE OF WORDS AND BOXES."""
    try:
        return pytesseract.image_to_data(
            image,
            config=settings(mode, language),
            output_type=pytesseract.Output.DICT,
            timeout=TIMEOUT_SECONDS,
        )
    except RuntimeError:  # THE TIMEOUT.
        return None
    except pytesseract.TesseractNotFoundError:
        raise VisionError(complaint() or "Tesseract could not be run.")
    except pytesseract.TesseractError as error:
        raise VisionError(f"Tesseract refused the picture: {error}")


def harvest(found, scale):
    """THE TABLE AS WORDS, EACH WITH THE LINE IT CAME FROM, AND THE BOXES PUT
    BACK IN THE ORIGINAL PICTURE'S COORDINATES SO A CALLER CAN POINT AT WHAT WAS
    READ."""
    words = []

    for index, raw in enumerate(found["text"]):
        text = raw.strip()

        if not text:
            continue

        try:
            confidence = float(found["conf"][index])
        except (TypeError, ValueError):
            continue

        if confidence < KEEP_CONFIDENCE:
            continue

        where = (found["block_num"][index], found["par_num"][index], found["line_num"][index])

        words.append(
            (
                where,
                Word(
                    text=text,
                    confidence=confidence,
                    left=int((found["left"][index] - BORDER) / scale),
                    top=int((found["top"][index] - BORDER) / scale),
                    width=int(found["width"][index] / scale),
                    height=int(found["height"][index] / scale),
                ),
            )
        )

    return words


def rows(harvested):
    """THE WORDS GATHERED BACK INTO THE LINES THEY CAME FROM."""
    lines = []
    line = []
    where = None

    for here, word in harvested:
        if line and here != where:
            lines.append(Row(tuple(line)))
            line = []

        where = here
        line.append(word)

    if line:
        lines.append(Row(tuple(line)))

    return lines


def seam(step, usual, before, line):
    """WHAT BELONGS BETWEEN TWO LINES: A SPACE, A NEW LINE, OR A BLANK ONE."""
    if not usual or abs(step) < SAME_ROW * usual:
        # ONE ROW READ AS TWO. TOUCHING MEANS ONE SENTENCE THAT CHANGED COLOUR
        # PART WAY THROUGH. FAR APART MEANS A SIDEBAR THAT HAPPENS TO LINE UP,
        # AND JOINING THOSE IS HOW OCR PUTS WORDS IN SENTENCES THEY NEVER
        # BELONGED TO.
        return " " if line.left - before.right < SNUG * before.height else "\n"

    # A STEP THAT GOES BACK UP IS THE NEXT COLUMN STARTING, WHICH IS AS BIG A
    # BREAK AS THERE IS.
    return PARAGRAPH if step <= 0 or step > BREAK * usual else "\n"


def laid_out(lines):
    """THE LINES AS TEXT THAT STILL READS LIKE THE SCREEN LOOKED.

    A BLANK LINE MEANS A REAL GAP ON THE SCREEN AND NOT A CHANGE OF BLOCK
    NUMBER, BECAUSE SPARSE READING CALLS EVERY LINE ITS OWN BLOCK AND WOULD
    DOUBLE SPACE THE WHOLE SCREEN. WHAT COUNTS AS A BIG GAP IS MEASURED AGAINST
    THIS PICTURE'S OWN LINE SPACING, SINCE A LIST OF MAIL AND A PARAGRAPH OF
    PROSE ARE SPACED NOTHING ALIKE."""
    if not lines:
        return ""

    steps = [later.top - earlier.top for earlier, later in zip(lines, lines[1:])]
    rises = [step for step in steps if step > 0]
    usual = float(np.median(rises)) if rises else 0.0

    out = [lines[0].text]

    for step, before, line in zip(steps, lines, lines[1:]):
        out.append(seam(step, usual, before, line) + line.text)

    return "".join(out).strip()


def certainty(words):
    return sum(word.confidence for word in words) / len(words) if words else 0.0


def attempt(picture, recipe, mode, scale, language):
    """ONE RECIPE READ ONE WAY."""
    found = scan(prepared(picture, recipe, scale), mode, language)

    if found is None:
        return None

    harvested = harvest(found, scale)
    words = [word for _, word in harvested]
    lines = rows(harvested)

    return Reading(
        text=laid_out(lines),
        confidence=certainty(words),
        words=words,
        lines=lines,
        recipe=recipe.name,
        mode=mode,
    )


def enough(reading):
    """TRUE WHEN A READING IS GOOD ENOUGH THAT TRYING HARDER IS JUST DELAY."""
    return (
        reading.confidence >= ENOUGH_CONFIDENCE
        and sum(len(word.text) for word in reading.words) >= ENOUGH_CHARACTERS
    )


def look(image, language=LANGUAGE, recipes=None, modes=MODES, thorough=False):
    """EVERY RECIPE THE PICTURE NEEDS, AND THE BEST READING OF IT.

    STOPS EARLY ON A CONFIDENT READING UNLESS thorough, WHICH RUNS THE LOT AND
    IS WHAT YOU WANT WHEN COMPARING RECIPES RATHER THAN ANSWERING SOMEONE."""
    use()

    picture = load(image)
    scale = factor(picture.shape[1])
    best = None

    for recipe in recipes or RECIPES:
        for mode in modes:
            reading = attempt(picture, recipe, mode, scale, language)

            if reading is None:
                continue

            if best is None or reading.score > best.score * MARGIN:
                best = reading

            if not thorough and enough(reading):
                return best

    if best is None:  # EVERY PASS TIMED OUT, OR THERE WERE NONE TO RUN.
        raise VisionError("Tesseract could not get through this picture.")

    return best


def read(image, language=LANGUAGE, **how):
    """THE TEXT IN A PICTURE, AS A STRING. THE ONE CALL MOST CALLERS WANT."""
    return look(image, language=language, **how).text


def words(image, language=LANGUAGE, **how):
    """THE SAME READING AS WORDS WITH BOXES, FOR ANYTHING THAT HAS TO POINT AT
    WHAT IT FOUND."""
    return look(image, language=language, **how).words


def find(image, phrase, language=LANGUAGE, **how):
    """EVERY WORD MATCHING A PHRASE, CASE INSENSITIVE."""
    wanted = phrase.strip().lower()

    return [word for word in words(image, language=language, **how) if wanted in word.text.lower()]


# THE SCREEN ITSELF, AND FINDING THINGS ON IT.


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


def density(pixels):
    """HOW MANY PIXELS OF PICTURE THERE ARE TO ONE STEP OF THE POINTER.

    TWO ON EVERY RETINA MAC AND ON A SCALED WINDOWS DISPLAY. GETTING THIS WRONG
    IS NOT A NEAR MISS: A CLICK MEANT FOR THE MIDDLE OF THE SCREEN LANDS PAST
    THE BOTTOM RIGHT CORNER."""
    try:
        from screeninfo import get_monitors

        monitors = get_monitors()
    except Exception:  # NO DISPLAY, OR A PLATFORM IT DOES NOT KNOW.
        return 1.0

    for monitor in monitors:
        if monitor.is_primary and monitor.width:
            return pixels / monitor.width

    return pixels / monitors[0].width if monitors and monitors[0].width else 1.0


def grab():
    """THE WHOLE SCREEN, NOW."""
    from PIL import ImageGrab

    try:
        picture = ImageGrab.grab()
    except Exception as error:
        raise VisionError(f"{BLIND} ({error})")

    if picture is None:
        raise VisionError(BLIND)

    # PERMISSION IS NOT REFUSED OUT LOUD ON MACOS. THE GRAB SUCCEEDS AND EVERY
    # PIXEL IN IT IS BLACK, WHICH WOULD OTHERWISE READ AS AN EMPTY SCREEN.
    if picture.convert("L").getextrema() == (0, 0):
        raise VisionError(BLIND)

    return Shot(picture, density(picture.width))


def tidy(words):
    """A TARGET OR A LABEL, REDUCED TO WHAT MATTERS FOR MATCHING IT."""
    said = " ".join(words.lower().split())

    for filler in NOISE:
        said = said.removeprefix(filler + " ").removesuffix(" " + filler)

    return said.strip(PUNCTUATION)


def span(line, wanted):
    """THE RUN OF WORDS INSIDE A LINE THAT SAYS wanted, OR THE WHOLE LINE.

    A BUTTON IS A FEW WORDS IN A ROW THAT MAY ALSO HOLD A LABEL AND A SHORTCUT.
    CLICKING THE MIDDLE OF THE ROW WOULD MISS IT."""
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

    CONTAINING THE TARGET IS NOT ENOUGH ON ITS OWN. A SENTENCE OF PROSE WITH THE
    WORD "OUTPUT" BURIED IN IT CONTAINS IT EXACTLY AS MUCH AS A TAB LABELLED
    OUTPUT DOES, AND CLICKING THE SENTENCE IS NOT A NEAR MISS. SO A MATCH IS
    WORTH HOW MUCH OF THE LABEL IT ACCOUNTS FOR, WHICH IS ALL OF A BUTTON AND
    ALMOST NONE OF A PARAGRAPH."""
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
    """WHERE target IS ON THE SCREEN, AS A POINT FOR THE POINTER, OR None.

    THE WORDS ARE TRIED FIRST BECAUSE OCR KNOWS EXACTLY WHERE IT READ SOMETHING,
    AND A MODEL ASKED FOR A COORDINATE IS GUESSING AT ONE. THE MODEL IS FOR WHAT
    THE WORDS CANNOT DO: THE ICON WITH NO LABEL, AND THE NAME A PERSON USED THAT
    IS NOWHERE ON THE SCREEN."""
    shot = shot or grab()
    seen = seen or look(shot.image)

    words = spot(seen, target)

    if words:
        return Found(*shot.point(*middle(words)), " ".join(w.text for w in words), "words")

    if not ask:
        return None

    return chosen(shot, seen, target) or pointed(shot, target)


# THE MODEL THAT LOOKS. OCR SAYS WHAT THE WORDS ARE AND EXACTLY WHERE, AND IS
# BLIND TO EVERYTHING ELSE: AN ICON, A CHECKBOX, WHICH WINDOW IS IN FRONT, WHAT
# THE LAYOUT MEANS. THE MODEL SEES ALL OF THAT AND IS BAD AT COORDINATES, SO IT
# IS ASKED TO PICK FROM WHAT OCR ALREADY LOCATED RATHER THAN TO MEASURE.


def smaller(image):
    """THE PICTURE AT A SIZE WORTH SENDING. A FULL RETINA GRAB IS MEGABYTES OF
    BASE64 AND MOSTLY EMPTY DESKTOP, AND EVERY ONE OF THOSE BYTES IS TIME."""
    if image.width <= VLM_WIDTH:
        return image, 1.0

    ratio = VLM_WIDTH / image.width

    return image.resize((VLM_WIDTH, int(image.height * ratio))), ratio


def packed(image):
    """THE PICTURE AS THE MODEL WANTS IT: BASE64 IN A DATA URL."""
    hold = io.BytesIO()
    image.save(hold, format="PNG")

    return "data:image/png;base64," + base64.b64encode(hold.getvalue()).decode()


def asked(image, question):
    """ONE QUESTION ABOUT ONE PICTURE, ANSWERED BY THE LOOKING MODEL."""
    import llm  # LATE: llm REACHES BACK INTO agents FOR WHAT IS INSTALLED.

    from langchain_core.messages import HumanMessage

    message = HumanMessage(
        content=[
            {"type": "text", "text": question},
            {"type": "image_url", "image_url": {"url": packed(image)}},
        ]
    )

    try:
        return llm.eyes().invoke([message]).text.strip()
    except Exception as error:
        said = llm.reason(error)

        if "not found" in said.lower():  # THE SERVER IS UP, THE MODEL IS NOT THERE.
            raise VisionError(
                MISSING_EYES.format(
                    model=llm.VISION_MODEL, how=llm.obtain(llm.VISION_MODEL)
                )
            )

        raise VisionError(f"{llm.VISION_MODEL} could not look at it: {said}")


def listing(seen, limit=MAX_LABELS):
    """THE TEXT ON SCREEN AS A NUMBERED MENU FOR THE MODEL TO PICK FROM."""
    lines = [line for line in seen.lines if line.text.strip()][:limit]

    return lines, "\n".join(f"{number}: {line.text}" for number, line in enumerate(lines))


def chosen(shot, seen, target):
    """THE MODEL PICKING WHICH PIECE OF READ TEXT IS THE TARGET.

    IT ANSWERS WITH A NUMBER, NEVER A COORDINATE. THE NUMBER IS AN INDEX INTO
    TEXT OCR ALREADY FOUND THE EXACT BOX OF, SO A RIGHT ANSWER IS EXACTLY RIGHT
    AND A WRONG ONE IS STILL SOMEWHERE REAL ON THE SCREEN."""
    lines, menu = listing(seen)

    if not lines:
        return None

    answer = asked(smaller(shot.image)[0], PICK.format(menu=menu, target=target))
    number = digits(answer)

    if number is None or not 0 <= number < len(lines):
        return None

    line = lines[number]
    words = span(line, tidy(target)) if tidy(target) in tidy(line.text) else line.words

    return Found(*shot.point(*middle(words)), line.text, "model picked the words")


def pointed(shot, target):
    """THE MODEL GIVING A PLACE OUTRIGHT, FOR WHAT HAS NO TEXT TO PICK: AN ICON,
    A SWITCH, A PICTURE. THE LEAST EXACT OF THE THREE WAYS AND THE LAST TRIED."""
    small, ratio = smaller(shot.image)
    answer = asked(small, POINT.format(target=target, width=small.width, height=small.height))
    pair = numbers(answer)

    if not pair:
        return None

    x, y = pair

    if not (0 <= x <= small.width and 0 <= y <= small.height):
        return None

    return Found(*shot.point(x / ratio, y / ratio), target, "model pointed at it")


def digits(answer):
    """THE FIRST WHOLE NUMBER IN AN ANSWER, OR None. MODELS SAY "3" AND THEY SAY
    "THE ANSWER IS 3." AND BOTH ARE THE SAME ANSWER."""
    found = re.search(r"-?\d+", answer or "")

    return int(found.group()) if found else None


def numbers(answer):
    """THE FIRST PAIR OF NUMBERS IN AN ANSWER, OR None."""
    found = re.findall(r"-?\d+(?:\.\d+)?", answer or "")

    return (float(found[0]), float(found[1])) if len(found) >= 2 else None


# TOOLS. THE DESCRIPTIONS BELOW ARE READ BY THE MODEL, NOT BY US, SO THEY ARE
# WRITTEN AS PLAIN PROSE RATHER THAN AS COMMENTS.


@tool
def read_image(path: str) -> str:
    """Read the words inside a picture: a screenshot, a photo of a screen or a
    sign, a scanned page, or anything else where the text is part of the image
    rather than in the file. Accepts a full path like "~/Desktop/shot.png", or
    just a name like "screenshot" or "the receipt photo", in which case it finds
    the picture first.

    Use this whenever you are asked what a picture says or shows in words. Do
    not say you cannot see images."""
    from agents import files  # LATE, SO files CAN HAND PICTURES BACK HERE.

    where, note = files.locate(path)

    if where is None:
        return note

    if where.is_dir():
        return f"{where} is a folder, not a picture."

    try:
        seen = look(where)
    except VisionError as problem:
        return str(problem)

    if not seen.text:
        return f"{where.name} is a picture, but there are no words in it."

    header = f"{note}\n" if note else ""

    return f"{header}{seen.text[:MAX_CHARS]}"


@tool
def read_screen() -> str:
    """Read the text that is on the screen right now, exactly as it appears,
    with the layout kept. Use this whenever you are asked what is on the screen,
    what a window says, what an error message is, or what the user is looking
    at. This is fast and exact, so prefer it over look_at_screen whenever the
    answer is written on the screen in words."""
    try:
        seen = look(grab().image)
    except VisionError as problem:
        return str(problem)

    return seen.text[:MAX_CHARS] if seen.text else "There is no text on the screen."


@tool
def look_at_screen(question: str) -> str:
    """Ask about what the screen looks like, rather than what it says: which
    window is in front, where something sits, what an icon or a picture shows,
    what colour something is, whether a box is ticked. Give the question you
    want answered.

    This wakes a second model and takes several seconds, so use read_screen
    instead when the answer is text that is written on the screen."""
    try:
        shot = grab()
        seen = look(shot.image)

        return asked(smaller(shot.image)[0], SCREEN_QUESTION.format(text=seen.text[:MAX_CHARS], question=question))
    except VisionError as problem:
        return str(problem)


TOOLS = [read_image, read_screen, look_at_screen]


if __name__ == "__main__":
    problem = complaint()

    if problem:
        sys.exit(problem)

    if len(sys.argv) < 2:
        sys.exit("Usage: python agents/vision.py <picture> [--thorough]")

    every = "--thorough" in sys.argv

    if every:  # EVERY RECIPE, SIDE BY SIDE, TO SEE WHICH ONE THIS PICTURE LIKES.
        source = load(sys.argv[1])
        size = factor(source.shape[1])

        for choice in RECIPES:
            for way in MODES:
                got = attempt(source, choice, way, size, LANGUAGE)
                print(
                    f"{choice.name:>9} psm {way:<3} "
                    f"score {got.score:8.1f}  confidence {got.confidence:5.1f}  "
                    f"{len(got.words)} words"
                )

        print()

    best = look(sys.argv[1], thorough=every)
    print(f"[{best.recipe}, psm {best.mode}, {best.confidence:.0f}% sure]\n")
    print(best.text)
