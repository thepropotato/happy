"""TELLING WORDS FROM WHAT A MODEL SAYS INSTEAD WHEN IT CANNOT HEAR SOMETHING."""

import re

# THE OTHER THING IT SAYS INSTEAD OF WORDS: [BLANK_AUDIO], [MUSIC PLAYING], (WIND BLOWING).
STAGED = re.compile(r"[\[\(][^\]\)]*[\]\)]")

# EVERY LANGUAGE'S WORDS, SO A TAKE IN ANY SCRIPT STILL SPLITS INTO ONES.
WORDS = re.compile(r"\w+", re.UNICODE)

# NOTHING BUT THINKING NOISES IS NOT A QUESTION, IT IS SOMEBODY GETTING READY.
NOISES = {"um", "uh", "er", "erm", "hmm", "mm", "hm", "uhh", "ahh", "ah", "oh"}


def nothing(text):
    """TRUE WHEN THE WHOLE TAKE WAS SOMEBODY CLEARING THEIR THROAT."""
    found = WORDS.findall((text or "").lower())

    return not found or all(word in NOISES for word in found)


def clean(text):
    heard = (text or "").strip()

    if looping(heard):
        return ""

    # ONLY WHERE IT IS THE WHOLE TAKE.
    return "" if not STAGED.sub("", heard).strip() else heard


def looping(text, most=5, unit=8):
    """IT FALLS INTO REPEATING ITSELF, AND NOT ALWAYS ONE CHARACTER AT A TIME."""
    for size in range(1, unit + 1):
        for start in range(len(text) - size):
            piece = text[start : start + size]
            run = 1

            while text.startswith(piece, start + run * size):
                run += 1

                if run > most:
                    return True

    return False
