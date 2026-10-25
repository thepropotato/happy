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


def markdown_out(text):
    text = re.sub(r"```.*?```", " (the code is on screen) ", text, flags=re.S)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\((?:[^)]+)\)", r"\1", text)
    text = re.sub(r"(\*\*|__|\*|_)(?=\S)(.+?)(?<=\S)\1", r"\2", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*\|.*\|\s*$", "", text, flags=re.M)
    text = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s+(.*?)\s*$", lambda m: m.group(1).rstrip(".") + ".", text, flags=re.M)
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
    text = re.sub(r"\be\.g\.", "for example", text)
    text = re.sub(r"\bi\.e\.", "that is", text)
    text = re.sub(r"\betc\.", "and so on", text)
    text = text.replace("—", ", ").replace("–", ", ").replace("…", "...")
    text = re.sub(r"[*#_|<>{}\[\]\\^~]", " ", text)
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
