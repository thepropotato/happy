"""ASKING A SECOND TIME WHETHER A PAGE REALLY BELONGS ON THEIR SCREEN."""

from hands.apps import telling

SHOW = "SHOW"

READ = "READ"

# A JUDGE THAT CANNOT MAKE ITS MIND UP LETS THE PAGE THROUGH. A SWALLOWED "SHOW ME" IS A
# WORSE FAILURE THAN THE ONE BEING FIXED, BECAUSE IT LOOKS LIKE HAPPY IGNORING THEM.
UNSURE = SHOW


def wanted(said):
    """WHETHER THIS PAGE BELONGS ON THEIR SCREEN. TRUE UNLESS SOMETHING IS SURE IT DOES NOT."""
    if not said:
        return True

    # THREE MILLISECONDS FIRST. IT ANSWERS FIVE TIMES IN SIX, AND HANDS THE CLOSE ONES ON TO
    # THE MODEL, WHICH TAKES NEARLY THREE SECONDS BUT UNDERSTANDS WORDS IT HAS NEVER SEEN.
    quick = telling.told(said)

    if quick is not None:
        return quick == telling.SHOWN

    return asked(said) != READ


def asked(said):
    """THE JUDGE'S ONE WORD, OR WHAT WE DO WHEN IT WILL NOT SAY ONE."""
    from brain import asking, signatures  # LATE: brain REACHES BACK INTO hands.

    # A JUDGE THAT IS DOWN NEVER STOPS A PAGE, AND asked() HANDS BACK None RATHER THAN RAISE.
    answer = asking.asked(signatures.Judging, said=said)

    return worded(None if answer is None else answer.wants)


def worded(said):
    """SHOW OR READ OUT OF WHATEVER THE FIELD CAME BACK HOLDING.

    THE SIGNATURE ASKS FOR ONE WORD BUT A MODEL MAY STILL SAY A SENTENCE, SO THE ANSWER IS
    STILL READ FOR WHICH WORD IS IN IT RATHER THAN COMPARED WHOLE."""
    said = (said or "").strip().upper()

    if READ in said and SHOW not in said:
        return READ

    if SHOW in said:
        return SHOW

    return UNSURE


def forget():
    """DROP THE HELD MODEL, FOR WHEN THE SETTINGS BEHIND IT MOVE."""
    from brain import asking

    asking.forget()
