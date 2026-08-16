"""PUTTING WHAT AN ADDRESS HANDS OVER ONTO THE DISK, WHATEVER KIND OF THING IT TURNS OUT TO BE."""

from concurrent.futures import ThreadPoolExecutor
import re
import threading
from urllib.parse import unquote, urlparse

import httpx

from hands.apps.opening import web_address
from hands.files import kinds
from hands.web.pages import AS_OURSELVES
from hands.web.searching import LIKE_A_BROWSER

PATIENCE = 30

MOST_BYTES = 500 * 1024 * 1024

# HOW MANY GO AT ONCE. TEN PICTURES ONE AFTER ANOTHER IS A MINUTE OF SOMEBODY WAITING.
AT_ONCE = 6

# ENOUGH OF THE FRONT TO KNOW WHAT A THING IS. THE REST GOES STRAIGHT TO THE DISK.
TASTE = 65536

# ALL OF IT, WHATEVER IT IS. THE IMAGE-FIRST ONE A BROWSER SENDS MAKES A CDN NEGOTIATE, AND AN
# AVIF SITTING IN A DOWNLOADS FOLDER OPENS IN FEWER THINGS THAN THE JPEG IT WOULD OTHERWISE SEND.
EVERYTHING = "*/*"

# A CDN WANTS A BROWSER ASKING. A SITE WITH A ROBOT POLICY WANTS TO BE TOLD WHO WE REALLY ARE.
WANTING = {**LIKE_A_BROWSER, "Accept": EVERYTHING}

HONEST = {**AS_OURSELVES, "Accept": EVERYTHING}

TURNED_AWAY = (401, 403, 429)

# WHAT THE SERVER CALLS IT WHEN IT MEANT THIS TO BE SAVED RATHER THAN SHOWN.
NAMED = re.compile(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)", re.I)

PLAIN = re.compile(r"[^A-Za-z0-9]+")

# SIX AT ONCE ALL WANT THE SAME NAME, AND WITHOUT THIS TWO OF THEM PICK IT.
claiming = threading.Lock()


class DownloadError(Exception):
    pass


class Refused(DownloadError):
    """A DOOR HELD SHUT, WHICH IS THE ONE FAILURE WORTH ASKING A SECOND WAY."""


def save(url, into, stem="", page="", only=()):
    """ONE ADDRESS ONTO THE DISK. only NAMES THE ENDINGS WORTH KEEPING, FOR WHEN WE PICKED THE
    ADDRESS OURSELVES: THERE THE NAME ON IT PROVES NOTHING AND THE BYTES HAVE TO DECIDE."""
    address = web_address(url)
    asking = {**WANTING, "Referer": page} if page else WANTING

    try:
        return written(address, asking, into, stem, only)
    except Refused:
        return written(address, HONEST, into, stem, only)


def written(address, headers, into, stem, only):
    """ONE ATTEMPT, READ IN PIECES SO THAT SOMETHING ENORMOUS NEVER SITS IN MEMORY."""
    try:
        with httpx.stream(
            "GET", address, headers=headers, timeout=PATIENCE, follow_redirects=True
        ) as answer:
            if answer.status_code in TURNED_AWAY:
                raise Refused(f"it answered {answer.status_code}")

            if answer.status_code >= 400:
                raise DownloadError(f"it answered {answer.status_code}")

            pieces = answer.iter_bytes(TASTE)
            head = next(pieces, b"")
            kind = (answer.headers.get("content-type") or "").split(";")[0].strip().lower()
            called = given(answer) or urlparse(address).path
            ending = kinds.sniffed(head) if only else kinds.ending_for(head, kind, called)

            if ending is None or (only and ending not in only):
                raise DownloadError(f"what came back was {kind or 'nothing'}, not what was wanted")

            named = f"{stem}{ending}" if stem else kinds.kept(called, ending)

            return poured(head, pieces, free(into, named))
    except httpx.HTTPError as error:
        raise DownloadError(f"it could not be fetched ({error.__class__.__name__})")


def poured(head, pieces, landed):
    """THE BYTES ONTO THE DISK, AND NOTHING LEFT LYING THERE HALF WRITTEN IF IT STOPS."""
    size = 0

    try:
        with landed.open("wb") as file:
            for piece in (head, *pieces):
                size += len(piece)
                if size > MOST_BYTES:
                    raise DownloadError("it is too big to be worth downloading")

                file.write(piece)
    except Exception:
        landed.unlink(missing_ok=True)
        raise

    return landed


def given(answer):
    """THE NAME THE SERVER ASKED FOR IT TO BE SAVED AS, WHERE IT SAID ONE."""
    found = NAMED.search(answer.headers.get("content-disposition") or "")

    return unquote(found.group(1)).strip() if found else ""


def free(into, named):
    """A PATH NOTHING IS SITTING AT, SO A SECOND GO NEVER WRITES OVER THE FIRST."""
    stem, ending = kinds.parted(named)
    plain = PLAIN.sub("-", stem).strip("-").lower()[:60] or "download"

    with claiming:
        path = into / f"{plain}{ending}"
        count = 1

        while path.exists():
            path = into / f"{plain}-{count}{ending}"
            count += 1

        path.touch()  # THE NAME IS TAKEN WHEN IT IS PICKED, NOT WHEN THE BYTES ARRIVE.

    return path


def gather(candidates, into, wanted, stem, only=()):
    """AS MANY AS WERE ASKED FOR, TAKEN A HANDFUL AT A TIME AND SKIPPING WHATEVER REFUSES."""
    saved, refused, rest = [], 0, list(candidates)

    with ThreadPoolExecutor(max_workers=AT_ONCE) as pool:
        while rest and len(saved) < wanted:
            batch, rest = rest[: wanted - len(saved)], rest[wanted - len(saved) :]

            for landed in pool.map(lambda one: tried(one, into, stem, only), batch):
                if landed is None:
                    refused += 1
                else:
                    saved.append(landed)

    return saved, refused


def tried(found, into, stem, only):
    try:
        return save(found.url, into, stem, found.page, only)
    except Exception:
        return None
