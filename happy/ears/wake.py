"""Whether speech was said to Happy: its name first, perhaps after a greeting, never just in passing."""

import re

GREETINGS = {"hey", "hi", "ok", "okay", "yo", "hello", "oi", "oh", "um", "uh", "so", "and", "ah", "hay", "a"}


def addressed(text, name):
    """The request that follows the name, or None when the name was only used in passing."""
    words = re.findall(r"[\w']+|[.,!?;]", text)
    target = name.lower()
    for i, word in enumerate(words):
        if word.lower().strip("'") not in (target, target + "s", target + "'s"):
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
