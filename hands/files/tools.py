"""THE TOOLS. EVERY DOCSTRING HERE IS READ BY THE MODEL, NOT BY US."""

from pathlib import Path

from langchain_core.tools import tool

from hands import reasons
from hands.files import infront
from hands.files.finding import describe, hunt, locate
from hands.files.readers import UNREADABLE, extract

MAX_CHARS = 40000

FRONT = "{app} is in front with {what}, at {path}."

BEHIND = "Also open: {app} with {what}, at {path}."

FOLDER = "the project {name}"

INSIDE = " It is in the project {name}, at {project}."

REPO = " It is a git repository."

# HOW MANY OF THE THINGS OPEN BEHIND THE FRONT ONE ARE WORTH NAMING.
MOST_BEHIND = 2

CUT = "\n\n[...cut. Ask again with start set past here to read on.]"

MAX_ENTRIES = 200


@tool
def file_in_front() -> str:
    """What this person has open in front of them, as a real path on this
    computer: the file itself, and the project folder it sits in.

    Call this the moment they say this, that, it, the one I have open, the one
    I am looking at, or the one I am working on, about anything that lives on
    the disk. Send this to Ravi, attach it, read it back to me, how many commits
    have I made today, what has changed in here — all of them are about a thing
    on the screen that every other tool needs as a path, and the name on a window
    is not a path.

    A file goes straight to read_file, attach_file or download. A project folder
    goes to run_command as directory, which otherwise runs in their home folder
    and answers about nothing. Their editor, their PDF, their document: this is
    the same question for all of them.

    Never go looking for it yourself. Listing Desktop and Documents one folder
    after another to guess which one they meant is not looking, it is searching
    in front of somebody who already knows, and the folder you settle on is a
    guess you will not mention. When this cannot tell, ask them which one they
    mean and use the path they say.

    This is where a thing is. current_activity is what they are doing and is
    the one to use when you were asked a question to answer out loud, not asked
    to go and do something with the file."""
    found, complaint = infront.settled()

    if not found:
        return reasons.no(complaint)

    app, path, project = found[0]
    whole = path.is_dir()
    said = FRONT.format(
        app=app,
        what=FOLDER.format(name=path.name) if whole else path.name,
        path=path,
    )

    # THE FOLDER A FILE SITS IN IS WHAT EVERY COMMAND ABOUT IT NEEDS, AND A TITLE
    # NEVER SAYS IT.
    if project is not None and not whole:
        said += INSIDE.format(name=project.name, project=project)

    if project is not None and (project / ".git").exists():
        said += REPO

    behind = [
        BEHIND.format(app=name, what=other.name, path=other)
        for name, other, _ in found[1:][:MOST_BEHIND]
    ]

    return "\n".join([said, *behind])


@tool
def read_file(path: str, start: int = 0) -> str:
    """Read what is inside a file and return it as plain text. Handles PDFs,
    Word documents, spreadsheets, presentations, screenshots and photos, and any
    kind of text or code file. Accepts a full path like "~/Documents/cv.pdf", or
    just a name like "resume" or "my cv", in which case it finds the file first.

    Use this whenever you are asked about the contents of something: to read,
    summarise, check, review or answer questions about a document. Do not say
    you cannot read files. If the text comes back cut short, call this again
    with start set to carry on from there."""
    found, note = locate(path)

    if found is None:
        return reasons.no(note)

    if found.is_dir():
        return reasons.no(f"{found} is a folder, not a file. Use list_folder to see inside it.")

    kind = UNREADABLE.get(found.suffix.lower())

    if kind:
        return reasons.no(
            f"{found.name} is {kind}. I can tell you it is there, but I cannot read it."
        )

    try:
        text = extract(found)
    except Exception as error:
        return reasons.no(f"Could not read {found.name}: {error}")

    if not text.strip():
        return reasons.no(f"{found.name} opened, but there is no text in it.")

    window = text[start : start + MAX_CHARS]
    more = CUT if len(text) > start + MAX_CHARS else ""
    header = f"{describe(found)}\n" + (f"{note}\n" if note else "")

    return f"{header}\n{window}{more}"


@tool
def find_files(name: str) -> str:
    """Find files by name anywhere in the usual places: Desktop, Documents,
    Downloads, Pictures and the home folder. Give the part of the name you know,
    like "resume", "tax", or "invoice 2026". Use this when you need a file's real
    path, or when the user is vague about where something is."""
    hits = hunt(name)

    if not hits:
        return reasons.no(f"Nothing found matching {name}.")

    return "\n".join(describe(path) for path in hits)


@tool
def list_folder(path: str = "~") -> str:
    """List what is directly inside a folder, with sizes. Use this for questions
    like "what is in my downloads" or before reading something when you are not
    sure of the exact file name."""
    folder = Path(path).expanduser()

    if not folder.is_dir():
        return reasons.no(f"{folder} is not a folder.")

    entries = sorted(folder.iterdir(), key=lambda p: p.name.lower())
    shown = [p for p in entries if not p.name.startswith(".")]

    if not shown:
        return reasons.no(f"{folder} is empty.")

    return "\n".join(f"{p.name}/" if p.is_dir() else describe(p) for p in shown[:MAX_ENTRIES])


TOOLS = [file_in_front, read_file, find_files, list_folder]
