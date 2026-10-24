"""Whether speech was said to Happy: its name first, perhaps after a greeting, never just in passing."""

import difflib
import re

GREETINGS = {"hey", "hi", "ok", "okay", "yo", "hello", "oi", "oh", "um", "uh", "so", "and", "ah", "hay", "a"}


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
        if all(b in GREETINGS or b == "," for b in before):
            rest = text.split(word, 1)[1] if word in text else ""
            return rest.lstrip(" ,.!?;:-").strip()
    return None
