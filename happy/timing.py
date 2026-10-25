"""Spoken times worked out in code, never by the model: "at four", "in ten minutes", "every weekday at nine"."""

import re
from datetime import datetime, timedelta

NUMBERS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
           "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40,
           "forty five": 45, "fifty": 50, "sixty": 60, "ninety": 90, "couple of": 2, "a couple of": 2, "few": 3, "a few": 3}
UNITS = {"second": 1, "sec": 1, "minute": 60, "min": 60, "hour": 3600, "hr": 3600, "day": 86400, "week": 604800}
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]
# WHAT A PART OF THE DAY MEANS WHEN NO HOUR IS SAID, AND WHICH HALF OF THE CLOCK IT PUTS AN HOUR IN.
PARTS = {"morning": (9, "am"), "afternoon": (15, "pm"), "evening": (18, "pm"), "night": (20, "pm"), "tonight": (20, "pm")}
COUNT = r"(?P<n>\d+|" + "|".join(sorted(map(re.escape, NUMBERS), key=len, reverse=True)) + r")"
UNIT = r"(?P<unit>second|sec|minute|min|hour|hr|day|week)s?"


class Unclear(ValueError):
    """A time the words do not pin down, with what to say instead."""


def count(word):
    word = word.strip()
    return int(word) if word.isdigit() else NUMBERS[word]


def clock(text):
    """(hour, minute, half) for a time of day in the words, half being 'am', 'pm' or '' when unsaid."""
    if re.search(r"\bnoon\b|\bmidday\b", text):
        return 12, 0, "pm"
    if re.search(r"\bmidnight\b", text):
        return 0, 0, "am"
    words = r"\d+|" + "|".join(k for k in NUMBERS if " " not in k and NUMBERS[k] <= 12)
    match = re.search(rf"\b(?P<rel>half|quarter|\d+) (?P<dir>past|to) (?P<h>{words})\b", text)
    if match:
        hour = count(match["h"])
        minutes = {"half": 30, "quarter": 15}.get(match["rel"]) or int(match["rel"])
        hour, minute = (hour, minutes) if match["dir"] == "past" else (hour - 1, 60 - minutes)
        return hour % 24, minute, half_in(text)
    match = re.search(r"(?:\bat |^|\b)(?P<h>\d{1,2})(?:[:.](?P<m>\d{2}))? ?(?P<half>a\.?m\.?|p\.?m\.?|o'?clock)?(?=\W|$)", text)
    if match and (match["m"] or match["half"] or re.search(rf"\bat {match['h']}\b|\bby {match['h']}\b", text)):
        half = (match["half"] or "").replace(".", "")
        return int(match["h"]), int(match["m"] or 0), half if half in ("am", "pm") else half_in(text)
    match = re.search(rf"\bat (?P<h>{words})(?: (?P<half>am|pm|o'?clock))?\b", text)
    if match:
        half = match["half"] or ""
        return count(match["h"]), 0, half if half in ("am", "pm") else half_in(text)
    return None


def half_in(text):
    for part, (_, half) in PARTS.items():
        if re.search(rf"\b{part}\b", text):
            return half
    return ""


def day_named(text, now):
    """The date a day word names, or None: today, tomorrow, a weekday, or a date."""
    if re.search(r"\bday after tomorrow\b", text):
        return (now + timedelta(days=2)).date()
    if re.search(r"\btomorrow\b", text):
        return (now + timedelta(days=1)).date()
    if re.search(r"\btoday\b|\btonight\b|\bthis (?:morning|afternoon|evening)\b", text):
        return now.date()
    match = re.search(rf"\b(?:next |this |on )?(?P<day>{'|'.join(DAYS)})\b", text)
    if match:
        # "NEXT FRIDAY" MEANS DIFFERENT THINGS TO DIFFERENT PEOPLE; THE SOONEST FRIDAY IS SAID BACK SO IT CAN BE CORRECTED.
        ahead = (DAYS.index(match["day"]) - now.weekday()) % 7 or 7
        return (now + timedelta(days=ahead)).date()
    months = "|".join(MONTHS + [m[:3] for m in MONTHS])
    match = (re.search(rf"\b(?P<d>\d{{1,2}})(?:st|nd|rd|th)? (?:of )?(?P<mon>{months})\b", text)
             or re.search(rf"\b(?P<mon>{months}) (?:the )?(?P<d>\d{{1,2}})(?:st|nd|rd|th)?\b", text))
    if match:
        month = next(i for i, m in enumerate(MONTHS, 1) if m.startswith(match["mon"][:3]))
        for year in (now.year, now.year + 1):
            try:
                when = datetime(year, month, int(match["d"])).date()
            except ValueError:
                raise Unclear(f"{match['mon'].title()} has no {match['d']}") from None
            if when >= now.date():
                return when
    match = re.search(r"\bthe (?P<d>\d{1,2})(?:st|nd|rd|th)\b", text)
    if match:
        day = int(match["d"])
        for ahead in range(0, 3):
            month, year = (now.month + ahead - 1) % 12 + 1, now.year + (now.month + ahead - 1) // 12
            try:
                when = datetime(year, month, day).date()
            except ValueError:
                continue
            if when >= now.date():
                return when
    return None


