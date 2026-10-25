"""Finding pictures on the web, and saving whatever a link holds into Downloads."""

import mimetypes
import re
import time
import urllib.parse
from pathlib import Path
from typing import Annotated

from happy.system import native
from happy.tools import asked, report, tool
from happy.tools.apps import size_of

FOLDER = Path.home() / "Downloads"
CHUNK = 1 << 16
REPORT_EVERY = 5.0
images = []
found_at = 0.0


@tool(say="Looking for pictures.", label="Finding pictures of {query}")
def find_images(query: Annotated[str, "what the picture is of, in a few words"]):
    """Search the web for pictures: gives numbered images with their size and site. Save one with download and its number."""
    from ddgs import DDGS
    from ddgs.exceptions import DDGSException

    global images, found_at
    try:
        images = [r for r in DDGS(timeout=10).images(query, max_results=10) if r.get("image")]
    except DDGSException as error:
        return f"The picture search did not answer ({error}). Try again in a moment."
    found_at = time.monotonic()
    if not images:
        return f"Found no pictures of {query}."
    lines = [f"{i}. {r.get('title', '')[:80]} — {r.get('width', '?')}x{r.get('height', '?')}, from {urllib.parse.urlsplit(r.get('url') or r['image']).hostname}"
             for i, r in enumerate(images, 1)]
    return "\n".join(lines) + "\n\nThe first ones are the best matches; download saves one by its number."


def chosen(where):
    """The real address meant: a result number, the tab in front, or a link the person gave."""
    from happy.tools import web

    wanted = where.strip()
    if wanted.isdigit():
        number = int(wanted)
        # A NUMBER MEANS WHICHEVER LIST CAME LAST, PICTURES OR PAGES.
        pictures = found_at >= web.searched_at
        listed = images if pictures else web.results
        if not 1 <= number <= len(listed):
            raise LookupError(f"There is no result {number} to download.")
        hit = listed[number - 1]
        return (hit["image"], hit.get("thumbnail")) if pictures else (hit["href"], None)
    if re.fullmatch(r"(?:the |that |this )?(?:link|page|tab|file|one|it)", wanted.lower()):
        from happy.tools.browser import current, front_browser, list_tabs

        app = front_browser()
        tab = current(list_tabs(app)) if app else None
        if not tab:
            raise LookupError("No page is open to download; give the link or a result number.")
        return tab["url"], None
    url = wanted if "://" in wanted else "https://" + wanted
    said = asked.get()
    labels = [label for label in (urllib.parse.urlsplit(url).hostname or "").split(".")[:-1] if len(label) > 1 and label != "www"]
    known = [r["href"] for r in web.results] + [r["image"] for r in images]
    # AN ADDRESS THE MODEL WROTE ITSELF IS USUALLY INVENTED; IT HAS TO COME FROM THE PERSON OR A RESULT.
    if said is not None and wanted not in said and not any(label in said.lower() for label in labels) and url not in known:
        raise LookupError("That link was not given by them or found by a search. Use find_images or web_search, then download by number.")
    return url, None


def named(url, reply):
    """A file name for what came back: the one the site gives, else the end of the address, with the right extension."""
    disposition = reply.headers.get("content-disposition", "")
    match = re.search(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)", disposition)
    name = urllib.parse.unquote(match.group(1)) if match else urllib.parse.unquote(Path(urllib.parse.urlsplit(url).path).name)
    name = re.sub(r'[\\/:*?"<>|]+', " ", name).strip() or "download"
    kind = (reply.headers.get("content-type") or "").split(";")[0].strip()
    extension = mimetypes.guess_extension(kind) if kind else None
    if extension == ".jpe":
        extension = ".jpg"
    if extension and not Path(name).suffix:
        name += extension
    return name, kind


def free(name):
    """A path in Downloads that does not overwrite anything already there."""
    path = FOLDER / name
    count = 2
    while path.exists():
        path = FOLDER / f"{Path(name).stem} {count}{Path(name).suffix}"
        count += 1
    return path


def fetch(url):
    """Streams one address to Downloads, reporting how far it has got on a big file."""
    from curl_cffi import requests

    with requests.Session(impersonate="chrome") as session:
        reply = session.get(url, stream=True, timeout=30, allow_redirects=True)
        if reply.status_code >= 400:
            raise ConnectionError(f"the site refused it (status {reply.status_code})")
        name, kind = named(url, reply)
        total = int(reply.headers.get("content-length") or 0)
        FOLDER.mkdir(parents=True, exist_ok=True)
        path = free(name)
        partial = path.with_name(path.name + ".part")
        got, told = 0, time.monotonic()
        with partial.open("wb") as file:
            for piece in reply.iter_content(CHUNK):
                file.write(piece)
                got += len(piece)
                if time.monotonic() - told > REPORT_EVERY:
                    told = time.monotonic()
                    report(f"Downloaded {size_of(got)}" + (f" of {size_of(total)}" if total else "") + ".")
        partial.rename(path)
    return path, kind, got


@tool(say="Downloading it.", label="Downloading {where}")
def download(where: Annotated[str, "a result number from find_images or web_search, a link they gave, or 'this' for the page open in front"]):
    """Save whatever a link holds into Downloads (a picture, PDF, song, zip, installer, anything) and show it in Finder."""
    try:
        url, spare = chosen(where)
    except LookupError as error:
        return str(error)
    try:
        path, kind, got = fetch(url)
    except Exception as error:
        if not spare:
            return f"Could not download {url}: {error}"
        try:
            path, kind, got = fetch(spare)
        except Exception:
            return f"Could not download that picture: {error}. Try another result."
        smaller = " The full-size picture was refused, so this is the smaller copy the search had."
    else:
        smaller = ""
    native.open_path(path, reveal=True)
    note = smaller + ( " It is the web page itself, not a file inside it: this site only shows that in a browser." if kind == "text/html" else "")
    return f"Saved {path.name} ({size_of(got)}) to Downloads and showed it in {'Finder' if native.__name__.endswith('macos') else 'Explorer'}.{note}"
