"""FIGURES AND SHORTHAND WRITTEN OUT AS THE WORDS THEY ARE SAID WITH."""

import re

from num2words import num2words

# A NUMBER BIG ENOUGH TO CARRY SEPARATORS IS THE ONE THAT BREAKS: THE COMMA CUTS IT INTO
# GROUPS AND EACH GROUP IS READ ALONE, SO 100,000 COMES OUT AS A HUNDRED AND THREE ZEROES.
GROUPED = re.compile(r"(?<![\d.])(\d{1,3}(?:,\d{3})+)(?!\d|,\d)")

# WHAT A SYMBOL IN FRONT OF A NUMBER IS WORTH, SAID AFTER IT THE WAY A PERSON SAYS IT.
MONEY = {"$": ("dollar", "dollars"), "£": ("pound", "pounds"), "€": ("euro", "euros"), "¥": ("yen", "yen"),
         "₹": ("rupee", "rupees")}

CURRENCY = re.compile(r"([$£€¥₹])\s?(\d(?:[\d,]*\d)?(?:\.\d+)?)")

# A YEAR IS SAID IN TWO HALVES, NOT AS A COUNT OF THOUSANDS.
# A FULL STOP ENDING THE SENTENCE IS NOT PART OF THE NUMBER, SO ONLY A DIGIT AFTER A POINT
# RULES A YEAR OUT.
YEAR = re.compile(r"\b(in|In|since|Since|by|By|year|Year|until|Until)\s(1[6-9]\d{2}|20\d{2})(?!\d|,\d|\.\d|%)")

PERCENT = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s?%")

# THE VERSION-LIKE RUNS THAT MUST STAY DIGIT BY DIGIT, SO 3.5.1 IS NEVER A DECIMAL.
DOTTED = re.compile(r"\d+(?:\.\d+){2,}")

DECIMAL = re.compile(r"(?<![\d.])(\d[\d,]*)\.(\d+)(?![\d.])")

WHOLE = re.compile(r"(?<![\d.\w])(\d+)(?!\d|\.\d|\w)")

ORDINAL = re.compile(r"(?<![\w])(\d+)(st|nd|rd|th)\b", re.I)

# WHAT A SHORT FORM STANDS FOR OUT LOUD. THE UNITS ONLY COUNT WHEN A NUMBER CAME FIRST.
UNITS = {
    "km": ("kilometre", "kilometres"), "cm": ("centimetre", "centimetres"),
    "mm": ("millimetre", "millimetres"), "kg": ("kilogram", "kilograms"),
    "mb": ("megabyte", "megabytes"), "gb": ("gigabyte", "gigabytes"),
    "tb": ("terabyte", "terabytes"), "kb": ("kilobyte", "kilobytes"),
    "ms": ("millisecond", "milliseconds"), "hz": ("hertz", "hertz"),
    "khz": ("kilohertz", "kilohertz"), "ghz": ("gigahertz", "gigahertz"),
    "m": ("metre", "metres"), "s": ("second", "seconds"), "h": ("hour", "hours"),
}

UNIT = re.compile(r"\b(\d[\d,]*(?:\.\d+)?)\s?(" + "|".join(sorted(UNITS, key=len, reverse=True)) + r")\b", re.I)

# THE WRITTEN SHORTHAND A VOICE SHOULD NEVER SPELL OUT.
SHORTHAND = {
    "e.g.": "for example", "i.e.": "that is", "etc.": "and so on",
    "vs.": "versus", "vs": "versus", "approx.": "approximately",
    "Dr.": "Doctor", "Mr.": "Mister", "Mrs.": "Missus", "Ms.": "Miz",
    "St.": "Saint", "Prof.": "Professor", "No.": "Number",
}

SHORT = re.compile("|".join(re.escape(k) for k in sorted(SHORTHAND, key=len, reverse=True)))


def said(number, kind="cardinal"):
    """ONE FIGURE AS WORDS, OR THE FIGURE BACK IF IT IS NOT ONE WE CAN SAY."""
    try:
        return num2words(number, to=kind).replace("-", " ").replace(",", "")
    except Exception:
        return str(number)


def spoken(text):
    """A SENTENCE WITH EVERY FIGURE AND SHORT FORM PUT INTO THE WORDS IT IS READ AS."""
    said_text = str(text or "")

    # THE RUNS THAT MUST SURVIVE WHOLE ARE PUT ASIDE BEFORE ANY NUMBER RULE TOUCHES THEM.
    kept = []

    def hold(found):
        kept.append(found.group(0))
        return "\x00" + chr(0xE000 + len(kept) - 1) + "\x00"

    said_text = DOTTED.sub(hold, said_text)

    said_text = SHORT.sub(lambda f: SHORTHAND[f.group(0)], said_text)
    said_text = YEAR.sub(lambda f: f'{f.group(1)} {said(int(f.group(2)), "year")}', said_text)

    said_text = CURRENCY.sub(
        lambda f: money(f.group(1), f.group(2)), said_text
    )

    said_text = PERCENT.sub(lambda f: f"{plain(f.group(1))} percent", said_text)
    said_text = UNIT.sub(lambda f: measured(f.group(1), f.group(2)), said_text)

    said_text = ORDINAL.sub(lambda f: said(int(f.group(1)), "ordinal"), said_text)
    said_text = GROUPED.sub(lambda f: said(int(f.group(1).replace(",", ""))), said_text)
    said_text = DECIMAL.sub(
        lambda f: said(float(f.group(1).replace(",", "") + "." + f.group(2))), said_text
    )
    said_text = WHOLE.sub(lambda f: said(int(f.group(1))), said_text)

    return re.sub("\x00(.)\x00", lambda f: kept[ord(f.group(1)) - 0xE000], said_text)


def plain(figure):
    """A FIGURE THAT MAY CARRY SEPARATORS OR A POINT, AS WORDS."""
    bare = figure.replace(",", "")

    return said(float(bare) if "." in bare else int(bare))


def money(mark, figure):
    """A SUM SAID THE WAY IT IS SPOKEN, WITH THE NAME OF THE MONEY AFTER THE COUNT."""
    one, many = MONEY[mark]
    bare = figure.replace(",", "")
    amount = float(bare) if "." in bare else int(bare)

    return f"{said(amount)} {one if amount == 1 else many}"


def measured(figure, unit):
    """A COUNT AND WHAT IT COUNTS, WITH THE UNIT WRITTEN OUT."""
    one, many = UNITS[unit.lower()]
    bare = figure.replace(",", "")
    amount = float(bare) if "." in bare else int(bare)

    return f"{said(amount)} {one if amount == 1 else many}"
