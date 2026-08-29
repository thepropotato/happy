"""THE WORD ITSELF: HOW IT MIGHT BE WRITTEN, WHAT LETTERS ARE IN IT, AND HOW
MANY. A MODEL IS HANDED WHOLE CHUNKS OF A WORD RATHER THAN ITS LETTERS, SO
COUNTING THEM OR SPELLING THEM OUT IS SOMETHING IT HAS TO ASK FOR."""

import re

from langchain_core.tools import tool

# HOW MANY ARE WORTH OFFERING BACK. PAST THIS IS NOISE, NOT HELP.
MOST = 10

SPLIT = re.compile(r"[\s_\-]+")


def variations(text):
    """EVERY LIKELY SPELLING OF text, ORIGINAL FIRST, NEVER REPEATED."""
    said = (text or "").strip()

    if not said:
        return []

    words = [word for word in SPLIT.split(said) if word]

    made = [
        said,
        said.lower(),
        said.upper(),
        said.title(),
        "_".join(words),
        "_".join(words).lower(),
        "-".join(words),
        "-".join(words).lower(),
        " ".join(words),
        "".join(words),
        "".join(words).lower(),
    ]

    seen, out = set(), []

    for each in made:
        if each and each not in seen:
            seen.add(each)
            out.append(each)

    return out[:MOST]


@tool
def word_variations(text: str) -> str:
    """Every likely spelling of one word or name, to try after an exact search
    for it came back with nothing. Give the exact word or phrase that failed,
    for example "website for venu" or "tax invoice 2026".

    Returns the other ways it might actually be written: upper case, lower
    case, title case, spaces swapped for underscores or hyphens, and with no
    spaces at all. Try the search again with each one in turn before telling
    the person nothing was found.

    Use this as a fallback after find_files, whatsapp_search_contacts, or any
    other tool that searches by name comes back empty. It only varies the
    name you search with — it does not search anything itself, and it is not
    specific to files or to any one tool."""
    said = variations(text)

    if not said:
        return "There was nothing to vary."

    return "\n".join(said)


# HOW MANY OF A LETTER IS WORTH LISTING WHERE THEY ARE. PAST THIS, THE COUNT IS THE ANSWER.
FEW = 6


def occurrences(text, letter):
    """EVERY PLACE letter SITS IN text, COUNTING FROM ONE, IGNORING CASE."""
    said = (text or "").strip()
    wanted = (letter or "").strip().lower()

    if not said or not wanted:
        return []

    return [spot for spot, each in enumerate(said, 1) if each.lower() == wanted]


def placing(spots):
    """WHERE THEY ARE, SAID THE WAY A PERSON SAYS IT OUT LOUD."""
    said = [ORDINALS.get(spot, f"{spot}th") for spot in spots]

    if len(said) == 1:
        return said[0]

    return f"{', '.join(said[:-1])} and {said[-1]}"


ORDINALS = {
    1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth", 7: "seventh",
    8: "eighth", 9: "ninth", 10: "tenth", 11: "eleventh", 12: "twelfth",
}

COUNTS = {
    0: "no", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
    8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve",
}


def counted(number):
    return COUNTS.get(number, str(number))


@tool
def count_letters(text: str, letter: str) -> str:
    """How many times one letter appears in a word or phrase, and where. Give
    the word exactly as it was said, for example "strawberry", and the single
    letter to count, for example "r".

    Call this every time you are asked how many of a letter are in something,
    whether a word is spelled a certain way, or which letter comes at some
    position. You cannot see the letters in a word by yourself and you will
    get it wrong, so never count them in your head and never answer from what
    the word looks like to you. Case is ignored, so "R" and "r" are the same
    letter.

    Returns the count and, when there are only a few, which positions they sit
    in. Say the number back the way a person says it out loud."""
    said = (text or "").strip()
    wanted = (letter or "").strip()

    if not said:
        return "There was no word to count in."

    if len(wanted) != 1:
        return "Give one single letter to count."

    spots = occurrences(said, wanted)
    many = counted(len(spots))

    if not spots:
        return f"There is no {wanted.lower()} in {said}."

    if len(spots) > FEW:
        return f"There are {many} {wanted.lower()}s in {said}."

    where = placing(spots)
    plural = "" if len(spots) == 1 else "s"
    verb = "is" if len(spots) == 1 else "are"

    return (
        f"There {verb} {many} {wanted.lower()}{plural} in {said}, "
        f"at the {where} letter{plural}."
    )


@tool
def spell_word(text: str) -> str:
    """The letters of a word one at a time, in order, for when you need to see
    how something is actually written. Give the word exactly as it was said,
    for example "strawberry".

    Call this when you are asked to spell something out, how long a word is,
    what it reads like backwards, or anything else about the letters
    themselves. You cannot see the letters in a word by yourself, so never
    spell one out from what it looks like to you.

    Returns each letter separated by spaces, and how many there are."""
    said = (text or "").strip()

    if not said:
        return "There was no word to spell."

    letters = " ".join(said)

    return f"{said} is spelled {letters}, and it has {counted(len(said))} letters."


TOOLS = [word_variations, count_letters, spell_word]