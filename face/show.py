"""EVERY FACE AT ONCE."""

faces = []


def attach(face):
    if face not in faces:
        faces.append(face)


def detach(face):
    if face in faces:
        faces.remove(face)


def clear():
    faces.clear()


def tell(what, *args, **kwargs):
    for face in list(faces):
        doing = getattr(face, what, None)

        if doing is None:
            continue

        try:
            doing(*args, **kwargs)
        except Exception:
            continue


def cost():
    """WHAT THIS TURN HAS COST SO FAR, FROM WHICHEVER FACE IS KEEPING COUNT.

    THE FACES HOLD THE STOPWATCH, NOT THE BRAIN, AND WHAT IS WRITTEN DOWN AT THE END OF A
    TURN HAS TO COME FROM THE SAME PLACE THE PANEL READ IT OFF."""
    for face in list(faces):
        asking = getattr(face, "cost", None)

        if asking is None:
            continue

        try:
            found = asking()
        except Exception:
            continue

        if found:
            return found

    return None


def begin():
    tell("begin")


def waking():
    """A TURN THAT STARTED WITHOUT ANYBODY ASKING FOR ONE."""
    tell("waking")


def listening():
    tell("listening")


def idle():
    """WHAT WAS BEING LISTENED TO WAS NOT MEANT FOR HAPPY. PUT THE FACE BACK."""
    tell("idle")


def said(text, seconds=None):
    tell("said", text, seconds)


def opening():
    tell("opening")


def piece(text):
    tell("piece", text)


def unsay(many):
    """TAKE THE LAST many CHARACTERS BACK OFF THE PANEL.

    A GUARD TURNED THAT ROUND BACK AFTER THE STREAM HAD ALREADY DRAWN IT, SO WHAT IS ON THE
    SCREEN IS AN ANSWER NOBODY IS GOING TO STAND BEHIND."""
    tell("unsay", many)


def step(kind, name, seconds, about=None):
    tell("step", kind, name, seconds, about)


def trouble(text):
    tell("trouble", text)


def end():
    tell("end")


def note(text):
    tell("note", text)


def unprompted(text):
    tell("unprompted", text)


def working(text):
    """WHERE SOMETHING RUNNING IN THE BACKGROUND HAS GOT TO, WHILE IT IS STILL GOING."""
    tell("working", text)


def level(value):
    """HOW LOUD THE MICROPHONE IS RIGHT NOW, 0 TO 1."""
    tell("level", value)


def envelope(values, seconds):
    """THE SHAPE OF A CLIP ABOUT TO PLAY, SO A FACE CAN MOVE IN TIME WITH IT."""
    tell("envelope", values, seconds)


def hush():
    """HAPPY WAS CUT OFF. WHATEVER A FACE WAS DOING WITH SOUND, STOP."""
    tell("hush")


def state(name):
    tell("state", name)
