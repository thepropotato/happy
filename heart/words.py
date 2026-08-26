"""THE WORDS A PERSON SAYS A TIME IN, AND THE PATTERNS THAT FIND THEM."""

import re

# WHAT A NUMBER LOOKS LIKE WHEN IT IS SPELT OUT, WHICH IS HOW A PERSON SAYS IT.
COUNTS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40,
}

SPANS = {
    "second": 1, "sec": 1, "minute": 60, "min": 60, "hour": 3600, "hr": 3600,
    "day": 86400, "week": 604800,
}

WEEKDAYS = {
    "monday": 0, "mon": 0, "tuesday": 1, "tue": 1, "tues": 1, "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thurs": 3, "friday": 4, "fri": 4, "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}

MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3, "april": 4,
    "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7, "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9, "october": 10, "oct": 10, "november": 11,
    "nov": 11, "december": 12, "dec": 12,
}

# A PART OF THE DAY SAYS WHICH HALF OF THE CLOCK WITHOUT ANYBODY SAYING AM OR PM.
HALVES = {
    "morning": "am", "afternoon": "pm", "evening": "pm", "night": "pm", "tonight": "pm",
    "noon": "pm", "midday": "pm", "midnight": "am",
}

RELATIVE = {"today": 0, "tonight": 0, "tomorrow": 1, "overmorrow": 2}

# WORDS THAT CARRY NOTHING AND SO ARE NOT LEFTOVERS WORTH COMPLAINING ABOUT.
FILLER = frozenset((
    "at", "on", "the", "this", "of", "in", "me", "and", "o'clock", "oclock", "sharp",
    "please", "coming", "upcoming", "for", "by", "around", "about", "remind",
))

# ANYTHING WITH ONE OF THESE IN IT IS NOT A TIME THIS UNDERSTANDS, AND GUESSING AT ONE IS
# WORSE THAN SAYING SO.
BEYOND = frozenset((
    "next", "last", "other", "alternate", "quarter", "past", "til", "till", "to", "between",
))

HALVED = "half"

COUNT = "|".join(sorted([*COUNTS, HALVED], key=len, reverse=True))

SPAN = "|".join(sorted(SPANS, key=len, reverse=True))

MONTH = "|".join(sorted(MONTHS, key=len, reverse=True))

EVERY = re.compile(rf"\bevery\s+(?:(\d+|{COUNT})\s+)?({SPAN})s?\b")

REPEAT = re.compile(r"\bevery\s+(day|weekday|weekend|" + "|".join(WEEKDAYS) + r")s?\b")

PLAINLY = re.compile(r"\b(daily|hourly|nightly|weekly)\b")

OFFSET = re.compile(rf"\b(?:in|after)\s+(\d+|{COUNT})\s*(?:an?\s+)?({SPAN})s?\b")

AHEAD = re.compile(rf"\bin\s+(\d+|{COUNT})\s+(day|week)s?\b")

DATED = re.compile(rf"\b(?:({MONTH})\s+(\d{{1,2}})|(\d{{1,2}})\s+({MONTH}))\b")

DAY_OF_MONTH = re.compile(r"\bthe\s+(\d{1,2})(?:st|nd|rd|th)?\b")

CLOCK = re.compile(r"\b(\d{1,2})(?:[:.](\d{2}))?\s*(a\.?m\.?|p\.?m\.?)?(?=\b|$)")

NOON = re.compile(r"\b(noon|midday|midnight)\b")

HALF = re.compile(r"\b(" + "|".join(HALVES) + r")\b")


def tidy(said):
    text = str(said or "").lower().replace("’", "'")
    text = re.sub(r"[,;!?]", " ", text)

    return " ".join(text.split())


def counted(word, size=1):
    """HOW MANY OF SOMETHING, WHERE half MEANS HALF OF THE THING IT SITS IN FRONT OF."""
    if word == HALVED:
        return size // 2

    return (int(word) if str(word).isdigit() else COUNTS.get(word, 0)) * size


def leftover(text):
    """WHAT WAS NOT UNDERSTOOD, WHICH IS THE ONLY REASON TO REFUSE A PHRASE."""
    return " ".join(word for word in text.split() if word not in FILLER)


def beyond(said):
    """WHETHER THE PHRASE USES SOMETHING THIS DELIBERATELY WILL NOT GUESS AT."""
    return sorted(BEYOND.intersection(tidy(said).split()))
