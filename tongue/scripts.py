"""WHICH LANGUAGE A PIECE OF TEXT IS IN, COUNTED OFF THE SHAPE OF ITS LETTERS."""

TELUGU = "te"
HINDI = "hi"
ENGLISH = "en"

BLOCKS = {
    TELUGU: ((0x0C00, 0x0C7F),),
    HINDI: ((0x0900, 0x097F),),
    ENGLISH: ((0x0041, 0x005A), (0x0061, 0x007A)),
}

# ONE ENGLISH WORD IN A LONG HINDI SENTENCE IS STILL HINDI. HALF AND HALF IS NOT.
CLEAR = 0.8

# THE SCRIPTS A PLAIN ENGLISH VOICE CANNOT READ, HARDEST FIRST, FOR reading() BELOW.
HARDEST = (TELUGU, HINDI)


def which(character):
    point = ord(character)

    for code, ranges in BLOCKS.items():
        if any(low <= point <= high for low, high in ranges):
            return code

    return None


def spelt(word):
    """THE LANGUAGE MOST OF ONE WORD IS SPELT IN, OR NOTHING IF IT IS ALL DIGITS."""
    seen = {}

    for character in word:
        code = which(character)

        if code:
            seen[code] = seen.get(code, 0) + 1

    return max(seen, key=seen.get) if seen else None


def tally(text):
    """HOW MANY WORDS OF EACH, NOT LETTERS: ENGLISH SPELLS THE SAME IDEA LONGER."""
    counts = {}

    for word in (text or "").split():
        code = spelt(word)

        if code:
            counts[code] = counts.get(code, 0) + 1

    return counts


def language(text):
    """THE ONE MOST OF IT IS WRITTEN IN."""
    counts = tally(text)

    return max(counts, key=counts.get) if counts else ENGLISH


def reading(text):
    """THE LANGUAGE WHOSE VOICE CAN READ ALL OF THIS, WHICH IS NOT ALWAYS MOST OF IT.

    ASKED TO READ A SCRIPT IT DOES NOT KNOW, A VOICE DOES NOT SKIP IT — IT SAYS THE NAME OF
    THE LANGUAGE OUT LOUD BEFORE EVERY LETTER. AN INDIAN VOICE HANDED AN ENGLISH WORD READS IT
    ANYWAY, SO ONE INDIAN WORD IN A MOSTLY ENGLISH SENTENCE DECIDES WHICH VOICE SPEAKS IT."""
    counts = tally(text)

    return next((code for code in HARDEST if counts.get(code)), ENGLISH)


def share(text):
    counts = tally(text)

    return max(counts.values()) / sum(counts.values()) if counts else 1.0


def mixed(text):
    """TWO LANGUAGES IN ONE SENTENCE, WHICH NOTHING TRAINED ON ONE OF THEM CAN WRITE."""
    return share(text) < CLEAR
