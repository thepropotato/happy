"""THE BROWSER THE PERSON CHOSE, LOOKED UP THE WAY EACH SYSTEM RECORDS IT."""

import json
import shutil
from pathlib import Path

from hands.apps.running import ask

APP = ".app"

# THE SAME FILE `open` READS, SO THIS AND THE BROWSER THAT APPEARS CANNOT DISAGREE.
MAC_HANDLERS = (
    Path.home()
    / "Library/Preferences/com.apple.LaunchServices/com.apple.launchservices.secure.plist"
)
MAC_SCHEME = "https"
MAC_HANDLER_LIST = "LSHandlers"
MAC_HANDLER_SCHEME = "LSHandlerURLScheme"
MAC_HANDLER_ROLE = "LSHandlerRoleAll"

PLUTIL_JSON = ["plutil", "-convert", "json", "-o", "-"]
MDFIND = ["mdfind"]
BUNDLE_QUERY = "kMDItemCFBundleIdentifier == '{bundle}'c"  # c: MATCH ANY CASE.

WINDOWS_CHOICE = [
    "reg",
    "query",
    r"HKCU\Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice",
    "/v",
    "ProgId",
]
WINDOWS_PROGID = "ProgId"
WINDOWS_COMMAND = r"HKCR\{progid}\shell\open\command"

LINUX_CHOICE = ["xdg-settings", "get", "default-web-browser"]
LINUX_DESKTOPS = [
    Path("/usr/share/applications"),
    Path("/usr/local/share/applications"),
    Path.home() / ".local/share/applications",
]
LINUX_EXEC = "Exec="


def mac():
    """THE BUNDLE REGISTERED FOR https, WHICH IS THE ONE `open` WOULD USE."""
    bundle = mac_handler()

    return mac_app(bundle) if bundle else None


def mac_handler():
    """THE BUNDLE ID THE PERSON CHOSE, OR None IF THEY NEVER CHOSE."""
    said = ask(PLUTIL_JSON + [str(MAC_HANDLERS)])

    if not said:
        return None

    try:
        handlers = json.loads(said).get(MAC_HANDLER_LIST, [])
    except json.JSONDecodeError:
        return None

    for entry in handlers:
        if entry.get(MAC_HANDLER_SCHEME) == MAC_SCHEME:
            return entry.get(MAC_HANDLER_ROLE)

    return None


def mac_app(bundle):
    """SPOTLIGHT ONLY IGNORES CASE IF ASKED TO, AND LAUNCH SERVICES WRITES THE ID LOWERCASED
    WHILE THE BUNDLE DOES NOT."""
    found = ask(MDFIND + [BUNDLE_QUERY.format(bundle=bundle)])

    for line in (found or "").splitlines():
        path = Path(line.strip())

        if path.suffix == APP and path.is_dir():
            return path

    return None


def windows():
    """THE PROGRAM BEHIND THE https ASSOCIATION, OUT OF THE REGISTRY."""
    progid = registry_value(ask(WINDOWS_CHOICE), WINDOWS_PROGID)

    if not progid:
        return None

    command = registry_value(ask(["reg", "query", WINDOWS_COMMAND.format(progid=progid)]), None)

    return Path(quoted(command)) if command else None


def registry_value(said, name):
    """THE LAST FIELD OF THE MATCHING reg query LINE."""
    for line in (said or "").splitlines():
        parts = line.split(None, 2)

        if len(parts) == 3 and (name is None or parts[0] == name):
            return parts[2].strip()

    return None


def quoted(command):
    """THE PROGRAM OUT OF A COMMAND LINE, WHICH IS QUOTED WHEN IT HAS SPACES."""
    if command.startswith('"'):
        return command[1:].split('"', 1)[0]

    return command.split(None, 1)[0]


def linux():
    """THE PROGRAM BEHIND THE CHOSEN .desktop ENTRY."""
    said = ask(LINUX_CHOICE)

    if not said:
        return None

    entry = desktop_entry(said.strip())

    if not entry:
        return None

    for line in entry.read_text(errors="ignore").splitlines():
        if line.startswith(LINUX_EXEC):
            # THE Exec LINE CARRIES PLACEHOLDERS LIKE %U. WE WANT THE PROGRAM.
            found = shutil.which(line[len(LINUX_EXEC) :].split()[0])

            return Path(found) if found else None

    return None


def desktop_entry(name):
    for folder in LINUX_DESKTOPS:
        entry = folder / name

        if entry.exists():
            return entry

    return None
