"""WHICH FOLDER THE CODER WORKS IN, WHICH IS NEVER WHEREVER HAPPY HAPPENS TO BE."""

from pathlib import Path

from hands.files import finding

# WHAT MAKES A FOLDER SOMEBODY'S PROJECT AND NOT JUST A FOLDER.
MARKS = [
    ".git", "package.json", "pyproject.toml", "Cargo.toml", "go.mod",
    "requirements.txt", "pom.xml", "Gemfile", "CMakeLists.txt", "Makefile",
]

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


def pick(wanted):
    """THE LIKELIEST FOLDER OF THAT NAME, OR None IF NOTHING GOES BY IT."""
    hits = finding.dig(wanted)

    return sorted(hits, key=lambda path: rank(path, wanted))[0] if hits else None


def rank(path, wanted):
    """LOWER IS LIKELIER: A PROJECT BEFORE A FOLDER, THE WHOLE NAME BEFORE A PIECE OF IT."""
    return (not looks(path), path.name.lower() != wanted.lower(), len(path.parts))


def looks(path):
    """WHETHER ANYONE WOULD CALL THIS FOLDER A PROJECT."""
    return any((path / mark).exists() for mark in MARKS)
