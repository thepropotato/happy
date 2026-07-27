"""THE TEXT INSIDE A FILE, WHATEVER KIND OF FILE IT IS.

A PDF, A WORD FILE AND A SPREADSHEET ARE DIFFERENT PROBLEMS TO A PROGRAM AND THE
SAME REQUEST TO A PERSON. WHAT COMES BACK IS ALWAYS PLAIN TEXT.

A PICTURE IS A FORMAT LIKE ANY OTHER HERE, HANDED TO eyes AND COMING BACK AS THE
WORDS THAT WERE IN IT.
"""

SPREADSHEET_ROWS = 500  # A SHEET WITH A HUNDRED THOUSAND ROWS IS NOT A READ.

# THINGS THAT ARE NOT TEXT AND NEVER WILL BE. PICTURES ARE NOT ON THIS LIST.
UNREADABLE = {
    ".gif": "an image", ".heic": "an image",
    ".mp3": "audio", ".wav": "audio", ".m4a": "audio", ".aac": "audio", ".flac": "audio",
    ".mp4": "video", ".mov": "video", ".avi": "video", ".mkv": "video",
    ".zip": "an archive", ".tar": "an archive", ".gz": "an archive", ".dmg": "a disk image",
    ".doc": "an old Word file, which needs converting to .docx first",
}


def pdf(path):
    from pypdf import PdfReader

    pages = PdfReader(str(path)).pages

    return "\n\n".join(f"[page {n}]\n{p.extract_text() or ''}" for n, p in enumerate(pages, 1))


def word(path):
    import docx

    document = docx.Document(str(path))
    lines = [p.text for p in document.paragraphs]

    for table in document.tables:  # A CV'S DATES OFTEN LIVE IN A TABLE.
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
    """THE WORDS INSIDE AN IMAGE. IMPORTED LATE, SO eyes CAN USE locate() TOO."""
    import eyes

    return eyes.read(path)


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
