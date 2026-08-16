"""WORDS TURNED INTO THE SOUNDS THEY ARE MADE OF, WHICH IS WHAT A VOICE MODEL READS."""

# espeak-ng HAS ITS OWN NAME FOR A LANGUAGE, WHICH IS NOT THE TWO LETTERS EVERYTHING ELSE USES.
SPELLING = {"en": "en-us", "hi": "hi", "te": "te"}

# THE MODEL READS NO MORE THAN THIS AT ONCE, AND ITS STYLES ARE ONLY WRITTEN OUT THAT FAR.
LIMIT = 500

# NOTHING IS HEARD UNTIL A MOUTHFUL IS FINISHED, AND THE MODEL COSTS A TENTH OF A SECOND FLAT
# PLUS ANOTHER PER TWO HUNDRED SOUNDS, SO THE FIRST ONE IS CUT SHORT AND THE REST ARE NOT.
FIRST = 40

# UNDER THIS A SENTENCE IS SAID IN ONE GO: THE JOIN WOULD COST MORE THAN THE WAIT IT SAVES.
WHOLE = 80

# A LONG SENTENCE IS BROKEN WHERE A PERSON WOULD BREATHE, NEVER IN THE MIDDLE OF A WORD.
BREAKS = ".,!?;:"

started = False


def start():
    """POINT THE PHONEMISER AT THE espeak-ng THAT CAME IN THE WHEEL, NOT ONE INSTALLED BY HAND."""
    global started

    if started:
        return

    import espeakng_loader
    from phonemizer.backend.espeak.wrapper import EspeakWrapper

    EspeakWrapper.set_data_path(espeakng_loader.get_data_path())
    EspeakWrapper.set_library(espeakng_loader.get_library_path())

    started = True


def sounds(text, language, vocab):
    """ONE SENTENCE AS THE SOUNDS IT IS SAID WITH, MINUS ANY THIS MODEL WAS NOT TAUGHT."""
    import phonemizer

    start()

    # A SENTENCE THAT MIXES TWO LANGUAGES MAKES espeak SWITCH MID-WAY AND MARK WHERE IT DID.
    # LEFT IN, THOSE MARKS ARE READ OUT AS SOUND; THE WORDS EITHER SIDE OF THEM ARE WANTED.
    said = phonemizer.phonemize(
        text,
        SPELLING.get(language, language),
        preserve_punctuation=True,
        with_stress=True,
        language_switch="remove-flags",
    )

    return "".join(mark for mark in said if mark in vocab).strip()


def spoken(text, language, vocab):
    """THE SOUNDS OF A SENTENCE, IN MOUTHFULS SHORT ENOUGH FOR THE MODEL TO TAKE."""
    return mouthfuls(sounds(text, language, vocab))


def mouthfuls(said):
    """AS FEW PIECES AS POSSIBLE, EACH ENDING WHERE THE SENTENCE ITSELF PAUSES, EXCEPT THE
    FIRST, WHICH IS SHORT SO SPEAKING STARTS WHILE THE REST OF IT IS STILL BEING MADE."""
    if not said:
        return []

    if len(said) <= WHOLE:
        return [said]

    pieces = []
    limit = FIRST

    while len(said) > limit:
        at = cut(said, limit)

        pieces.append(said[:at].strip())
        said = said[at:].strip()
        limit = LIMIT

    pieces.append(said)

    return [piece for piece in pieces if piece]


def cut(said, limit=LIMIT):
    """WHERE TO BREAK: THE LAST PAUSE THAT FITS, OR THE LAST GAP BETWEEN WORDS."""
    for mark in BREAKS:
        at = said.rfind(mark, 0, limit)

        if at > limit // 2:
            return at + 1

    space = said.rfind(" ", 0, limit)

    return space + 1 if space > 0 else limit


def ids(said, vocab):
    """THE SOUNDS AS THE NUMBERS THE MODEL WAS TRAINED ON, PADDED EACH END AS IT EXPECTS."""
    return [0] + [vocab[mark] for mark in said] + [0]
