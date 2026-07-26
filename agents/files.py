"""
FILES. FINDING THEM AND READING WHAT IS INSIDE THEM.

A PERSON DOES NOT SAY "READ /Users/me/Documents/CV_final_v3.pdf". THEY SAY "READ
MY RESUME". SO FINDING COMES FIRST AND IS ITS OWN TOOL, AND IT SEARCHES WHERE
PEOPLE ACTUALLY PUT THINGS RATHER THAN THE WHOLE DISK.

READING IS ONE TOOL OVER MANY FORMATS. A PDF, A WORD FILE AND A SPREADSHEET ARE
DIFFERENT PROBLEMS TO A PROGRAM AND THE SAME REQUEST TO A PERSON, AND THE MODEL
SHOULD NOT HAVE TO KNOW WHICH IS WHICH BEFORE IT ASKS. WHAT COMES BACK IS ALWAYS
PLAIN TEXT.

A PICTURE IS A FORMAT LIKE ANY OTHER HERE, HANDED TO vision.py AND COMING BACK
AS THE WORDS THAT WERE IN IT. THE MODEL BEHIND HAPPY STILL DOES NOT LOOK: IT IS
READING TEXT PULLED OFF THE PIXELS, SO A SCREENSHOT OF A MESSAGE READS FINE AND
A PHOTOGRAPH OF A DOG COMES BACK EMPTY.
"""

import os
from pathlib import Path

from langchain_core.tools import tool

# WHERE PEOPLE KEEP THINGS. SEARCHED IN THIS ORDER, NEAREST FIRST.
PLACES = ["Desktop", "Documents", "Downloads", "Pictures", "Movies", "Music"]

# NEVER WALKED. THESE ARE ENORMOUS AND HOLD NOTHING ANYONE ASKS FOR BY NAME.
AVOID = {
    "Library", "node_modules", ".git", ".venv", "venv", "__pycache__", ".Trash",
    "Applications", ".cache", ".npm", "site-packages", ".ollama", "Photos Library.photoslibrary",
}

MAX_DEPTH = 4
MAX_HITS = 12

# ONE READ MUST NOT SWALLOW THE WHOLE CONTEXT. GENEROUS, BECAUSE THE MODEL NOW
# HAS ROOM, BUT NOT UNLIMITED, BECAUSE THE HISTORY HAS TO LIVE SOMEWHERE TOO.
MAX_CHARS = 40000

CUT = "\n\n[...cut. Ask again with start set past here to read on.]"

SPREADSHEET_ROWS = 500  # A SHEET WITH A HUNDRED THOUSAND ROWS IS NOT A READ.

# THINGS THAT ARE NOT TEXT AND NEVER WILL BE. SAID PLAINLY RATHER THAN GUESSED.
# PICTURES ARE NOT ON THIS LIST ANY MORE, THEY GO THROUGH vision.py INSTEAD.
UNREADABLE = {
    ".gif": "an image", ".heic": "an image",
    ".mp3": "audio", ".wav": "audio", ".m4a": "audio", ".aac": "audio", ".flac": "audio",
    ".mp4": "video", ".mov": "video", ".avi": "video", ".mkv": "video",
    ".zip": "an archive", ".tar": "an archive", ".gz": "an archive", ".dmg": "a disk image",
    ".doc": "an old Word file, which needs converting to .docx first",
}


def home():
    return Path.home()


def roots():
    """WHERE TO LOOK, NEAREST FIRST, SKIPPING THE ONES THAT DO NOT EXIST."""
    found = [home() / place for place in PLACES]

    return [path for path in found if path.is_dir()] + [home()]


def walk(root, depth):
    """EVERY FILE UNDER root, WITHOUT DESCENDING INTO THE ENORMOUS."""
    for here, folders, names in os.walk(root):
        folders[:] = [f for f in folders if f not in AVOID and not f.startswith(".")]

        if len(Path(here).relative_to(root).parts) >= depth:
            folders[:] = []

        for name in names:
            if not name.startswith("."):
                yield Path(here) / name


def hunt(wanted, depth=MAX_DEPTH, limit=MAX_HITS):
    """FILES WHOSE NAME CONTAINS wanted, NEAREST PLACES FIRST, NO REPEATS."""
    needle = wanted.lower().strip()
    seen, hits = set(), []

    for root in roots():
        for path in walk(root, depth):
            if needle in path.name.lower() and path not in seen:
                seen.add(path)
                hits.append(path)

                if len(hits) >= limit:
                    return hits

    return hits


def describe(path):
    size = path.stat().st_size

    return f"{path} ({size / 1024:.0f} KB)" if size < 1024**2 else f"{path} ({size / 1024**2:.1f} MB)"


def pdf(path):
    from pypdf import PdfReader

    pages = PdfReader(str(path)).pages

    return "\n\n".join(f"[page {n}]\n{p.extract_text() or ''}" for n, p in enumerate(pages, 1))


