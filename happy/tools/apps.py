"""Opening and closing apps, files, folders and links."""

import difflib
import re
import os
import shutil
import subprocess
import sys
import time
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Annotated

from happy.system import Failed, native
from happy.tools import asked, tool

ALIASES = {
    "vs code": "Visual Studio Code", "vscode": "Visual Studio Code", "code": "Visual Studio Code",
    "chrome": "Google Chrome", "settings": "System Settings", "system preferences": "System Settings",
    "word": "Microsoft Word", "excel": "Microsoft Excel", "powerpoint": "Microsoft PowerPoint",
    "outlook": "Microsoft Outlook", "teams": "Microsoft Teams", "edge": "Microsoft Edge",
    "brave": "Brave Browser", "files": "Finder", "explorer": "File Explorer", "mail": "Mail",
    "claude": "Claude", "terminal": "Terminal", "iterm": "iTerm", "app store": "App Store",
}

PLACES = {
    "desktop": Path.home() / "Desktop", "downloads": Path.home() / "Downloads",
    "documents": Path.home() / "Documents", "home": Path.home(), "pictures": Path.home() / "Pictures",
    "music": Path.home() / "Music", "movies": Path.home() / "Movies", "videos": Path.home() / "Videos",
    "applications": Path("/Applications"),
}


def find_app(name):
    """The installed app a spoken name most likely means."""
    apps = native.installed_apps()
    wanted = ALIASES.get(name.lower().strip(), name.strip())
    lowered = {a.lower(): a for a in apps}
    if wanted.lower() in lowered:
        return lowered[wanted.lower()], apps[lowered[wanted.lower()]]
    starts = [a for a in apps if a.lower().startswith(wanted.lower())]
    if starts:
        best = min(starts, key=len)
        return best, apps[best]
    inside = [a for a in apps if wanted.lower() in a.lower()]
    if inside:
        best = min(inside, key=len)
        return best, apps[best]
    close = difflib.get_close_matches(wanted.lower(), list(lowered), n=1, cutoff=0.7)
    if close:
        return lowered[close[0]], apps[lowered[close[0]]]
    return None, None


@tool(label="Opening {name}")
def open_app(name: Annotated[str, "the app's name as said, like chrome or vs code"]):
    """Open an app, or bring it to the front if it is already open."""
    found, path = find_app(name)
    if not found:
        return f"No app called {name} is installed."
    native.open_app(path)
    return f"Opened {found}."


@tool(label="Quitting {name}")
def quit_app(name: Annotated[str, "the app's name"]):
    """Quit an app."""
    found, _ = find_app(name)
    running = native.running_apps()
    target = found if found in running else next((r for r in running if name.lower() in r.lower()), None)
    if not target:
        return f"{found or name} is not open."
    native.quit_app(target)
    return f"Quit {target}."


def score(path, words, folders):
    name = Path(path).name.lower()
    joined = " ".join(words)
    value = 0.0
    if name == joined or Path(path).stem.lower() == joined:
        value += 10
    elif name.startswith(joined):
        value += 6
    elif all(w in name for w in words):
        value += 4
    value -= path.count(os.sep) * 0.3
    if folders and Path(path).is_dir():
        value += 2
    if (Path(path) / ".git").exists():
        value += 1.5
    try:
        age_days = (time.time() - Path(path).stat().st_mtime) / 86400
        value += max(0.0, 2 - age_days / 30)
    except OSError:
        value -= 5
    return value


def locate(query, folders=False):
    """Paths that a spoken description of a file or folder could mean, best first."""
    query = query.strip().strip('"')
    expanded = Path(os.path.expanduser(query))
    if expanded.is_absolute() and expanded.exists():
        return [str(expanded)]
    key = query.lower().removesuffix(" folder").removeprefix("my ").strip()
    if key in PLACES and PLACES[key].exists():
        return [str(PLACES[key])]
    first, _, rest = key.replace("\\", "/").partition("/")
    if rest and first in PLACES:
        # A PATH FROM A KNOWN PLACE, WHICH SPOTLIGHT WOULD TAKE AS ONE UNKNOWN WORD.
        inside = next((PLACES[first] / name for name in os.listdir(PLACES[first]) if name.lower() == rest.strip("/")), None)
        if inside is not None:
            return [str(inside)]
    words = [w for w in key.replace("-", " ").replace("_", " ").split()
             if w not in ("the", "my", "folder", "file", "project", "repo")]
    if not words:
        return []
    hits = native.spotlight(" ".join(words), folders_only=folders)
    if not hits and folders:
        hits = native.spotlight(" ".join(words))
    return sorted(hits, key=lambda p: -score(p, words, folders))[:8]


