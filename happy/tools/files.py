"""Reading what is inside a file, writing text into one, and deleting to the Trash in a way that can be undone."""

import re
import time
import zipfile
from html import unescape
from pathlib import Path
from typing import Annotated, Literal

from happy import history
from happy.system import Failed, native
from happy.tools import Image, named_file, tool
from happy.tools.apps import PLACES, locate

LONGEST = 8000
PICTURES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".bmp", ".tiff"}
OFFICE = {".docx": r"word/document\.xml", ".pptx": r"ppt/slides/slide(\d+)\.xml", ".xlsx": r"xl/sharedStrings\.xml"}


def one(what):
    """The single file or folder a spoken name means, or why it cannot be told which."""
    given = Path(what.strip().strip('"')).expanduser()
    if given.is_absolute() and given.exists():
        return given
    hits = locate(what)
    words = [w for w in re.split(r"[\s_.-]+", what.lower().removeprefix("my ")) if w not in ("the", "file", "folder", "my", "")]
    named = [h for h in hits if all(w in Path(h).name.lower() for w in words)]
    if not named:
        raise LookupError(f"Found nothing called {what}." if not hits else
                          f"Nothing is called exactly {what}. Closest: " + "; ".join(hits[:4]))
    exact = [h for h in named if Path(h).stem.lower() == " ".join(words) or Path(h).name.lower() == what.lower()]
    if len(exact) == 1 or len(named) == 1:
        return Path((exact or named)[0])
    raise LookupError("More than one matches; which one? " + "; ".join(named[:5]))


def office_text(path):
    """The words in a Word, PowerPoint or Excel file, read straight from its XML."""
    with zipfile.ZipFile(path) as box:
        pattern = re.compile(OFFICE[path.suffix.lower()])
        parts = sorted((n for n in box.namelist() if pattern.fullmatch(n)),
                       key=lambda n: int(m.group(1)) if (m := pattern.fullmatch(n)) and m.groups() else 0)
        out = []
        for index, name in enumerate(parts, 1):
            xml = box.read(name).decode("utf-8", "replace")
            xml = re.sub(r"</w:p>|</a:p>|</si>", "\n", xml)
            text = unescape(re.sub(r"<[^>]+>", "", xml)).strip()
            out.append(f"[Slide {index}]\n{text}" if path.suffix.lower() == ".pptx" else text)
        return "\n\n".join(out)


def pdf_text(path):
    from pypdf import PdfReader

    reader = PdfReader(path)
    pages = []
    for number, page in enumerate(reader.pages, 1):
        pages.append(f"[Page {number}]\n{page.extract_text() or ''}")
        if sum(map(len, pages)) > LONGEST:
            break
    text = "\n\n".join(pages)
    if len(text.replace("[Page", "").strip()) < 20 * len(pages):
        return f"(This PDF is {len(reader.pages)} pages of scanned images with no text in them.)"
    return text + (f"\n\n(Read the first {len(pages)} of {len(reader.pages)} pages.)" if len(pages) < len(reader.pages) else "")


@tool(say="Reading it.", label="Reading {what}", check=named_file)
def read_file(what: Annotated[str, "the file's name as said, like 'my resume' or 'tax invoice', or a path"]):
    """Read what is inside a file on this computer: PDFs, Word, PowerPoint and Excel files, text and code, and pictures."""
    try:
        path = one(what)
    except LookupError as error:
        return str(error)
    if path.is_dir():
        return f"{path} is a folder; list_folder says what is in it."
    kind = path.suffix.lower()
    try:
        if kind in PICTURES:
            from happy.tools.screen import shrink

            data = path.read_bytes() if kind in (".png", ".jpg", ".jpeg") else native_png(path)
            return Image(shrink(data), f"The picture {path}.")
        if kind == ".pdf":
            text = pdf_text(path)
        elif kind in OFFICE:
            text = office_text(path)
        else:
            raw = path.read_bytes()[:400_000]
            if b"\0" in raw[:4000]:
                return f"{path.name} is not a kind of file that holds readable text."
            text = raw.decode("utf-8", "replace")
    except Exception as error:
        return f"Could not read {path}: {error}"
    more = f"\n\n(Showing the first {LONGEST} of {len(text)} characters.)" if len(text) > LONGEST else ""
    return f"{path}\n\n{text[:LONGEST]}{more}"


def native_png(path):
    """A picture in a format the model cannot take, turned into PNG by the system."""
    import subprocess
    import sys
    import tempfile

    if sys.platform != "darwin":
        raise Failed(f"{path.suffix} pictures can only be read on a Mac for now")
    with tempfile.TemporaryDirectory() as folder:
        out = Path(folder) / "picture.png"
        subprocess.run(["sips", "-s", "format", "png", str(path), "--out", str(out)], capture_output=True, check=True)
        return out.read_bytes()


