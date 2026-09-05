"""THE TOOLS. EVERY DOCSTRING HERE IS READ BY THE MODEL, NOT BY US."""

from pathlib import Path

from langchain_core.tools import tool

from hands import reasons
from hands.files import infront, trashing
from hands.files.finding import describe, dig, hunt, locate
from hands.files.making import TOOLS as MAKING
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

    A file goes straight to read_file, control_app with "attach", or download. A project folder
    goes to run_command as directory, which otherwise runs in their home folder
    and answers about nothing. Their editor, their PDF, their document: this is
    the same question for all of them.

    Never go looking for it yourself by listing folders to guess which one they
    meant. When this cannot tell, ask them which one they mean and use the path
    they say. This is where a thing is; current_activity is what they are doing,
    for a question answered out loud."""
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
    """Find a file or a folder by name anywhere in the usual places: Desktop,
    Documents, Downloads, Pictures and the home folder. Give the whole name as
    they said it, not a shortened or guessed-at version of it — "website for
    venu" and "tax invoice 2026" both work as given, and shortening one to
    "website" or "invoice" only turns up other things that happen to share the
    shorter word. Use this when you need a file or folder's real path, or when
    the user is vague about where something is."""
    hits = hunt(name) + dig(name)

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


@tool
def move_to_trash(path: str) -> str:
    """Delete a file or a folder by moving it to the Trash. This is how you delete
    anything on this computer. Accepts a full path like "~/Desktop/old notes", or a
    name like "screenshot 3", in which case it finds it first. Give the name exactly
    as they said it — do not shorten it or guess at the path yourself; a shortened or
    guessed path is not the thing they meant and will not be found.

    Use this whenever you are asked to delete, remove, get rid of, bin, throw away
    or clear out something on the disk. This is the only tool that deletes; a
    command is never a fallback when this refuses.

    What it moves is still there, in the Trash, and restore_from_trash can put it
    back. Say that when you report it, so they know they have not lost it.

    It moves one thing per call. Asked to clear out several, call it once for each
    and name each one.

    When it says several things share that name, do not guess and do not call it
    again with the same name. Read the paths out and ask which one they mean."""
    if not trashing.supported():
        return reasons.no(trashing.UNSUPPORTED)

    found, complaint = trashing.meant(path)

    if found is None:
        return reasons.no(complaint)

    refused = trashing.allowed(found)

    if refused:
        return reasons.no(refused)

    # ASKED LAST, BECAUSE IT IS THE SLOW ONE: IT ADDS UP A WHOLE FOLDER BEFORE IT CAN ANSWER.
    vanishing = trashing.recoverable(found)

    if vanishing:
        return reasons.no(trashing.WOULD_VANISH.format(name=found.name, why=vanishing))

    # COUNTED BEFORE IT GOES, BECAUSE ONCE IT HAS MOVED THERE IS NOTHING LEFT TO COUNT.
    what, held = trashing.named(found)
    trouble = trashing.trash(found)

    if trouble:
        return reasons.no(trashing.FAILED.format(what=what, trouble=trouble))

    return trashing.DONE.format(what=what, held=held)


@tool
def restore_from_trash(path: str) -> str:
    """Restore one file or folder from the Trash back to where it came from.

    Accepts the original name, a full original path, or the name it has inside
    the Trash. Use this whenever you are asked to undo a delete, bring something
    back, recover it, or restore it from Trash/Recycle Bin.

    It restores one thing per call. If several trashed things match that name,
    this refuses and lists a few so you can ask which one they mean."""
    if not trashing.supported():
        return reasons.no(trashing.UNSUPPORTED)

    found, complaint = trashing.forgotten(path)

    if found is None:
        return reasons.no(complaint)

    trouble, restored_to = trashing.restore(found)

    if trouble:
        return reasons.no(trashing.RESTORE_FAILED.format(what=found["what"], trouble=trouble))

    return trashing.RESTORED.format(what=found["what"], where=restored_to)


TOOLS = [file_in_front, read_file, find_files, list_folder, move_to_trash, restore_from_trash, *MAKING]