def placed(hour, minute, half, on, now, explicit_day):
    """The moment an hour means: a stated half as said, otherwise the soonest future one, or the likely one on a named day."""
    if half == "pm" and hour < 12:
        hour += 12
    elif half == "am" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        raise Unclear(f"{hour}:{minute:02d} is not a time of day")
    base = datetime.combine(on, datetime.min.time())
    if half or hour > 12 or hour == 0:
        moment = base.replace(hour=hour, minute=minute)
        return moment + timedelta(days=1) if moment <= now and not explicit_day else moment
    if explicit_day and on != now.date():
        # ON ANOTHER DAY THERE IS NO "SOONEST", SO ONE TO SIX IS THE AFTERNOON AND SEVEN TO ELEVEN THE MORNING.
        return base.replace(hour=hour + 12 if 1 <= hour <= 6 else hour, minute=minute)
    for candidate in (base.replace(hour=hour % 12, minute=minute), base.replace(hour=hour % 12 + 12, minute=minute)):
        if candidate > now:
            return candidate
    return (base + timedelta(days=1)).replace(hour=hour % 12, minute=minute)


def repeat(text, now):
    """A recurring rule in the words, as (rule, first due), or None for a one-off."""
    match = re.search(rf"\bevery {COUNT} {UNIT}\b|\bevery (?P<unit1>second|minute|hour|day|week)\b|\b(?P<ly>hourly|daily|weekly)\b", text)
    weekdays = re.search(r"\b(?:every|on) weekdays?\b|\bevery working day\b", text)
    weekends = re.search(r"\b(?:every|on) weekends?\b", text)
    named = re.findall(rf"\bevery ((?:{'|'.join(DAYS)})(?:s)?(?:(?:,| and|,? and) (?:{'|'.join(DAYS)})s?)*)", text)
    part = re.search(r"\bevery (morning|afternoon|evening|night)\b", text)
    if re.search(r"\bevery (?:month|year)\b|\bmonthly\b|\byearly\b", text):
        raise Unclear("monthly and yearly reminders are not something I can set yet; set it for a day and time")
    if not (match or weekdays or weekends or named or part):
        return None
    unit = (match and (match["unit"] or match["unit1"] or {"hourly": "hour", "daily": "day", "weekly": "week"}.get(match["ly"]))) or None
    if unit in ("second", "sec", "minute", "min", "hour", "hr"):
        step = count(match["n"]) * UNITS[unit] if match["n"] else UNITS[unit]
        if step < 60:
            raise Unclear("that is more often than once a minute")
        return {"every": step}, now + timedelta(seconds=step)
    if weekdays:
        days = [0, 1, 2, 3, 4]
    elif weekends:
        days = [5, 6]
    elif named:
        days = sorted({DAYS.index(d) for d in re.findall("|".join(DAYS), named[0])})
    elif unit == "week":
        days = [now.weekday()]
    else:
        days = list(range(7))
    said = clock(text)
    if said:
        hour, minute, half = said
        hour += 12 if (half == "pm" and hour < 12) else 0
        hour = 0 if half == "am" and hour == 12 else hour
        if not half and 1 <= hour <= 6:
            hour += 12
    elif part:
        hour, minute = PARTS[part[1]][0], 0
    elif unit == "week":
        hour, minute = now.hour, now.minute
    else:
        hour, minute = 9, 0
    rule = {"days": days, "at": f"{hour:02d}:{minute:02d}"}
    return rule, following(rule, now)