def guarded(path, doing="delete"):
    """Refuses the folders a slip of the tongue must never touch: home, its standard folders, and anything outside home."""
    resolved = path.resolve()
    if resolved in {p.resolve() for p in PLACES.values()} or Path.home().resolve() not in resolved.parents:
        raise LookupError(f"{path} is not something I {doing}; do that one yourself.")


def destination(name, folder):
    """Where a file to write goes: inside the folder named, else the existing file of that name, else the Desktop."""
    given = Path(name.strip().strip('"')).expanduser()
    if given.is_absolute():
        return given
    if folder.strip():
        place = PLACES.get(folder.lower().removeprefix("my ").removesuffix(" folder").strip())
        if place is None:
            found = [Path(p) for p in locate(folder, folders=True) if Path(p).is_dir()]
            if not found:
                raise LookupError(f"Found no folder called {folder}.")
            place = found[0]
        return place / given.name
    try:
        return one(name)
    except LookupError:
        return PLACES["desktop"] / given.name


@tool(say="Writing it.", label="Writing {name}")
def write_file(
    name: Annotated[str, "the file's name with its ending, like notes.txt, or a path"],
    text: Annotated[str, "exactly what goes in the file"],
    folder: Annotated[str, "the folder for it, like desktop or documents; empty to use the file of that name, or the Desktop for a new one"] = "",
    how: Annotated[Literal["new", "add", "replace"], "new makes a file, add puts the text at the end, replace rewrites all of it"] = "new",
):
    """Write text into a file on this computer: make a new one, add to the end of one, or rewrite one. A rewritten file's old version goes to the Trash, where restore_from_trash brings it back. Opens the file after so they see it."""
    try:
        path = destination(name, folder)
        guarded(path, "write to")
    except LookupError as error:
        return str(error)
    if path.suffix.lower() in PICTURES | set(OFFICE) | {".pdf"} or path.exists() and b"\0" in path.read_bytes()[:4000]:
        return f"{path.name} is not a plain text file, so writing into it would break it."
    if path.is_dir():
        return f"{path} is a folder; give the file a name."
    if not path.parent.is_dir():
        return f"There is no folder at {path.parent}."
    existed = path.exists()
    if existed and how == "new":
        return f"{path} already exists. Add to it, or replace what is in it."
    try:
        if existed and how == "replace":
            history.trashed(str(path), native.trash(path))
            path.write_text(text)
        elif existed and how == "add":
            before = path.read_text(errors="replace")
            path.write_text(before + ("" if not before or before.endswith("\n") else "\n") + text)
        else:
            path.write_text(text)
        native.open_path(path)
    except (OSError, Failed) as error:
        return f"Could not write {path}: {error}"
    if not existed:
        return f"Wrote {path} and opened it."
    if how == "add":
        return f"Added to {path} and opened it."
    return f"Rewrote {path} and opened it. The old version is in the Trash."


@tool(say="Moving it to the Trash.", label="Deleting {what}", check=named_file)
def move_to_trash(what: Annotated[str, "the file or folder's name exactly as said, or a path"]):
    """Delete a file or folder by moving it to the Trash, where restore_from_trash can bring it back."""
    try:
        path = one(what)
        guarded(path)
    except LookupError as error:
        return str(error)
    try:
        held = native.trash(path)
    except Failed as error:
        return f"Could not delete {path}: {error}"
    history.trashed(str(path), str(held))
    return f"Moved {path} to the Trash."


@tool(say="Bringing it back.", label="Restoring {what}")
def restore_from_trash(what: Annotated[str, "words from the name of what was deleted; empty for the last thing deleted"] = ""):
    """Undo a delete: put a file or folder Happy moved to the Trash back where it was. "Bring it back" or "undo that" needs no name: leave what empty for the last thing deleted."""
    found = history.trashed_matching(what)
    if not found:
        return ("I have not deleted anything like that. Things deleted by hand have to be put back from the Trash in Finder."
                if what else "I have not deleted anything to bring back.")
    original, held = Path(found["original"]), found["held"]
    swapped = original.exists()
    try:
        if swapped:
            # WHAT TOOK ITS PLACE GOES TO THE TRASH IN TURN, SO PUTTING ONE BACK NEVER LOSES THE OTHER.
            history.trashed(str(original), native.trash(original))
        native.untrash(held, original)
    except Failed as error:
        return f"Could not bring back {original.name}: {error}"
    history.untrashed(found["id"])
    when = time.strftime("%d %b at %I:%M %p", time.localtime(found["at"])).replace(" 0", " ")
    return f"Put {original.name} back in {original.parent} (deleted {when})." + (" The one that replaced it is in the Trash." if swapped else "")
