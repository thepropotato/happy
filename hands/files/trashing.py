"""PUTTING SOMETHING IN THE TRASH, WHERE THE PERSON CAN TAKE IT BACK OUT AGAIN."""

import os
import sys
import time
from pathlib import Path
from urllib.parse import quote

from hands.controls.commands import on_mac, on_windows, osascript, powershell, run
from hands.files.finding import dig, hunt

# THE FOLDERS A HOME IS BUILT AROUND. TRASHING ONE IS RECOVERABLE AND STILL NOT WHAT ANYBODY
# MEANS BY DELETE A FOLDER, SO IT IS THE ONE THING THIS SAYS NO TO OUTRIGHT. EACH SYSTEM NAMES
# ITS OWN, AND A MAC'S Movies IS A PC'S Videos, SO ONE LIST FOR ALL THREE GUARDS NONE OF THEM.
ALWAYS = {".ssh", ".config", ".local", ".Trash", "Dropbox", "iCloud Drive", "OneDrive"}

MAC_KEPT = {
    "Desktop", "Documents", "Downloads", "Pictures", "Movies", "Music",
    "Library", "Applications", "Public", "Sites",
}

WINDOWS_KEPT = {
    "Desktop", "Documents", "Downloads", "Pictures", "Videos", "Music",
    "AppData", "Favorites", "Links", "Contacts", "Searches", "Saved Games",
}

LINUX_KEPT = {
    "Desktop", "Documents", "Downloads", "Pictures", "Videos", "Music",
    "Public", "Templates",
}

OUTSIDE = (
    "{path} is outside your own folders, so I will not touch it. I only move things from "
    "inside {home} to the Trash."
)

ITSELF = "That is the home folder itself, which is everything you have. I will not move it."

BUILT_IN = (
    "{name} is one of the folders this computer is built around, not a folder somebody made. "
    "I will not move it. Name something inside it instead."
)

GONE = "There is nothing at {path}."

SEVERAL = "Several things are called {name}: {listing}. Say which one and I will move that one."

NOTHING = "There is nothing called {name}."

DONE = "Moved {what} to the Trash.{held} It is still there if you want it back."

HELD = " It had {count} things in it."

ONE_THING = " It had one thing in it."

FAILED = "Could not move {what} to the Trash: {trouble}"

UNSUPPORTED = "I do not know where the Trash is on this computer, so I have not moved anything."

# WHERE A LINUX DESKTOP KEEPS IT, AND THE NOTE IT WANTS BESIDE EVERY THING IN IT.
TRASH = ".local/share/Trash"

INFO = "[Trash Info]\nPath={where}\nDeletionDate={when}\n"

# THE FOUR WAYS WINDOWS DELETES SOMETHING OUTRIGHT WHILE BEING ASKED TO RECYCLE IT, AND THE TWO
# WAYS THE ASKING ITSELF FAILS. IT WARNS NOBODY AND REPORTS SUCCESS, SO THE ONLY PLACE TO CATCH
# IT IS BEFORE THE DELETE, AND ANYTHING THAT CANNOT BE CHECKED COUNTS AS UNSAFE.
NUKED = {
    "NETWORK": "it is on a network drive, and Windows keeps no Recycle Bin on those",
    "NOBIN": "the drive it is on has no Recycle Bin",
    "POLICY": "this computer is set to delete things outright rather than recycle them",
    "NUKE": "the Recycle Bin is switched off for that drive",
    "UNKNOWNDRIVE": "I could not tell what kind of drive it is on",
    "UNKNOWN": "I could not check whether the Recycle Bin would take it",
}

BIGGER = "it is {size} and that drive's Recycle Bin only holds {cap}, so Windows would bin it"

WOULD_VANISH = (
    "{name} would not reach the Recycle Bin: {why}. Deleting it would be final and there would "
    "be nothing to put back, so I have not touched it. Move it somewhere else if you want it "
    "gone from here, or delete it in File Explorer yourself if you really mean forever."
)

