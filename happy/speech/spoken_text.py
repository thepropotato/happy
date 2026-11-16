"""Turns written replies into words worth saying: no URLs, markdown or symbols read out."""

import re
from urllib.parse import urlparse

SITES = {
    "youtube": "YouTube", "youtu": "YouTube", "github": "GitHub", "google": "Google", "gmail": "Gmail",
    "whatsapp": "WhatsApp", "linkedin": "LinkedIn", "x": "X", "twitter": "Twitter", "reddit": "Reddit",
    "wikipedia": "Wikipedia", "amazon": "Amazon", "stackoverflow": "Stack Overflow", "claude": "Claude",
    "anthropic": "Anthropic", "openai": "OpenAI", "netflix": "Netflix", "spotify": "Spotify",
}

URL = re.compile(r"(?:https?://|www\.)[^\s<>()\[\]]+[^\s<>()\[\].,;:!?'\"]")
EMAIL = re.compile(r"\b([\w.+-]+)@([\w-]+(?:\.[\w-]+)+)\b")
PATH = re.compile(r"(?<![\w.])(?:~|/(?:Users|home|Applications|Volumes|tmp|var|opt)|[A-Z]:\\)[^\s,;:!?'\"]*[^\s,;:!?'\".)]")
CLOCK = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b(?:\s*([AaPp]\.?[Mm]\.?)(?![a-z]))?")
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")


def site_of(url):
    host = urlparse(url if "://" in url else "https://" + url).netloc.lower().removeprefix("www.")
    parts = host.split(".")
    core = parts[-2] if len(parts) >= 2 else parts[0]
    return SITES.get(core, core.capitalize() if core else "")


def say_url(match, text):
    before = text[max(0, match.start() - 40):match.start()].lower()
    if "link" in before:
        return ""
    site = site_of(match.group(0))
    return f"a link to {site}" if site else "a link"


def say_path(path):
    name = re.split(r"[\\/]", path.rstrip("/\\"))[-1] or "home"
    if name == "~":
        return "your home folder"
    if "." in name[1:]:
        stem, ext = name.rsplit(".", 1)
        return f"{stem.replace('_', ' ').replace('-', ' ')} {ext.upper() if len(ext) <= 4 else ext}"
    return f"the {name.replace('_', ' ').replace('-', ' ')} folder"


ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
        "seventeen eighteen nineteen").split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
SCALES = ((10**12, "trillion"), (10**9, "billion"), (10**6, "million"), (1000, "thousand"))
NUMBER = re.compile(r"(?<![\w.,/:+#-])(\d{1,3}(?:,\d{2,3})*,\d{3}|\d+)(?:\.(\d+))?(?![\w/]|[.,:]\d)")
MONTHS = "january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
BEFORE_A_YEAR = re.compile(rf"(?:\b(?:in|since|during|until|till|from|year|circa|{MONTHS})|\b(?:{MONTHS})\.? \d{{1,2}}(?:st|nd|rd|th)?,?) $", re.I)
MONEY = re.compile(r"\s(?:dollars|rupees|euros|pounds)\b")


