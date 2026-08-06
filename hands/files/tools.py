"""THE TOOLS. EVERY DOCSTRING HERE IS READ BY THE MODEL, NOT BY US."""

from pathlib import Path

from langchain_core.tools import tool

from hands import asking
from hands.files.finding import describe, hunt, locate
from hands.files.readers import UNREADABLE, extract

MAX_CHARS = 40000

CUT = "\n\n[...cut. Ask again with start set past here to read on.]"

MAX_ENTRIES = 200


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
        return asking.no(note)

    if found.is_dir():
        return asking.no(f"{found} is a folder, not a file. Use list_folder to see inside it.")

    kind = UNREADABLE.get(found.suffix.lower())

    if kind:
        return asking.no(
            f"{found.name} is {kind}. I can tell you it is there, but I cannot read it."
        )

    try:
        text = extract(found)
    except Exception as error:
        return asking.no(f"Could not read {found.name}: {error}")

    if not text.strip():
        return asking.no(f"{found.name} opened, but there is no text in it.")

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
        return asking.no(f"Nothing found matching {name}.")

    return "\n".join(describe(path) for path in hits)


@tool
def list_folder(path: str = "~") -> str:
    """List what is directly inside a folder, with sizes. Use this for questions
    like "what is in my downloads" or before reading something when you are not
    sure of the exact file name."""
    folder = Path(path).expanduser()

    if not folder.is_dir():
        return asking.no(f"{folder} is not a folder.")

    entries = sorted(folder.iterdir(), key=lambda p: p.name.lower())
    shown = [p for p in entries if not p.name.startswith(".")]

    if not shown:
        return asking.no(f"{folder} is empty.")

    return "\n".join(f"{p.name}/" if p.is_dir() else describe(p) for p in shown[:MAX_ENTRIES])


TOOLS = [read_file, find_files, list_folder]