# ONE SCRIPT, ONE WORD BACK. SPLIT INTO SEPARATE CHECKS IT WOULD BE FIVE POWERSHELL LAUNCHES.
ASKING = r"""
$ErrorActionPreference = 'Stop'
try {
  $p = '%s'
  if ($p.StartsWith('\\')) { 'NETWORK'; exit 0 }

  $letter = [System.IO.Path]::GetPathRoot($p).Substring(0, 2)
  $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$letter'" -EA SilentlyContinue
  if (-not $disk) { 'UNKNOWNDRIVE'; exit 0 }
  if ($disk.DriveType -ne 3) { 'NOBIN'; exit 0 }

  $pol = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer' `
         -Name NoRecycleFiles -EA SilentlyContinue
  if ($pol.NoRecycleFiles -eq 1) { 'POLICY'; exit 0 }

  $id = (Get-Volume -FilePath $p -EA SilentlyContinue).UniqueId
  if (-not $id) {
    $id = (Get-CimInstance Win32_Volume -Filter "DriveLetter='$letter'" -EA SilentlyContinue).DeviceID
  }
  if ($id -notmatch '(\{[0-9A-Fa-f-]+\})') { 'UNKNOWN'; exit 0 }

  # NO KEY AT ALL IS THE ORDINARY CASE: IT MEANS NOBODY CHANGED ANYTHING, NOT THAT NOTHING IS KNOWN.
  $bin = Get-ItemProperty ('HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\BitBucket\Volume\' `
         + $matches[1]) -EA SilentlyContinue
  if ($bin.NukeOnDelete -eq 1) { 'NUKE'; exit 0 }

  $cap = $bin.MaxCapacity
  if ($cap) { $cap = [int64]$cap * 1MB } else {
    # WHAT WINDOWS USES WHEN NOBODY HAS SET ONE: A TENTH OF THE FIRST 40 GB, A TWENTIETH OF THE REST.
    $size = [int64]$disk.Size
    $cap = ([Math]::Min($size, 40GB) * 0.10) + ([Math]::Max(0, $size - 40GB) * 0.05)
  }

  $item = Get-Item -LiteralPath $p -Force
  if ($item.PSIsContainer) {
    $bytes = (Get-ChildItem -LiteralPath $p -Recurse -Force -File -EA SilentlyContinue |
              Measure-Object -Sum Length).Sum
  } else { $bytes = $item.Length }
  if (-not $bytes) { $bytes = 0 }

  if ($bytes -ge $cap) { "TOOBIG $bytes $([int64]$cap)"; exit 0 }
  'SAFE'
} catch { 'UNKNOWN'; exit 0 }
"""

# A FOLDER OF MANY THOUSANDS HAS TO BE ADDED UP BEFORE ANY OF THIS CAN BE ANSWERED.
ASKING_SECONDS = 90


def meant(where):
    """THE ONE THING where NAMES, OR NOTHING AT ALL.

    READING PICKS THE FIRST OF SEVERAL MATCHES AND SAYS SO. THIS NEVER PICKS: THE COST OF
    READING THE WRONG FILE IS A WASTED SENTENCE, AND THE COST OF TRASHING THE WRONG ONE IS
    SOMEBODY ELSE'S WORK."""
    said = (where or "").strip()

    if not said:
        return None, NOTHING.format(name="nothing")

    direct = Path(said).expanduser()

    if direct.exists():
        return direct, None

    hits = hunt(said) + dig(said)
    exact = [each for each in hits if each.name.lower() == said.lower()]
    found = exact or hits

    if not found:
        return None, NOTHING.format(name=said)

    if len(found) > 1:
        listing = ", ".join(str(each) for each in found[:5])

        return None, SEVERAL.format(name=said, listing=listing)

    return found[0], None


def kept():
    """THE NAMES THIS SYSTEM'S HOME IS BUILT AROUND."""
    if on_mac():
        return ALWAYS | MAC_KEPT

    if on_windows():
        return ALWAYS | WINDOWS_KEPT

    return ALWAYS | LINUX_KEPT


def whole(path):
    """THE FULL PATH, WITHOUT FOLLOWING A LINK TO WHAT IT POINTS AT.

    resolve() FOLLOWS, AND A SHORTCUT HANDED TO IT COMES BACK AS SOMEBODY'S REAL FOLDER, WHICH
    IS THEN THE THING THAT GETS TRASHED WHILE THE SHORTCUT STAYS ON THE DESKTOP."""
    return os.path.abspath(os.path.expanduser(str(path)))


def allowed(path):
    """WHY THIS ONE IS NOT MOVING, OR None. THE ONLY REFUSALS THERE ARE."""
    home = Path.home().resolve()

    # RESOLVED ONLY TO ASK WHERE IT REALLY SITS. WHAT MOVES IS THE PATH AS GIVEN, SO A LINK
    # GOES TO THE TRASH AS A LINK AND WHATEVER IT POINTS AT STAYS WHERE IT IS.
    try:
        real = path.resolve()
    except OSError:
        return GONE.format(path=path)

    if real == home:
        return ITSELF

    if home not in real.parents:
        return OUTSIDE.format(path=real, home=home)

    if real.parent == home and real.name in kept():
        return BUILT_IN.format(name=real.name)

    return None


def named(path):
    """WHAT TO CALL IT OUT LOUD, AND HOW MUCH WENT WITH IT. A FOLDER'S COUNT IS THE ONLY WARNING
    ANYBODY GETS THAT MORE WENT THAN THEY PICTURED, AND IT CANNOT BE COUNTED AFTERWARDS."""
    # A LINK LOOKS LIKE THE FOLDER IT POINTS AT AND COUNTS ITS THINGS, AND NONE OF THEM MOVED.
    if path.is_symlink():
        return f"the shortcut {path.name}", ""

    if not path.is_dir():
        return path.name, ""

    try:
        inside = len(list(path.iterdir()))
    except OSError:
        return f"the folder {path.name}", ""

    if inside == 1:
        return f"the folder {path.name}", ONE_THING

    return f"the folder {path.name}", HELD.format(count=inside) if inside else ""


def sized(count):
    """A NUMBER OF BYTES IN WORDS SOMEBODY WOULD SAY."""
    for unit, step in [("GB", 1024**3), ("MB", 1024**2), ("KB", 1024)]:
        if count >= step:
            return f"{count / step:.1f} {unit}".replace(".0 ", " ")

    return f"{count} bytes"