def word(path):
    import docx

    document = docx.Document(str(path))
    lines = [p.text for p in document.paragraphs]

    for table in document.tables:  # A CV'S DATES OFTEN LIVE IN A TABLE, NOT A PARAGRAPH.
        for row in table.rows:
            lines.append(" | ".join(cell.text.strip() for cell in row.cells))

    return "\n".join(line for line in lines if line.strip())


def sheet(path):
    from openpyxl import load_workbook

    book = load_workbook(str(path), data_only=True, read_only=True)
    out = []

    for tab in book.worksheets:
        out.append(f"[sheet: {tab.title}]")

        for count, row in enumerate(tab.iter_rows(values_only=True)):
            if count >= SPREADSHEET_ROWS:
                out.append(f"[...{tab.title} has more rows]")
                break

            out.append(" | ".join("" if cell is None else str(cell) for cell in row))

    book.close()

    return "\n".join(out)


def slides(path):
    from pptx import Presentation

    out = []

    for number, slide in enumerate(Presentation(str(path)).slides, 1):
        out.append(f"[slide {number}]")
        out += [s.text for s in slide.shapes if hasattr(s, "text") and s.text.strip()]

    return "\n".join(out)


def rich(path):
    from striprtf.striprtf import rtf_to_text

    return rtf_to_text(path.read_text(encoding="utf-8", errors="replace"))


def plain(path):
    raw = path.read_bytes()

    if b"\x00" in raw[:4096]:  # NUL BYTES MEAN IT WAS NEVER TEXT.
        raise ValueError("not a text file")

    return raw.decode("utf-8", errors="replace")


def picture(path):
    """THE WORDS INSIDE AN IMAGE. IMPORTED LATE, SO THE OTHER DIRECTION WORKS
    TOO AND vision CAN USE locate() TO FIND THE PICTURE IT WAS ASKED FOR."""
    from agents import vision

    return vision.read(path)


READERS = {
    ".pdf": pdf,
    ".png": picture,
    ".jpg": picture,
    ".jpeg": picture,
    ".bmp": picture,
    ".tiff": picture,
    ".tif": picture,
    ".webp": picture,
    ".docx": word,
    ".xlsx": sheet,
    ".xlsm": sheet,
    ".pptx": slides,
    ".rtf": rich,
}


def extract(path):
    """THE TEXT INSIDE path, WHATEVER KIND OF FILE IT IS."""
    reader = READERS.get(path.suffix.lower(), plain)

    return reader(path)


def locate(where):
    """THE PATH MEANT BY where, WHETHER IT IS A PATH OR A DESCRIPTION."""
    direct = Path(where).expanduser()

    if direct.exists():
        return direct, None

    hits = hunt(where)

    if not hits:
        return None, f"Nothing found called {where}."

    if len(hits) > 1 and hits[0].name.lower() != where.lower():
        listing = ", ".join(str(p) for p in hits[:5])

        return hits[0], f"Several matched, reading the first. Others: {listing}"

    return hits[0], None


# TOOLS. THE DESCRIPTIONS BELOW ARE READ BY THE MODEL, NOT BY US, SO THEY ARE
# WRITTEN AS PLAIN PROSE RATHER THAN AS COMMENTS.


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
    path, note = locate(path)

    if path is None:
        return note

    if path.is_dir():
        return f"{path} is a folder, not a file. Use list_folder to see inside it."

    kind = UNREADABLE.get(path.suffix.lower())

    if kind:
        return f"{path.name} is {kind}. I can tell you it is there, but I cannot read it."

    try:
        text = extract(path)
    except Exception as error:
        return f"Could not read {path.name}: {error}"

    if not text.strip():
        return f"{path.name} opened, but there is no text in it."

    window = text[start : start + MAX_CHARS]
    more = CUT if len(text) > start + MAX_CHARS else ""
    header = f"{describe(path)}\n" + (f"{note}\n" if note else "")

    return f"{header}\n{window}{more}"


@tool
def find_files(name: str) -> str:
    """Find files by name anywhere in the usual places: Desktop, Documents,
    Downloads, Pictures and the home folder. Give the part of the name you know,
    like "resume", "tax", or "invoice 2026". Use this when you need a file's real
    path, or when the user is vague about where something is."""
    hits = hunt(name)

    if not hits:
        return f"Nothing found matching {name}."

    return "\n".join(describe(path) for path in hits)


@tool
def list_folder(path: str = "~") -> str:
    """List what is directly inside a folder, with sizes. Use this for questions
    like "what is in my downloads" or before reading something when you are not
    sure of the exact file name."""
    folder = Path(path).expanduser()

    if not folder.is_dir():
        return f"{folder} is not a folder."

    entries = sorted(folder.iterdir(), key=lambda p: p.name.lower())
    shown = [p for p in entries if not p.name.startswith(".")]

    if not shown:
        return f"{folder} is empty."

    return "\n".join(f"{p.name}/" if p.is_dir() else describe(p) for p in shown[:200])


TOOLS = [read_file, find_files, list_folder]


if __name__ == "__main__":
    import sys

    print(read_file.invoke({"path": " ".join(sys.argv[1:]) or "~/.zshrc"})[:2000])
