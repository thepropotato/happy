"""WHAT A THING TURNS OUT TO BE, AND WHAT IT OUGHT TO BE CALLED ONCE IT IS ON THE DISK."""

import mimetypes
from pathlib import Path
from urllib.parse import unquote

# HOW FAR IN TO LOOK, WHAT SITS THERE, WHAT IT MAKES THIS. A BRAND COMES BEFORE THE ftyp BELOW IT.
SIGNATURES = (
    (0, b"\xff\xd8\xff", ".jpg"), (0, b"\x89PNG\r\n\x1a\n", ".png"), (0, b"GIF8", ".gif"),
    (0, b"BM", ".bmp"), (0, b"II*\x00", ".tif"), (0, b"MM\x00*", ".tif"), (0, b"<svg", ".svg"),
    (8, b"WEBP", ".webp"), (8, b"avif", ".avif"), (8, b"heic", ".heic"), (8, b"heix", ".heic"),
    (8, b"mif1", ".heic"), (8, b"WAVE", ".wav"), (8, b"AVI ", ".avi"), (4, b"ftyp", ".mp4"),
    (0, b"%PDF", ".pdf"), (0, b"PK\x03\x04", ".zip"), (0, b"\x1f\x8b", ".gz"),
    (0, b"Rar!", ".rar"), (0, b"7z\xbc\xaf\x27\x1c", ".7z"), (0, b"ID3", ".mp3"),
    (0, b"OggS", ".ogg"), (0, b"fLaC", ".flac"), (0, b"\x1aE\xdf\xa3", ".mkv"),
)

# THE ONLY KINDS PYTHON'S OWN TABLE HAS NOTHING FOR.
EXTRA = {"audio/wav": ".wav", "application/gzip": ".gz", "application/vnd.rar": ".rar"}

# BYTES THAT ONLY SAY "A CONTAINER". A .docx IS A .zip, AND ONLY ITS NAME KNOWS WHICH IT IS.
LOOSE = {".zip", ".gz"}

MOST = 6  # A LONGER RUN AFTER A DOT IS PART OF THE NAME, NOT AN ENDING.


def sniffed(head):
    """WHAT THIS IS BY ITS BYTES ALONE, WHICH IS THE ONE THING A REFUSAL PAGE CANNOT DRESS UP AS."""
    for at, signature, ending in SIGNATURES:
        if head[at : at + len(signature)] == signature:
            return ending

    return None


def ending_for(head, kind, called):
    """THE BYTES DECIDE, SINCE AN ADDRESS ENDING .php CAN STILL HAND OVER A PDF. WHERE THEY ONLY
    SAY "A CONTAINER" THE NAME IT CAME WITH IS ASKED, AND AFTER THAT WHAT THE SERVER CALLED IT."""
    found = sniffed(head)

    if found and found not in LOOSE:
        return found

    told = EXTRA.get(kind) or mimetypes.guess_extension(kind)
    return named_as(called) or (told if told != ".bin" else None) or found or ".bin"


def named_as(called):
    """THE ENDING ON WHAT IT WAS CALLED, WHERE THAT IS ONE: 2301.00001 IS AN ID, NOT AN ENDING."""
    suffix = Path(unquote(called)).suffix.lower()
    real = 1 < len(suffix) <= MOST and suffix[1:].isalnum() and any(c.isalpha() for c in suffix)

    return suffix if real else None


def kept(called, ending):
    """THE NAME IT ARRIVED UNDER, KEPT WHOLE THE WAY A BROWSER KEEPS IT, AND ONLY GIVEN AN ENDING
    WHERE IT HAS NONE OF ITS OWN."""
    name = unquote(Path(called).name).strip() or "download"

    return name if name.lower().endswith(ending) else name + ending


def parted(name):
    """A NAME AND THE WHOLE OF ITS ENDING: archive.tar.gz IS archive AND .tar.gz, WHICH IS WHY A
    SECOND COPY OF IT CAN BE archive-1.tar.gz RATHER THAN archive.tar-1.gz."""
    stem, ending = name, ""

    while True:
        suffix = named_as(stem)

        if not suffix:
            return stem, ending

        stem, ending = stem[: -len(suffix)], suffix + ending
