"""THE PERSON'S WORDS FOR WHEN, TAKEN APART INTO THE PIECES A DATE IS MADE OF."""

import re

from heart.words import (
    AHEAD, CLOCK, DATED, DAY_OF_MONTH, EVERY, HALF, HALVES, MONTHS, NOON, OFFSET, PLAINLY,
    RELATIVE, REPEAT, SPANS, WEEKDAYS, counted, leftover, tidy,
)


BLANK = {
    "offset": None, "every": None, "repeat": "", "weekday": None, "date": None,
    "days": None, "shifted": False, "clocks": [], "rest": "",
}


def parts(said):
    """WHAT A TIME PHRASE IS MADE OF. rest HOLDS WHATEVER WAS NOT UNDERSTOOD."""
    text = tidy(said)
    found = dict(BLANK)

    for step in (recurring, offsetting, daying, dating, clocking):
        text = step(text, found)

    found["rest"] = leftover(text)

    return found


def recurring(text, found):
    """every hour, every day at eight, every monday, daily."""
    mark = REPEAT.search(text)

    if mark:
        word = mark.group(1)

        if word in WEEKDAYS:
            found["repeat"], found["weekday"] = "weekly", WEEKDAYS[word]
        elif word in ("weekday", "weekend"):
            found["repeat"] = f"{word}s"
        else:
            found["repeat"] = "daily"

        return REPEAT.sub(" ", text)

    mark = PLAINLY.search(text)

    if mark:
        said = mark.group(1)

        if said == "hourly":
            found["every"] = SPANS["hour"]
        elif said == "weekly":
            found["repeat"] = "weekly"
        else:
            found["repeat"] = "daily"

        return PLAINLY.sub(" ", text)

    mark = EVERY.search(text)

    if mark:
        size = SPANS[mark.group(2)]
        found["every"] = counted(mark.group(1), size) or size

        return EVERY.sub(" ", text)

    return text


def offsetting(text, found):
    """in twenty minutes, after an hour. A DAY OR MORE PINS A DAY RATHER THAN AN INSTANT."""
    mark = AHEAD.search(text)

    if mark:
        found["days"] = counted(mark.group(1), 7 if mark.group(2) == "week" else 1)
        found["shifted"] = True

        return AHEAD.sub(" ", text)

    mark = OFFSET.search(text)

    if mark:
        found["offset"] = counted(mark.group(1), SPANS[mark.group(2)])

        return OFFSET.sub(" ", text)

    return text


def daying(text, found):
    """today, tomorrow, friday."""
    for word, span in RELATIVE.items():
        if not re.search(rf"\b{word}\b", text):
            continue

        if found["days"] is None:
            found["days"] = span

        # tonight ALSO SAYS WHICH HALF OF THE CLOCK, SO IT IS LEFT FOR clocking TO READ.
        if word != "tonight":
            text = re.sub(rf"\b{word}\b", " ", text)

    if found["weekday"] is not None:
        return text

    for word, number in WEEKDAYS.items():
        if re.search(rf"\b{word}\b", text):
            found["weekday"] = number

            return re.sub(rf"\b{word}\b", " ", text)

    return text


def dating(text, found):
    """may 21, 21 may, the twenty first."""
    mark = DATED.search(text)

    if mark:
        found["date"] = (
            MONTHS[mark.group(1) or mark.group(4)],
            int(mark.group(2) or mark.group(3)),
        )

        return DATED.sub(" ", text)

    mark = DAY_OF_MONTH.search(text)

    if mark:
        found["date"] = (None, int(mark.group(1)))

        return DAY_OF_MONTH.sub(" ", text)

    return text


def clocking(text, found):
    """at four, at 4:30 pm, at noon, in the evening."""
    mark = NOON.search(text)

    if mark:
        found["clocks"] = [(0, 0)] if mark.group(1) == "midnight" else [(12, 0)]

        return NOON.sub(" ", text)

    half = halving(text)
    text = HALF.sub(" ", text)

    mark = CLOCK.search(text)

    if not mark:
        return text

    hour, minute = int(mark.group(1)), int(mark.group(2) or 0)

    if hour > 24 or minute > 59:
        return text

    found["clocks"] = readings(hour, minute, (mark.group(3) or "").replace(".", "")[:2] or half)

    return text[: mark.start()] + " " + text[mark.end():]


def halving(text):
    """WHICH HALF OF THE CLOCK A PART OF THE DAY SAYS, OR None."""
    mark = HALF.search(text)

    return HALVES[mark.group(1)] if mark else None


def readings(hour, minute, stated):
    """EVERY CLOCK FACE THOSE WORDS COULD MEAN: TWO WHEN NOBODY SAID WHICH HALF OF THE
    DAY, ONE WHENEVER THEY DID OR WHENEVER THE HOUR SAYS SO ON ITS OWN."""
    if hour > 12:
        return [(hour % 24, minute)]

    morning = (0 if hour == 12 else hour, minute)
    afternoon = (12 if hour == 12 else hour + 12, minute)

    if stated == "am":
        return [morning]

    if stated == "pm":
        return [afternoon]

    return [morning, afternoon]