def code_editor(app):
    lowered = app.lower()
    if lowered in ("vs code", "vscode", "code", "visual studio code"):
        cli = shutil.which("code")
        return ("cli", cli) if cli else ("app", "Visual Studio Code")
    if lowered == "cursor" and shutil.which("cursor"):
        return "cli", shutil.which("cursor")
    found, path = find_app(app)
    if not found:
        raise Failed(f"No app called {app} is installed.")
    return "app", path


@tool(label="Opening {what}")
def open_file(
    what: Annotated[str, "a path, or the name of a file or folder, like 'happy project' or 'resume pdf'"],
    app: Annotated[str, "app to open it in, like 'vs code', 'finder' or 'preview'; empty for the default"] = "",
    folder: Annotated[bool, "true if they mean a folder or project"] = False,
):
    """Find a file or folder on this computer and open it, in Finder, VS Code or any other app."""
    hits = locate(what, folders=folder or app.lower() in ("vs code", "vscode", "code", "cursor"))
    if not hits:
        return f"Found nothing called {what}."
    path = hits[0]
    if app.lower() in ("finder", "file explorer", "explorer"):
        native.open_path(path, reveal=not Path(path).is_dir())
        where = "Finder" if sys.platform == "darwin" else "Explorer"
    elif app:
        kind, how = code_editor(app)
        if kind == "cli":
            subprocess.Popen([how, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            native.open_path(path, app=how)
        where = app
    else:
        native.open_path(path)
        where = "its default app"
    others = "" if len(hits) == 1 else " Other matches: " + "; ".join(hits[1:4])
    return f"Opened {path} in {where}.{others}"


@tool(label="Looking for {what}")
def find_files(
    what: Annotated[str, "name or part of the name"],
    folder: Annotated[bool, "true to look only for folders"] = False,
):
    """Search this computer for files or folders by name, without opening anything."""
    hits = locate(what, folders=folder)
    if not hits:
        return f"Found nothing called {what}."
    lines = []
    for path in hits:
        try:
            when = time.strftime("%d %b %Y", time.localtime(Path(path).stat().st_mtime))
        except OSError:
            when = "?"
        lines.append(f"{path} (changed {when})")
    return "\n".join(lines)


def size_of(count):
    for unit in ("bytes", "KB", "MB", "GB"):
        if count < 1024 or unit == "GB":
            return f"{count:.0f} {unit}" if unit == "bytes" else f"{count:.1f} {unit}"
        count /= 1024


def folder_sizes(folders, limit=20):
    """Each folder's total size in bytes, everything inside counted; empty when it would take too long."""
    if not folders:
        return {}
    if sys.platform != "win32":
        try:
            out = subprocess.run(["du", "-sk", *map(str, folders)], capture_output=True, text=True, timeout=limit).stdout
        except subprocess.TimeoutExpired:
            return {}
        sizes = {}
        for line in out.splitlines():
            kb, _, path = line.partition("\t")
            if kb.isdigit():
                sizes[path] = int(kb) * 1024
        return sizes
    ends, sizes = time.monotonic() + limit, {}
    for folder in folders:
        total = 0
        for root, _, names in os.walk(folder):
            if time.monotonic() > ends:
                return {}
            for name in names:
                try:
                    total += os.lstat(os.path.join(root, name)).st_size
                except OSError:
                    pass
        sizes[str(folder)] = total
    return sizes


def files_within(folder, limit=8):
    """How many files are in a folder counting every folder inside it, or None when it would take too long."""
    ends, count = time.monotonic() + limit, 0
    for _, _, names in os.walk(folder):
        if time.monotonic() > ends:
            return None
        count += len(names)
    return count


@tool(label="Looking in {folder}")
def list_folder(folder: Annotated[str, "a folder by name, like downloads, desktop or 'happy project', or a path"]):
    """What is inside a folder: how many files and folders, what kinds, how big each one is and in all, and the newest ones. Use it for 'how many files', 'how big', 'what's in' and 'latest download'."""
    hits = locate(folder, folders=True)
    place = next((Path(p) for p in hits if Path(p).is_dir()), None)
    if place is None:
        return f"Found no folder called {folder}."
    try:
        entries = [e for e in place.iterdir() if not e.name.startswith(".")]
    except PermissionError:
        return f"{place} cannot be read: allow Happy in System Settings > Privacy & Security > Files and Folders."
    files = [e for e in entries if e.is_file()]
    folders = [e for e in entries if e.is_dir()]
    kinds = {}
    for e in files:
        kind = e.suffix.lower().lstrip(".") or "no extension"
        kinds[kind] = kinds.get(kind, 0) + 1
    common = ", ".join(f"{n} {k}" for k, n in sorted(kinds.items(), key=lambda kv: -kv[1])[:6])
    newest = sorted(entries, key=lambda e: e.stat().st_mtime, reverse=True)[:15]
    sizes = folder_sizes(folders)
    whole = sum(e.stat().st_size for e in files) + sum(sizes.values())
    lines = [f"{place}: {len(files)} files and {len(folders)} folders" + (f" (files: {common})" if common else "") + ".",
             f"In all: {size_of(whole)}." if sizes or not folders else "Folder sizes took too long to add up."]
    if folders:
        within = files_within(place)
        lines.append(f"Counting everything inside its folders too: {within} files." if within is not None else "Too many files inside to count them all.")
    lines.append("Newest first:")
    for e in newest:
        stat = e.stat()
        when = time.strftime("%d %b %Y", time.localtime(stat.st_mtime))
        size = size_of(sizes[str(e)]) if str(e) in sizes else "" if e.is_dir() else size_of(stat.st_size)
        lines.append(f"{e.name}{'/' if e.is_dir() else ''} ({'folder, ' if e.is_dir() else ''}{size}{', ' if size else ''}{when})")
    return "\n".join(lines)


# WORDS THAT ASK TO SEE SOMETHING; WITHOUT ONE, A PAGE OPENING ON SCREEN WOULD BREAK INTO WHAT THEY ARE DOING.
SHOW = re.compile(r"\b(?:open|show|visit|go to|take me|pull up|bring up|launch|display|let me see|watch|play|put on|navigate|load)\b")
REFERENCE = re.compile(r"(?:the |that |this )?(?:link|page|site|website|url|result|article|one|it)")


def as_url(text):
    text = text.strip()
    if "://" in text:
        return text
    if " " not in text and "." in text:
        return "https://" + text
    return "https://www.google.com/search?q=" + urllib.parse.quote_plus(text)


@tool(label="Opening {where}")
def open_link(where: Annotated[str, "a full URL, a site like youtube.com, or words to search for"]):
    """Open a website or a search page in the browser, only when they ask to open, visit or show it. A search result opens by its number. To find something out, use web_search. Never to check mail or messages."""
    said = asked.get()
    if said is not None and not SHOW.search(said.lower()):
        return "Nothing opened: they asked to find something out, not to see a page. Answer from what you found."
    from happy.tools import web

    wanted = where.strip().lower()
    if wanted.isdigit():
        # A SEARCH RESULT BY NUMBER IS ITS REAL ADDRESS; ANY ADDRESS THE MODEL WRITES ITSELF IS INVENTED.
        number = int(wanted)
        if not 1 <= number <= len(web.results):
            return f"There is no search result {number} to open."
        where = web.results[number - 1]["href"]
    elif REFERENCE.fullmatch(wanted):
        if not web.last_read:
            return f"Nothing opened: '{where}' names no page. Give the site, or the number of a search result."
        where = web.last_read
    url = as_url(where)
    if sys.platform == "darwin":
        native.open_path(url)
    else:
        webbrowser.open(url)
    return f"Opened {url}."
