"""Whether speech was said to Happy: its name first, perhaps after a greeting, never just in passing."""

import difflib
import re

GREETINGS = {"hey", "hi", "ok", "okay", "yo", "hello", "oi", "oh", "um", "uh", "so", "and", "ah", "hay", "a"}
OPENERS = {"open", "close", "quit", "pause", "play", "resume", "stop", "set", "turn", "mute", "unmute", "lock", "find",
           "search", "read", "send", "tell", "text", "message", "reply", "email", "show", "go", "take", "check", "start",
           "make", "give", "remind", "help", "put", "switch", "skip", "next", "call", "what", "whats", "what's",
           "who", "where", "when", "why", "how", "is", "are", "do", "does", "did", "can", "could", "would", "will",
           "please", "i", "i'm", "my", "write", "build", "fix", "summarise", "summarize", "volume", "brightness"}


def skeleton(word):
    """The consonants of a word in order, which is what survives a mis-heard vowel."""
    return word[:1] + re.sub(r"(.)\1+", r"\1", re.sub(r"[aeiouyhw']", "", word[1:]))


def sounds_like(word, name):
    word, name = word.lower().strip("'"), name.lower()
    for ending in ("'s", "s"):
        if word.endswith(ending) and word[: -len(ending)] == name:
            return True
    if word == name:
        return True
    return skeleton(word) == skeleton(name) and difflib.SequenceMatcher(None, word, name).ratio() >= 0.6


def opens(word):
    """Whether a word starts a request, allowing for a word heard only in part, like 'closing' for 'close'."""
    word = word.lower()
    return word in OPENERS or len(word) >= 4 and any(len(o) >= 4 and word[:4] == o[:4] for o in OPENERS)


def mentions(text, name, within=3):
    """Whether the name is among the first few words, said to Happy or not."""
    return any(sounds_like(w, name) for w in re.findall(r"[\w']+", text)[:within])


def addressed(text, name):
    """The request that follows the name, or None when the name was only used in passing."""
    words = re.findall(r"[\w']+|[.,!?;]", text)
    for i, word in enumerate(words):
        if not sounds_like(word, name):
            continue
        before = []
        for prior in reversed(words[:i]):
            if prior in ".!?":
                break
            before.append(prior.lower())
        if not all(b in GREETINGS or b == "," for b in before):
            continue
        after = words[i + 1] if i + 1 < len(words) else ""
        greeted = any(b in GREETINGS for b in before)
        if greeted or not after or after in ",.!?;" or after.lower() in GREETINGS or opens(after):
            lead, rest = text.split(word, 1) if word in text else (text, "")
            rest = rest.lstrip(" ,.!?;:-").strip()
            if not greeted:
                return rest
            # A GREETING IS KEPT: SAID ALONE IT IS ANSWERED WHOLE, AND BEFORE A REQUEST ONLY THE NAME IS DROPPED.
            return f"{lead.strip(' ,')}, {rest}" if rest else text.strip()
    return None
