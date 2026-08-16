"""WHAT SOMEBODY HAS OPEN, TURNED FROM THE NAME ON A WINDOW INTO A PATH ON THIS DISK."""

import re
from pathlib import Path

from eyes import attention
from hands.files import finding, projects

# WHAT AN EDITOR'S APPLICATION IS CALLED, LOWERCASED, ON EITHER SYSTEM. THESE HOLD A
# WHOLE FOLDER OPEN, SO THEIR TITLES NAME A PROJECT AND NOT ONLY A FILE.
EDITORS = [
    "code", "codium", "cursor", "windsurf", "zed", "sublime", "atom", "textmate",
    "nova", "pycharm", "intellij", "idea", "webstorm", "phpstorm", "rubymine",
    "goland", "clion", "rider", "datagrip", "fleet", "android studio", "eclipse",
    "netbeans", "emacs", "vim", "xcode",
]

# A PAGE IN ONE OF THESE IS NOT A FILE ON THIS DISK, WHATEVER ITS TITLE SAYS.
BROWSERS = ["chrome", "safari", "firefox", "opera", "edge", "brave", "arc", "vivaldi", "chromium"]

# THE SAME APPLICATIONS AS A TITLE SPELLS THEM, WHICH IS NEVER THE NAME OF THE FILE.
NAMES = {
    "code", "visual studio code", "vscodium", "cursor", "windsurf", "zed",
    "sublime text", "android studio", "intellij idea", "pycharm", "webstorm",
    "phpstorm", "xcode", "emacs", "vim", "neovim", "preview", "textedit",
    "microsoft word", "microsoft excel", "microsoft powerpoint", "pages",
    "numbers", "keynote", "adobe acrobat",
}

# WHAT AN APPLICATION PUTS BETWEEN THE FILE, THE FOLDER AND ITS OWN NAME.
SPLITS = ["—", "–", " - ", "|", "(", ")", "[", "]", "•", "●", "◍"]

# WHAT A TITLE SAYS ABOUT ITSELF RATHER THAN ABOUT ANYTHING ON THE DISK.
DECOR = {
    "workspace", "untitled", "administrator", "restricted mode", "new window",
    "ssh", "wsl", "dev container", "updating", "unsaved", "welcome", "default",
    "extension development host", "page", "read only", "compatibility mode",
}

# A PIECE LONGER THAN THIS IS A SENTENCE OFF A TAB, NOT THE NAME OF ANYTHING.
LONGEST = 60
MOST_WORDS = 8

# HOW MANY PIECES OF ONE TITLE, AND HOW MANY WINDOWS, ARE WORTH A WALK ROUND THE DISK.
MOST = 3
MOST_WINDOWS = 4

SUFFIX = re.compile(r"\.[A-Za-z0-9]{1,5}$")

CUT = ("…", "...")

NOTHING = "Nothing is open, so I cannot tell what they have in front of them."

UNKNOWN = (
    '{app} is in front with "{title}" open, but there is nothing by that name'
    " anywhere I looked. Ask them where it is and use the path they say."
)

BROWSING = (
    "{app} is in front, and a page in a browser is not a file on this disk."
    " already_open is what reads their tabs, and download is what puts a page's"
    " file on the disk."
)


def settled():
    """WHAT IS OPEN AS (app, path, project), FRONT FIRST, OR NOTHING AND WHAT TO SAY."""
    seen = attention.windows()

    if not seen:
        return [], NOTHING

    found = []

    for place, (app, title) in enumerate(seen[:MOST_WINDOWS]):
        if any(mark in app.lower() for mark in BROWSERS):
            continue

        # THE APPLICATION IN FRONT IS ASKED OUTRIGHT WHICH FILE IT IS SHOWING. THE ONES
        # BEHIND IT ARE ONLY WORTH THE DISK WHEN THEIR TITLE PLAINLY NAMES A FILE.
        said = attention.document() if place == 0 else None
        path = Path(said) if said else named(title, whole=place == 0)

        if path is not None:
            found.append((app, path, projects.holding(path)))

    if found:
        return found, None

    app, title = seen[0]

    if any(mark in app.lower() for mark in BROWSERS):
        return [], BROWSING.format(app=app)

    return [], UNKNOWN.format(app=app, title=title or "no title")


def named(title, whole):
    """THE PATH A WINDOW TITLE NAMES, LOOKED FOR ON THE DISK."""
    project = None
    file = None
    plain = None

    for piece in pieces(title):
        if SUFFIX.search(piece):
            file = file or hunted(piece)
            continue

        if not whole:
            continue

        found = spelled(piece) or projects.pick(piece)

        if found is None:
            continue

        # A FOLDER WITH A .git OR A package.json IN IT BEATS ONE THAT ONLY HAS THE NAME.
        if projects.looks(found):
            project = project or found
        else:
            plain = plain or found

    return project or file or plain


def hunted(piece):
    """THE FILE ONE PIECE OF A TITLE NAMES, SPELLED OUT OR GONE LOOKING FOR."""
    found = spelled(piece)

    if found is not None:
        return found

    hits = finding.hunt(piece)

    return hits[0] if hits else None


def spelled(piece):
    """A PIECE THAT IS ALREADY A WHOLE PATH, WHICH IS NOTHING TO GO LOOKING FOR."""
    path = Path(piece).expanduser()

    if piece.startswith("~") or path.is_absolute():
        return path if path.exists() else None

    return None


def pieces(title):
    """THE PARTS OF A TITLE THAT COULD NAME SOMETHING, LIKELIEST FIRST."""
    said = title

    for mark in SPLITS:
        said = said.replace(mark, "\n")

    # AN EDITOR PUTS THE FOLDER AT THE END AND A JETBRAINS ONE AT THE FRONT, SO BOTH
    # ENDS ARE TRIED AND THE LAST ONE GOES FIRST.
    found = [part.strip() for part in said.split("\n")]

    return [part for part in reversed(found) if worth(part)][:MOST]


def worth(part):
    """WHETHER A PIECE OF A TITLE IS WORTH A WALK ROUND THE DISK."""
    said = part.lower()

    if not part or said in DECOR or said in NAMES:
        return False

    # A NAME THE TITLE BAR RAN OUT OF ROOM FOR IS NOT A NAME ANYTHING HAS.
    if any(mark in part for mark in CUT):
        return False

    return len(part) <= LONGEST and len(part.split()) <= MOST_WORDS
