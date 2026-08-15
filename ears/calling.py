"""HIS NAME, AND WHETHER THIS LINE WAS SAID TO HIM."""

import difflib
import re

from memory import settings

PHRASE = "ears.wake"

FALLBACK = "hey happy, happy"

# HOW CLOSE A MISHEARD WORD STILL COUNTS AS THAT WORD, AND HOW CLOSE THE LAST ONE HAS TO BE.
EACH_CLOSE = 0.55
NAME_CLOSE = 0.8

# EVERY LANGUAGE'S WORDS, SO A PHRASE SOMEBODY SET IN THEIR OWN SCRIPT STILL SPLITS INTO
# ONES.
WORDS = re.compile(r"\w+", re.UNICODE)


def phrases():
    """EVERY NAME HE ANSWERS TO, LONGEST FIRST SO "hey happy" IS TRIED BEFORE "happy"."""
    said = settings.get(PHRASE) or FALLBACK
    found = [split(each) for each in said.split(",")]

    kept = [each for each in found if each]

    return sorted(kept or [split(FALLBACK.split(",")[0])], key=len, reverse=True)


def addressed(text, wanted=None):
    """WHAT FOLLOWS HIS NAME IN THIS LINE, OR None WHEN HIS NAME IS NOT IN IT."""
    found = list(WORDS.finditer(text or ""))

    if not found:
        return None

    for name in wanted or phrases():
        rest = following(text, found, name)

        if rest is not None:
            return rest

    return None


def following(text, found, wanted):
    """WHAT IS LEFT AFTER THIS ONE NAME, OR None WHEN IT IS NOT IN THE LINE."""
    if len(found) < len(wanted):
        return None

    # A NAME OF ONE WORD IS A WORD PEOPLE SAY IN ORDINARY SENTENCES, SO IT ONLY
    # COUNTS WHERE A PERSON ADDRESSING HIM WOULD PUT IT: AT THE VERY FRONT.
    most = 1 if len(wanted) == 1 else len(found) - len(wanted) + 1

    for at in range(most):
        run = [each.group().lower() for each in found[at : at + len(wanted)]]

        if says(run, wanted):
            # ONLY OFF THE FRONT: THE QUESTION MARK AT THE END IS PART OF THE QUESTION.
            return text[found[at + len(wanted) - 1].end() :].lstrip(" ,.!?:;-").strip()

    return None


def says(run, wanted):
    """WHETHER THIS RUN OF WORDS IS SOMEBODY SAYING THAT NAME."""
    if run == wanted:
        return True

    last = len(wanted) - 1

    for at, (said, word) in enumerate(zip(run, wanted)):
        if near(said, word) < (NAME_CLOSE if at == last else EACH_CLOSE):
            return False

    return True


def near(said, name):
    return difflib.SequenceMatcher(None, said, name).ratio()


def split(text):
    return WORDS.findall((text or "").lower())


def spoken():
    """THE NAMES AS THEY WERE WRITTEN, FOR SOMETHING THAT HAS TO SAY THEM."""
    return " or ".join(" ".join(each) for each in phrases())
