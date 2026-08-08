"""TELLING WORDS FROM WHAT A MODEL SAYS INSTEAD WHEN IT CANNOT HEAR SOMETHING."""

import re

# THE OTHER THING IT SAYS INSTEAD OF WORDS: [BLANK_AUDIO], [MUSIC PLAYING], (WIND
# BLOWING). NOBODY SAID ANY OF IT ALOUD, AND A TAKE OF NOTHING HANDED ON WHILE HAPPY
# IS WAITING FOR THE REST OF A SENTENCE BECOMES THE QUESTION HE ANSWERS.
STAGED = re.compile(r"[\[\(][^\]\)]*[\]\)]")


def clean(text):
    heard = (text or "").strip()

    if looping(heard):
        return ""

    # ONLY WHERE IT IS THE WHOLE TAKE. INSIDE A SENTENCE SOMEBODY DID SAY SOMETHING,
    # AND WHAT THEY SAID IS WORTH MORE THAN THE TIDINESS OF THE LINE.
    return "" if not STAGED.sub("", heard).strip() else heard


def looping(text, most=5, unit=8):
    """IT FALLS INTO REPEATING ITSELF, AND NOT ALWAYS ONE CHARACTER AT A TIME.

    A CONSONANT AND ITS VIRAMA ARE TWO CHARACTERS, SO A TELUGU LOOP NEVER REPEATS
    ONE ON ITS OWN AND WAS BEING HANDED ON AS THOUGH IT WERE WORDS.
    """
    for size in range(1, unit + 1):
        for start in range(len(text) - size):
            piece = text[start : start + size]
            run = 1

            while text.startswith(piece, start + run * size):
                run += 1

                if run > most:
                    return True

    return False
