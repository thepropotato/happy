"""THE HANDFUL OF WORDS THIS EAR RELIABLY MISHEARS, PUT BACK.

NOT A SPELLCHECKER AND NOT A GUESS AT WHAT SOMEBODY MEANT. EACH ENTRY IS A MISHEARING THAT
WAS MEASURED ACROSS VOICES IN bench/regress.py, WHERE THE SOUND IS RIGHT AND ONLY THE WORD
BOUNDARY IS WRONG: "in red" IS NOT A THING ANYBODY SAYS TO HAPPY AND "unread" IS SAID DAILY.
"""

import re

# "unread" COMES BACK AS TWO WORDS OR AS A NUMBER. THE NUMBER ONLY COUNTS BESIDE SOMETHING
# THAT CAN BE UNREAD, BECAUSE "how many hundred" IS OTHERWISE A REAL THING TO SAY.
READABLE = r"(?:emails?|messages?|ones?|texts?|mails?|notifications?|chats?)"

MISHEARD = [
    # THE WORD SPLIT IN TWO, WHICH IS THE COMMON ONE. IT ONLY COUNTS BESIDE SOMETHING THAT CAN
    # BE UNREAD, OR AFTER A WORD THAT ASKS ABOUT ONE: "dressed in red" IS A COLOUR AND STAYS.
    (re.compile(r"\b(?:in|and|on|un)[\s-]+red\b(?=\s+" + READABLE + r"\b)", re.I), "unread"),
    (re.compile(r"\b(many|anything|any|as|is that one|is that|is it|the)\s+(?:in|and|on|un)[\s-]+red\b", re.I), r"\1 unread"),

    # THE WORD ALMOST RIGHT.
    (re.compile(r"\bunred\b", re.I), "unread"),
    (re.compile(r"\bunrate\b", re.I), "unread"),

    # THE WORD AS A NUMBER, ONLY WHERE A THING THAT CAN BE UNREAD FOLLOWS.
    (re.compile(r"\b(?:hundred|100)\s+(" + READABLE + r")\b", re.I), r"unread \1"),

    # AND AS A NUMBER STANDING ALONE WHERE THE SENTENCE WAS ASKING WHETHER ONE WAS.
    (re.compile(r"\bis that (?:one )?(?:hundred|100)\b", re.I), "is that one unread"),
]


def corrected(text):
    """ONE TAKE WITH THE KNOWN MISHEARINGS PUT RIGHT."""
    heard = text or ""

    for pattern, right in MISHEARD:
        heard = pattern.sub(right, heard)

    return heard
