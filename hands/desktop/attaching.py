"""PUTTING A FILE INTO WHATEVER IS ASKING FOR ONE."""

import time

from hands.controls import clipboard
from hands.controls.commands import on_mac
from hands.desktop import acting, expecting, noticing, pointer
from hands.desktop.verifying import Done, judged, looking, report, settled


def attached(path, into=""):
    """PUT A FILE WHERE THE CURSOR IS, AND CHECK THAT IT ARRIVED."""
    from hands import files  # LATE, THE WAY eyes DOES IT.

    where, note = files.locate(path)

    if where is None:
        return Done(note, False)

    if where.is_dir():
        return Done(f"{where.name} is a folder, not a file.", False)

    complaint = clipboard.write_file(where)

    if complaint:
        return Done(complaint, False)

    if into and not holding(into):
        first = acting.clicked(into)

        if not first.worked:
            return first

    model, before, trouble = looking()

    if trouble:
        return Done(trouble, False)

    expectation = expecting.for_attaching(where.name)
    at = time.time()

    noticing.watch().start()
    pointer.press(paste())

    answer, after = judged(expectation, before, settled(before), model)
    said = f"Attached {where.name}" + (f" to {into}" if into else "")
    done = report(said, answer, after, at)

    # THE ONE THAT GOES OUT CANNOT BE TAKEN BACK, AND ONLY THE PERSON KNOWS WHICH.
    if note and done.worked:
        return Done(f"{done.said} More than one file matched, so check it is the right one.", True)

    return done


def holding(into):
    """TRUE WHEN THE KEYBOARD IS ALREADY IN THE BOX WE WERE GOING TO CLICK."""
    import eyes

    focus = eyes.current().glance().focus

    return bool(focus) and expecting.settled(focus, into)


def paste():
    return "cmd+v" if on_mac() else "ctrl+v"