def following(rule, after):
    """When a rule comes round next, strictly after a moment; wall clock, so eight stays eight across a clock change."""
    if "every" in rule:
        return after + timedelta(seconds=rule["every"])
    hour, minute = map(int, rule["at"].split(":"))
    for ahead in range(0, 8):
        day = after + timedelta(days=ahead)
        candidate = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if day.weekday() in rule["days"] and candidate > after:
            return candidate
    raise Unclear("that rule never comes round")


def when(text, now=None):
    """(the first moment, the repeat rule or None) for spoken words, or Unclear saying what to say instead."""
    now = (now or datetime.now()).replace(microsecond=0)
    # A MODEL THAT WORKED THE MOMENT OUT ITSELF HANDS IT OVER AS ISO, WHICH NEEDS NO READING.
    if re.fullmatch(r"\s*\d{4}-\d{2}-\d{2}[t ]\d{2}:\d{2}(?::\d{2})?\s*", text, re.I):
        moment = datetime.fromisoformat(text.strip().upper().replace(" ", "T"))
        if moment <= now:
            raise Unclear("that time has already gone")
        return moment, None
    text = " ".join(text.lower().replace(",", " ").replace("-", " ").split())
    text = re.sub(r"^(?:remind me |set (?:it|a reminder) )", "", text)
    rule = repeat(text, now)
    if rule:
        return rule[1], rule[0]
    if re.search(r"\bhalf an hour\b", text):
        return now + timedelta(minutes=30), None
    match = (re.search(rf"\b(?:in|after) (?:another )?{COUNT} {UNIT}(?: and a half)?\b", text)
             or re.search(rf"\b{COUNT} {UNIT} from now\b", text))
    if match:
        unit = match["unit"]
        seconds = count(match["n"]) * UNITS[unit] * (1.5 if "and a half" in match.group(0) else 1)
        return now + timedelta(seconds=seconds), None
    match = re.search(rf"\b(?:in|after) (?:an?|one) {UNIT}\b", text)
    if match:
        return now + timedelta(seconds=UNITS[match["unit"]]), None
    on = day_named(text, now)
    said = clock(text)
    if said:
        moment = placed(*said, on or now.date(), now, explicit_day=on is not None)
    elif on or half_in(text):
        part = next((p for p in PARTS if re.search(rf"\b{p}\b", text)), None)
        hour = PARTS[part][0] if part else 9
        moment = datetime.combine(on or now.date(), datetime.min.time()).replace(hour=hour)
        if moment <= now and not on:
            moment += timedelta(days=1)
    else:
        raise Unclear("say when, like 'at four', 'in ten minutes', 'tomorrow at nine' or 'every weekday at eight'")
    if moment <= now:
        raise Unclear(f"{spoken(moment, now)} has already gone")
    return moment, None


def spoken(moment, now=None):
    """'4:30 PM today', 'tomorrow at 9 AM', 'Friday 30 October at 4 PM'."""
    now = now or datetime.now()
    hour = moment.strftime("%I:%M %p").lstrip("0").replace(":00 ", " ")
    if moment.date() == now.date():
        return f"{hour} today"
    if moment.date() == (now + timedelta(days=1)).date():
        return f"tomorrow at {hour}"
    if 0 < (moment.date() - now.date()).days < 7:
        return f"{moment.strftime('%A')} at {hour}"
    return f"{moment.strftime('%A')} {moment.day} {moment.strftime('%B')} at {hour}"


def spoken_rule(rule):
    if "every" in rule:
        step = rule["every"]
        if step % 3600 == 0:
            return "every hour" if step == 3600 else f"every {step // 3600} hours"
        return f"every {step // 60} minutes"
    hour = datetime.strptime(rule["at"], "%H:%M").strftime("%I:%M %p").lstrip("0").replace(":00 ", " ")
    days = rule["days"]
    named = {(0, 1, 2, 3, 4, 5, 6): "every day", (0, 1, 2, 3, 4): "every weekday", (5, 6): "every weekend day"}
    which = named.get(tuple(days)) or "every " + " and ".join(DAYS[d].title() for d in days)
    return f"{which} at {hour}"
