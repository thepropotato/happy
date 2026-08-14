"""FINDING THE TESSERACT PROGRAM AND RUNNING ONE PASS OF IT."""

import os
import shutil
import sys
from pathlib import Path

import pytesseract

from eyes.parts import VisionError

MACOS = "darwin"
WINDOWS = "win32"

PROGRAM = "tesseract"

# THE WINDOWS INSTALLER NEVER ADDS ITSELF TO THE PATH.
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

ENGINE = 3  # LSTM ONLY.

SPARSE = 11  # TEXT WHEREVER IT IS. THE ONLY ONE THAT SUITS A SCREEN.
PAGE = 3  # FIND THE COLUMNS FIRST, THEN READ. GOOD FOR A WINDOW OF PROSE.

# ONE UNIFORM BLOCK IS LEFT OUT: IT STAPLES THE SIDEBAR ONTO THE MAIN WINDOW.
MODES = (SPARSE, PAGE)

TIMEOUT_SECONDS = 30


def located():
    """THE PROGRAM, OR None. IT IS ALWAYS ON THE MACHINE, THE PATH VARIABLE IS NOT."""
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
    """LOOKED UP EACH TIME, SO INSTALLING TESSERACT DOES NOT MEAN RESTARTING."""
    found = located()

    if not found:
        raise VisionError(complaint())

    pytesseract.pytesseract.tesseract_cmd = found

    return found


def settings(mode, language):
    return f"--oem {ENGINE} --psm {mode} -l {language}"


def scan(image, mode, language):
    """ONE PASS, AS A TABLE OF WORDS AND BOXES."""
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
