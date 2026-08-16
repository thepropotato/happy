"""WORDS TURNED INTO THE SOUNDS THEY ARE MADE OF, WHICH IS WHAT A VOICE MODEL READS."""

# espeak-ng HAS ITS OWN NAME FOR A LANGUAGE, WHICH IS NOT THE TWO LETTERS EVERYTHING ELSE USES.
SPELLING = {"en": "en-us", "hi": "hi", "te": "te"}

# THE MODEL READS NO MORE THAN THIS AT ONCE, AND ITS STYLES ARE ONLY WRITTEN OUT THAT FAR. A
# SENTENCE ARRIVES CUT TO 260 LETTERS, SO ONLY ONE MADE ALMOST WHOLLY OF DIGITS REACHES IT.
LIMIT = 500

# WHERE A PERSON WOULD BREATHE, STRONGEST FIRST.
BREAKS = ".!?;:,"

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
    """A SENTENCE IS SAID IN ONE GO. THE ONLY THING THAT EVER BREAKS ONE IS THE MODEL REFUSING
    TO READ MORE THAN LIMIT SOUNDS AT A TIME.

    NOTHING IS BROKEN TO START SPEAKING SOONER ANY MORE. IT SAVED HALF A SECOND OF WAITING AND
    BOUGHT A PAUSE IN THE MIDDLE OF A CLAUSE: THE MODEL SHAPES A WHOLE UTTERANCE AT ONCE, SO
    WHEREVER A SENTENCE IS CUT IT FALLS AWAY AS THOUGH IT HAD ENDED THERE, MARK OR NO MARK."""
    pieces = []

    while len(said) > LIMIT:
        at = cut(said)

        pieces.append(said[:at].strip())
        said = said[at:].strip()

    return [piece for piece in pieces + [said] if piece]


def cut(said):
    """WHERE TO BREAK A SENTENCE LONGER THAN THE MODEL WILL READ: THE LAST PAUSE THAT FITS, AND
    ONLY IF IT HAS NONE AT ALL, THE LAST GAP BETWEEN WORDS."""
    for mark in BREAKS:
        at = said.rfind(mark, 0, LIMIT)

        if at > 0:
            return at + 1

    space = said.rfind(" ", 0, LIMIT)

    return space + 1 if space > 0 else LIMIT


def ids(said, vocab):
    """THE SOUNDS AS THE NUMBERS THE MODEL WAS TRAINED ON, PADDED EACH END AS IT EXPECTS."""
    return [0] + [vocab[mark] for mark in said] + [0]
