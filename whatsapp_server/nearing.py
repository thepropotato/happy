"""THE SAVED NAMES CLOSEST TO ONE THAT MATCHED NOTHING."""

import difflib
import re

CLOSE = 0.75

MOST = 3


def words(name):
    return [each for each in re.findall(r"[a-z0-9]+", str(name or "").lower()) if len(each) > 1]


def squeeze(word):
    """A WORD AS IT SOUNDS: "-ie", "-y", "-ee", "-ey" ENDINGS MADE ALIKE AND A RUN OF ONE LETTER CUT TO ONE, SO "jonnie" AND "jonny" MATCH."""
    return re.sub(r"(.)\1+", r"\1", re.sub(r"(?:ie|ee|ey|y)$", "i", word))


def sounds(word):
    """A WORD AS IT IS SAID, SO TWO SPELLINGS OF ONE NAME COME OUT THE SAME."""
    said = word.lower()
    for written, heard in (("ph", "f"), ("sh", "s"), ("th", "t"), ("dh", "d"), ("bh", "b"), ("kh", "k"), ("gh", "g"), ("ck", "k"),
                           ("q", "k"), ("w", "v"), ("z", "j"), ("ee", "i"), ("oo", "u"), ("ou", "u")):
        said = said.replace(written, heard)
    said = re.sub(r"c(?!h)", "k", said)
    said = re.sub(r"(?:ie|ey)$", "i", said).replace("y", "i")
    said = re.sub(r"(?<=[aeiou])h(?=[^aeiou])", "", said)
    return re.sub(r"(.)\1+", r"\1", re.sub(r"([aeiou])[aeiou]+", r"\1", said))


def alike(asked, name):
    """0 WHEN EVERY WORD ASKED IS SAID LIKE A WORD OF THE NAME, 1 WHEN EVERY WORD ONLY STARTS ONE, ELSE None."""
    said, saved = [sounds(w) for w in words(asked)], [sounds(w) for w in words(name)]
    if not said or not saved:
        return None
    if all(word in saved for word in said):
        return 0
    if all(len(word) >= 3 and any(other.startswith(word) for other in saved) for word in said):
        return 1
    return None


def inside(one, other):
    """HOW WELL one MATCHES THE BEST STRETCH OF other, FOR A NAME HIDDEN IN A LONGER ONE LIKE "notjane"."""
    if len(other) <= len(one) or len(one) < 4:
        return 0.0
    return max(difflib.SequenceMatcher(None, one, other[i:i + len(one)]).ratio() for i in range(len(other) - len(one) + 1))


def likeness(asked, name):
    said, saved = [squeeze(w) for w in words(asked)], [squeeze(w) for w in words(name)]

    if not said or not saved:
        return 0.0

    whole = difflib.SequenceMatcher(None, " ".join(said), " ".join(saved)).ratio()

    # A NAME SAID WITH EXTRA WORDS AROUND IT STILL HOLDS EVERY WORD OF THE SAVED ONE.
    each = sum(max(difflib.SequenceMatcher(None, one, other).ratio() for one in said) for other in saved)

    within = max(inside(one, other) for one in said for other in saved)

    return max(whole, each / len(saved), within)


def nearest(asked, names, most=MOST):
    """UP TO most SAVED NAMES THAT LOOK LIKE asked, CLOSEST FIRST; A NAME MAY BE (WHAT TO MATCH, WHAT TO SHOW)."""
    kept = {}
    for name in names:
        matched, shown = name if isinstance(name, tuple) else (name, name)
        if matched and not str(matched).lstrip("+").isdigit():
            kept[str(shown).strip()] = max(kept.get(str(shown).strip(), 0.0), likeness(asked, str(matched)))
    scored = sorted(((score, shown) for shown, score in kept.items()), reverse=True)

    return [shown for score, shown in scored if score >= CLOSE][:most]


def missed(asked, close):
    """WHAT A FAILED LOOKUP SAYS, WITH THE NAMES IT COULD HAVE MEANT."""
    if not close:
        return f"No contact matching '{asked}' was found, so nothing was read, and no saved name is close to it."

    # A PERSON IS (NAME, PROFILE NAME); THE NAME IN QUOTES IS THE ONE TO CALL AGAIN WITH, THE PROFILE ONLY SAYS WHO IT IS.
    named = ", ".join(f"'{name}' (WhatsApp profile name {profile})" if profile else f"'{name}'"
                      for name, profile in (each if isinstance(each, tuple) else (each, "") for each in close))
    closest = f"The closest saved name is {named}" if len(close) == 1 else f"The closest saved names are {named}"

    return (
        f"No contact matching '{asked}' was found, so nothing was read. {closest}. "
        "If one is plainly the same person said differently, call again with it. "
        "If not, ask them which they meant, naming these."
    )
