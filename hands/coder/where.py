"""WHICH FOLDER THE CODER WORKS IN, WHICH IS NEVER WHEREVER HAPPY HAPPENS TO BE."""

from pathlib import Path

from hands.files.projects import pick

NOWHERE = (
    "There is no project called {name} anywhere I looked. If this is new work, ask"
    " the user which folder it should go in, then call build again with the whole"
    " path. Do not pick a folder yourself."
)

NAMELESS = "Say which project this is for, by name or by whole path."


def settle(project):
    """THE FOLDER TO WORK IN, OR None AND WHAT TO SAY INSTEAD OF WORKING."""
    wanted = " ".join(str(project or "").split())

    if not wanted:
        return None, NAMELESS

    spelled = Path(wanted).expanduser()

    # A WHOLE PATH IS THE USER'S OWN ANSWER TO WHERE, SO IT IS TAKEN AS GIVEN AND
    # MADE IF IT IS NOT THERE YET.
    if wanted.startswith("~") or len(spelled.parts) > 1:
        return made(spelled)

    found = pick(wanted)

    return (found, None) if found else (None, NOWHERE.format(name=wanted))


def made(path):
    """A WHOLE PATH, DUG OUT IF THE FOLDER ABOVE IT IS ALREADY THERE."""
    if path.is_dir():
        return path, None

    if path.exists():
        return None, f"{path} is a file, not a folder."

    if not path.parent.is_dir():
        return None, f"There is no folder at {path.parent} to put {path.name} in."

    try:
        path.mkdir()
    except OSError as error:
        return None, f"Could not make {path}. {error}"

    return path, None