def recoverable(path):
    """WHY THIS WOULD NOT SURVIVE THE DELETE, OR None.

    ONLY WINDOWS HAS ANYTHING TO ANSWER HERE. A MAC'S TRASH TAKES WHAT IT IS GIVEN OR REFUSES,
    AND LINUX IS A MOVE THAT EITHER WORKS OR RAISES. WINDOWS IS THE ONE THAT QUIETLY DOES THE
    OTHER THING AND REPORTS SUCCESS."""
    if not on_windows():
        return None

    said = run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ASKING % whole(path).replace("'", "''")],
        timeout=ASKING_SECONDS,
    )

    # THE SCRIPT ANSWERS EVEN WHEN IT FAILS, SO NOTHING BACK AT ALL IS ITSELF AN UNKNOWN.
    words = (said or "UNKNOWN").split()
    verdict = words[0] if words else "UNKNOWN"

    if verdict == "SAFE":
        return None

    if verdict == "TOOBIG" and len(words) == 3:
        return BIGGER.format(size=sized(int(words[1])), cap=sized(int(words[2])))

    return NUKED.get(verdict, NUKED["UNKNOWN"])


def trash(path):
    """PUT path IN THE TRASH. THE COMPLAINT IF IT DID NOT GO, OR None."""
    if on_mac():
        return mac(path)

    if on_windows():
        return windows(path)

    return linux(path)


def mac(path):
    """THE SAME CALL THE FINDER MAKES, WHICH ASKS NOBODY AND LEAVES PUT BACK WORKING."""
    try:
        from Foundation import NSURL, NSFileManager
    except ImportError:
        # osascript IS THE FALLBACK, NOT THE PLAN: IT WANTS THE FINDER RUNNING AND CONSENT
        # TO DRIVE IT, WHICH IS TWO WAYS TO FAIL THAT THE FRAMEWORK CALL DOES NOT HAVE.
        said = osascript(f'tell application "Finder" to delete POSIX file "{whole(path)}"')

        return None if said is not None else "the Finder would not do it"

    where = NSURL.fileURLWithPath_(str(path))
    went, _, trouble = NSFileManager.defaultManager().trashItemAtURL_resultingItemURL_error_(
        where, None, None
    )

    if went:
        return None

    return trouble.localizedDescription() if trouble else "the system would not do it"


def windows(path):
    """THE RECYCLE BIN, THROUGH THE ONE CALL WINDOWS EXPOSES FOR IT.

    THIS ASKS FOR THE BIN AND IS NOT TOLD WHEN IT DOES NOT GET IT, SO recoverable() HAS TO HAVE
    RUN FIRST. THE FLAG THAT WOULD HAVE WARNED, FOF_WANTNUKEWARNING, ONLY EXISTS ON THE RAW SHELL
    CALL AND ONLY WARNS BY PUTTING A DIALOG ON THE SCREEN, WHICH IS A YES TO WAIT ON."""
    quoted = whole(path).replace("'", "''")
    call = "DeleteDirectory" if path.is_dir() else "DeleteFile"

    # WITHOUT THE try A THROWN .NET ERROR CAN STILL LEAVE POWERSHELL EXITING ZERO, AND A FAILED
    # DELETE WOULD BE REPORTED AS A DONE ONE.
    said = powershell(
        "$ErrorActionPreference='Stop'; Add-Type -AssemblyName Microsoft.VisualBasic; "
        f"try {{ [Microsoft.VisualBasic.FileIO.FileSystem]::{call}("
        f"'{quoted}','OnlyErrorDialogs','SendToRecycleBin') }} catch {{ exit 1 }}"
    )

    return None if said is not None else "the Recycle Bin would not take it"


def linux(path):
    """THE TRASH EVERY LINUX DESKTOP AGREES ON: THE THING ITSELF, AND A NOTE SAYING WHERE IT
    CAME FROM, WHICH IS WHAT PUT BACK READS."""
    home = Path.home()
    files, notes = home / TRASH / "files", home / TRASH / "info"

    try:
        files.mkdir(parents=True, exist_ok=True)
        notes.mkdir(parents=True, exist_ok=True)
    except OSError as trouble:
        return str(trouble)

    landing = free(files, path.name)
    when = time.strftime("%Y-%m-%dT%H:%M:%S")

    try:
        (notes / f"{landing.name}.trashinfo").write_text(
            INFO.format(where=quote(whole(path)), when=when)
        )
        os.rename(path, landing)
    except OSError as trouble:
        return str(trouble)

    return None


def free(folder, name):
    """A NAME NOTHING IN THE TRASH IS USING, SO TRASHING TWO THINGS CALLED notes.txt KEEPS BOTH."""
    landing = folder / name
    stem, suffix = Path(name).stem, Path(name).suffix

    count = 2

    while landing.exists():
        landing = folder / f"{stem} {count}{suffix}"
        count += 1

    return landing


def supported():
    return on_mac() or on_windows() or sys.platform.startswith("linux")
