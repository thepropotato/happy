"""TELLING WORDS FROM WHAT A MODEL SAYS INSTEAD WHEN IT CANNOT HEAR SOMETHING."""


def clean(text):
    heard = (text or "").strip()

    return "" if looping(heard) else heard


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
