"""WHAT MAKES A FOLDER SOMEBODY'S PROJECT, AND WHICH FOLDER A BARE NAME MEANS."""

from hands.files import finding

# WHAT MAKES A FOLDER SOMEBODY'S PROJECT AND NOT JUST A FOLDER.
MARKS = [
    ".git", "package.json", "pyproject.toml", "Cargo.toml", "go.mod",
    "requirements.txt", "pom.xml", "Gemfile", "CMakeLists.txt", "Makefile",
]

# HOW FAR UP FROM A FILE ITS PROJECT COULD BE BEFORE THE ANSWER IS THAT IT HAS NONE.
UP = 6


def looks(path):
    """WHETHER ANYONE WOULD CALL THIS FOLDER A PROJECT."""
    return any((path / mark).exists() for mark in MARKS)


def rank(path, wanted):
    """LOWER IS LIKELIER: A PROJECT BEFORE A FOLDER, THE WHOLE NAME BEFORE A PIECE OF IT."""
    return (not looks(path), path.name.lower() != wanted.lower(), len(path.parts))


def pick(wanted):
    """THE LIKELIEST FOLDER OF THAT NAME, OR None IF NOTHING GOES BY IT."""
    hits = finding.dig(wanted)

    return sorted(hits, key=lambda path: rank(path, wanted))[0] if hits else None


def holding(path):
    """THE PROJECT A FILE BELONGS TO, FOUND BY CLIMBING RATHER THAN BY SEARCHING."""
    here = path if path.is_dir() else path.parent

    for folder in [here, *here.parents][:UP]:
        if looks(folder):
            return folder

    return None