def in_words(number):
    """A whole number in words."""
    if number < 20:
        return ONES[number]
    if number < 100:
        return TENS[number // 10] + (f" {ONES[number % 10]}" if number % 10 else "")
    if number < 1000:
        return f"{ONES[number // 100]} hundred" + (f" and {in_words(number % 100)}" if number % 100 else "")
    size, name = next(scale for scale in SCALES if number >= scale[0])
    rest = number % size
    return f"{in_words(number // size)} {name}" + (f"{' and' if rest < 100 else ''} {in_words(rest)}" if rest else "")


def in_pairs(number):
    """A year as it is said, in two pairs of digits."""
    high, low = divmod(number, 100)
    if 2000 <= number < 2010:
        return in_words(number)
    return f"{in_words(high)} hundred" if not low else f"{in_words(high)} oh {ONES[low]}" if low < 10 else f"{in_words(high)} {in_words(low)}"


def say_number(match):
    """A number written out, because the voice drops digits from bare ones."""
    written, decimals = match.group(1), match.group(2)
    digits = written.replace(",", "")
    if decimals is None and "," not in written and (len(digits) >= 7 or (len(digits) >= 3 and digits[0] == "0")):
        return " ".join(ONES[int(d)] for d in digits)
    if decimals is None and len(digits) == 4 and 1000 <= int(digits) < 2100 and BEFORE_A_YEAR.search(match.string[:match.start()]):
        return in_pairs(int(digits))
    whole = in_words(int(digits))
    if decimals is None:
        return whole
    if len(decimals) == 2 and MONEY.match(match.string[match.end():]):
        return whole if decimals == "00" else f"{whole} oh {ONES[int(decimals[1])]}" if decimals[0] == "0" else f"{whole} {in_words(int(decimals))}"
    return f"{whole} point {' '.join(ONES[int(d)] for d in decimals)}"


def markdown_out(text):
    text = re.sub(r"```.*?```", " (the code is on screen) ", text, flags=re.S)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\((?:[^)]+)\)", r"\1", text)
    text = re.sub(r"(\*\*|__|\*|_)(?=\S)(.+?)(?<=\S)\1", r"\2", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*\|.*\|\s*$", "", text, flags=re.M)
    text = re.sub(r"^\s*(?:[-*•]|\d{1,2}[.)])\s+(.*?)\s*$", lambda m: m.group(1).rstrip(".") + ".", text, flags=re.M)
    return text


def say_clock(match):
    """A clock time the way it is said: a leading zero minute is "oh", and a whole hour is just the hour."""
    hour, minute, half = match.group(1), match.group(2), (match.group(3) or "").replace(".", "")
    spoken = hour if minute == "00" and half else f"{hour} o'clock" if minute == "00" else f"{hour} oh {minute[1]}" if minute[0] == "0" else f"{hour} {minute}"
    return f"{spoken} {half.upper()}".strip()


def speakable(text):
    text = markdown_out(text)
    text = URL.sub(lambda m: say_url(m, text), text)
    text = EMAIL.sub(lambda m: f"{m.group(1).replace('.', ' dot ')} at {m.group(2).replace('.', ' dot ')}", text)
    text = PATH.sub(lambda m: say_path(m.group(0)), text)
    text = EMOJI.sub("", text)
    text = CLOCK.sub(say_clock, text)
    text = re.sub(r"(\d)\s*%", r"\1 percent", text)
    text = re.sub(r"[$]\s?(\d[\d,.]*)", r"\1 dollars", text)
    text = re.sub(r"₹\s?(\d[\d,.]*)", r"\1 rupees", text)
    text = re.sub(r"€\s?(\d[\d,.]*)", r"\1 euros", text)
    text = re.sub(r"£\s?(\d[\d,.]*)", r"\1 pounds", text)
    text = re.sub(r"(\d)\s*°\s*C\b", r"\1 degrees", text)
    text = re.sub(r"\s*(?:->|→|=>)\s*", " to ", text)
    text = re.sub(r"\s&\s", " and ", text)
    text = re.sub(r"(\d)\s*-\s*(\d)", r"\1 to \2", text)
    text = NUMBER.sub(say_number, text)
    text = re.sub(r"\be\.g\.", "for example", text)
    text = re.sub(r"\bi\.e\.", "that is", text)
    text = re.sub(r"\betc\.", "and so on", text)
    text = text.replace("—", ", ").replace("–", ", ").replace("…", "...")
    text = re.sub(r"[*#_|<>{}\[\]\\^~]", " ", text)
    # QUOTE MARKS ARE SILENT, AND AROUND A STRETCHED WORD THEY MADE THE VOICE SAY "OKIEE OKIE" AS THREE OKIES.
    text = re.sub(r"[\"“”„«»]", "", text)
    # A STRETCHED WORD IS SAID ONCE: "Bruuu" IS "Bru". LOWERCASE ONLY, SO "III" STAYS A NUMBER.
    text = re.sub(r"([a-z])\1{2,}", r"\1", text)
    text = re.sub(r"\s*:\s*$", ".", text, flags=re.M)
    text = re.sub(r"\s+([.,!?])", r"\1", text)
    text = re.sub(r"([.,!?])\1+", r"\1", text)
    return re.sub(r"\s+", " ", text).strip(" ,")


ABBREVIATIONS = ("mr.", "mrs.", "ms.", "dr.", "st.", "vs.", "no.", "e.g.", "i.e.", "etc.", "approx.", "jan.", "feb.",
                 "mar.", "apr.", "jun.", "jul.", "aug.", "sep.", "sept.", "oct.", "nov.", "dec.")


class Sentences:
    """Collects streamed text and hands back whole sentences as soon as they are finished."""

    def __init__(self):
        self.buffer = ""
        self.first = True

    def add(self, delta):
        self.buffer += delta
        out = []
        while True:
            cut = self.boundary()
            if cut is None:
                break
            piece, self.buffer = self.buffer[:cut], self.buffer[cut:]
            if piece.strip():
                out.append(piece.strip())
                self.first = False
        return out

    def boundary(self):
        text = self.buffer
        for match in re.finditer(r"[.!?](?=\s)|\n+", text):
            end = match.end()
            word = text[:end].rsplit(None, 1)[-1].lower() if text[:end].split() else ""
            if word in ABBREVIATIONS:
                continue
            if URL.search(text[max(0, end - 60):end + 1]) and not text[end:end + 1].isspace():
                continue
            if len(text[:end].strip()) < (8 if self.first else 20) and match.group(0)[0] != "\n":
                continue
            return end
        if self.first and len(text) > 140:
            comma = text.rfind(", ", 40, 140)
            if comma > 0:
                return comma + 1
        return None

    def rest(self):
        piece, self.buffer = self.buffer.strip(), ""
        return [piece] if piece else []
