"""
THE MACHINE ITSELF. WHAT IS INSTALLED, WHAT IT IS RUNNING ON, AND OPENING THINGS.

WHAT IS INSTALLED IS A DIRECTORY SCAN AND NOT A QUESTION PUT TO ANYTHING. BOTH
SYSTEMS KEEP A FOLDER MEANT FOR A PERSON TO BROWSE, AND EVERY ENTRY IN IT IS
ALREADY NAMED THE WAY A PERSON WOULD SAY IT. system_profiler AND THE REGISTRY
BOTH KNOW MORE, AND BOTH ARE SLOW ENOUGH TO NOTICE.

MACOS: A .app BUNDLE UNDER /Applications.
WINDOWS: A .lnk SHORTCUT UNDER THE START MENU.

OPENING IS THE SAME IDEA. EVERY SYSTEM ALREADY KNOWS WHICH PROGRAM OWNS A FILE
AND WHICH BROWSER OWNS A LINK, AND IT KNOWS BECAUSE THE PERSON TOLD IT ONCE. SO
A PAGE IS HANDED TO `open` AND ARRIVES IN THE BROWSER THEY ALREADY USE, ALREADY
SIGNED IN, WITH THEIR EXTENSIONS AND THEIR HISTORY. NOTHING HERE PICKS A
BROWSER, AND NOTHING HERE SHOULD EVER LEARN HOW.
"""

import difflib
import getpass
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from langchain_core.tools import tool

MACOS = "darwin"
WINDOWS = "win32"  # ALSO ON 64 BIT. THE NAME NEVER CHANGED.
LINUX = "linux"

MAC_FOLDERS = [
    Path("/Applications"),  # WHAT YOU INSTALLED.
    Path("/System/Applications"),  # WHAT CAME WITH THE MAC.
    Path.home() / "Applications",  # YOURS ALONE, OFTEN EMPTY.
]

# APPS SIT ONE FOLDER DEEP TOO, LIKE /System/Applications/Utilities.
MAC_PATTERNS = ["*.app", "*/*.app"]

MENU = Path("Microsoft/Windows/Start Menu/Programs")

# TWO START MENUS, ONE FOR EVERYONE AND ONE FOR YOU. WINDOWS SHOWS THEM MERGED.
WINDOWS_ROOTS = ["PROGRAMDATA", "APPDATA"]

# THE START MENU NESTS BY PUBLISHER, AND SOMETIMES DEEPER THAN THAT.
WINDOWS_PATTERNS = ["**/*.lnk"]

# WHAT INSTALLERS LEAVE IN THE START MENU BESIDE THE APP. MATCHED WHOLE WORD,
# SO A REAL APP WITH ONE OF THESE INSIDE ITS NAME SURVIVES.
SKIP = {"uninstall", "readme", "documentation"}

SENTENCE = "Apps installed on this computer: "

# HOW CLOSE A SPOKEN NAME HAS TO BE TO A REAL ONE BEFORE WE MENTION IT AT ALL.
# SPEECH ARRIVES MISHEARD MORE OFTEN THAN IT ARRIVES WRONG, SO THIS IS FORGIVING
# ON PURPOSE.
MATCH_CUTOFF = 0.6

# AND HOW CLOSE BEFORE WE OPEN IT WITHOUT ASKING. "slack" AND "clock" SCORE
# EXACTLY 0.6 AGAINST EACH OTHER, AND "photoshop" AND "Photos" SCORE 0.8. A NAME
# THIS SIDE OF THE LINE IS THE SAME NAME MISHEARD; THE OTHER SIDE IS A DIFFERENT
# APP THAT HAPPENS TO RHYME, AND OPENING IT IS WORSE THAN ASKING.
SURE_CUTOFF = 0.85

GIGABYTE = 1024**3

OPEN_TIMEOUT_SECONDS = 15

# HOW LONG A BROWSER GETS TO FAIL BEFORE WE CALL IT LAUNCHED. SEE released().
EARLY_SECONDS = 2

UNSUPPORTED = "Opening a web address is not supported on this platform."

# ASKING THE SYSTEM SOMETHING SMALL ABOUT ITSELF. SHORT, BECAUSE EVERY ONE OF
# THESE IS BETWEEN A PERSON SPEAKING AND A PAGE OPENING.
ASK_TIMEOUT_SECONDS = 5

# WHAT DOES THE OPENING. THE SHELL IS NOT INVOLVED, SO A NAME WITH A SPACE OR A
# QUOTE IN IT IS JUST A NAME.
MAC_OPEN = ["open"]
MAC_OPEN_APP = ["open", "-a"]
WINDOWS_OPEN = ["cmd", "/c", "start", ""]  # THE EMPTY STRING IS start'S TITLE SLOT.
LINUX_OPEN = ["xdg-open"]

# WHAT A BROWSER WILL TAKE. ANYTHING ELSE SAID OUT LOUD, LIKE "youtube.com", IS
# AN ADDRESS WITH THE FRONT MISSING RATHER THAN SOMETHING ELSE ENTIRELY.
SCHEMES = ("http://", "https://")
SCHEME = "https://"

# WHERE MACOS KEEPS WHAT THE PERSON CHOSE. THE SAME FILE `open` READS, SO THE
# ANSWER HERE AND THE BROWSER THAT ACTUALLY APPEARS CANNOT DISAGREE.
MAC_HANDLERS = (
    Path.home()
    / "Library/Preferences/com.apple.LaunchServices/com.apple.launchservices.secure.plist"
)
MAC_SCHEME = "https"
MAC_HANDLER_LIST = "LSHandlers"
MAC_HANDLER_SCHEME = "LSHandlerURLScheme"
MAC_HANDLER_ROLE = "LSHandlerRoleAll"

MAC_INFO = "Contents/Info.plist"
MAC_BINARIES = "Contents/MacOS"
MAC_FRAMEWORKS = "Contents/Frameworks"
MAC_ENGINE = "*Framework.framework"
MAC_EXECUTABLE_KEY = "CFBundleExecutable"
APP = ".app"

PLUTIL_JSON = ["plutil", "-convert", "json", "-o", "-"]
PLUTIL_RAW = ["plutil", "-extract"]
MDFIND = ["mdfind"]
BUNDLE_QUERY = "kMDItemCFBundleIdentifier == '{bundle}'c"  # c: MATCH ANY CASE.

# WHAT THE PERSON CHOSE, ON WINDOWS AND ON LINUX.
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

# CHROMIUM BROWSERS BY THE NAME OF THEIR PROGRAM, FOR THE TWO SYSTEMS WHERE
# THERE IS NO BUNDLE TO LOOK INSIDE. ON MACOS THIS IS NOT GUESSED: SEE engine().
CHROMIUM_NAMES = {
    "chrome",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "msedge",
    "microsoft-edge",
    "brave",
    "brave-browser",
    "opera",
    "opera_gx",
    "vivaldi",
}


def apps():
    """EVERY APP BY THE NAME A PERSON WOULD SAY, SORTED, NO REPEATS."""
    names = set()

    for folder in folders():
        for pattern in patterns():
            names.update(path.stem for path in folder.glob(pattern))

    return sorted((name for name in names if keep(name)), key=str.lower)


def listing():
    """THE SAME LIST AS ONE LINE TO HAND A MODEL. EMPTY WHEN NOTHING IS FOUND."""
    installed = apps()

    return SENTENCE + ", ".join(installed) + "." if installed else ""


def folders():
    """WHERE TO LOOK. EMPTY ON A PLATFORM WE DO NOT KNOW, WHICH FINDS NOTHING."""
    if sys.platform == MACOS:
        return MAC_FOLDERS

    if sys.platform == WINDOWS:
        roots = [os.environ.get(name) for name in WINDOWS_ROOTS]

        return [Path(root) / MENU for root in roots if root]

    return []


def patterns():
    return MAC_PATTERNS if sys.platform == MACOS else WINDOWS_PATTERNS


def keep(name):
    return not SKIP.intersection(name.lower().split())


def resolve(spoken):
    """THE INSTALLED NAME CLOSEST TO WHAT WAS SAID, AND WHETHER IT IS CLOSE
    ENOUGH TO OPEN WITHOUT ASKING FIRST. (None, False) WHEN NOTHING IS NEAR."""
    lowered = {name.lower(): name for name in apps()}
    said = spoken.lower().strip()

    if said in lowered:
        return lowered[said], True

    # A NAME SAID SHORT IS STILL THE NAME, BUT ONLY WHILE IT POINTS AT ONE APP.
    shortened = [name for low, name in lowered.items() if shortens(said, low)]

    if len(shortened) == 1:
        return shortened[0], True

    close = difflib.get_close_matches(said, lowered, n=1, cutoff=MATCH_CUTOFF)

    if not close:
        return (shortened[0], False) if shortened else (None, False)

    ratio = difflib.SequenceMatcher(None, said, close[0]).ratio()

    # SEVERAL APPS ANSWER TO THE SHORT NAME, SO NO ONE OF THEM IS THE ANSWER.
    return lowered[close[0]], ratio >= SURE_CUTOFF and not shortened


def shortens(said, name):
    """WHETHER A NAME SAID SHORT IS STILL THIS NAME. IT HAS TO START A WORD OF
    IT: "chrome" IS Google Chrome, WHILE "word" IS NOT Passwords."""
    at = name.find(said)

    return at == 0 or (at > 0 and name[at - 1] == " ")


def memory_bytes():
    """TOTAL RAM, OR None WHERE WE CANNOT ASK CHEAPLY."""
    if sys.platform == WINDOWS:
        return windows_memory()

    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, ValueError, OSError):
        return None


def windows_memory():
    import ctypes

    class Status(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = Status()
    status.dwLength = ctypes.sizeof(Status)

    try:
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
    except (AttributeError, OSError):
        return None

    return status.ullTotalPhys


def gigabytes(count):
    return f"{count / GIGABYTE:.0f} GB" if count else "unknown"


def launch(command):
    """RUN AN OPENER. RETURNS THE COMPLAINT, OR None WHEN IT WORKED."""
    try:
        done = subprocess.run(
            command, capture_output=True, text=True, timeout=OPEN_TIMEOUT_SECONDS
        )
    except (OSError, subprocess.SubprocessError) as error:
        return f"Could not open it: {error}"

    if done.returncode != 0:
        return f"Could not open it: {(done.stderr or '').strip() or 'the system refused'}"

    return None


def opener():
    """HOW THIS PLATFORM OPENS A PATH OR AN ADDRESS, OR None WHERE WE DO NOT KNOW.

    THE WHOLE POINT OF THE FILE IN ONE FUNCTION: HAND IT OVER AND LET THE SYSTEM
    DECIDE WHAT OWNS IT. IT ALREADY KNOWS, AND IT KNOWS BECAUSE IT WAS TOLD.
    """
    if sys.platform == MACOS:
        return MAC_OPEN

    if sys.platform == WINDOWS:
        return WINDOWS_OPEN

    return LINUX_OPEN if sys.platform.startswith(LINUX) else None


def web_address(said):
    """WHAT WAS SAID, AS SOMETHING A BROWSER WILL TAKE. "youtube.com" IS AN
    ADDRESS WITH ITS FRONT MISSING, AND ANYTHING THAT IS NOT A PAGE AT ALL COMES
    OUT AS A HARMLESS ONE RATHER THAN AS SOMETHING ELSE THE SYSTEM WOULD RUN."""
    address = said.strip()

    if address.lower().startswith(SCHEMES):
        return address

    return SCHEME + address.lstrip("/")


def hand_over(address):
    """GIVE AN ADDRESS TO THE BROWSER THIS PERSON USES, IN THE PROFILE THEY USE.
    RETURNS THE COMPLAINT, OR None WHEN IT WORKED.

    THE SYSTEM'S OWN OPENER IS THE OBVIOUS ANSWER AND IS STILL THE FALLBACK, BUT
    IT ADDRESSES AN APPLICATION RATHER THAN A PROFILE: IT HANDS THE LINK TO
    WHICHEVER COPY OF THAT BROWSER IS ALREADY RUNNING. WHEN A BROWSER ERRAND HAS
    ONE OPEN ON HAPPY'S OWN PROFILE, THAT IS THE WRONG COPY, AND THE PERSON
    WATCHES THEIR LINK ARRIVE IN A WINDOW SIGNED IN TO NOTHING.

    A CHROMIUM STARTED WITHOUT A PROFILE FLAG USES THE ONE ITS OWNER BROWSES
    WITH, AND FORWARDS THE ADDRESS TO THAT WINDOW WHEN IT IS ALREADY OPEN. SO
    WHERE THE BROWSER IS KNOWN, THE PROFILE IS SAID OUT LOUD RATHER THAN LEFT TO
    WHATEVER HAPPENS TO BE RUNNING.
    """
    binary = drivable_browser()

    if binary is None:  # SAFARI, FIREFOX, OR A PLATFORM WE CANNOT READ. HAND IT OVER.
        how = opener()

        return launch(how + [address]) if how else UNSUPPORTED

    return released([str(binary), address])


def released(command):
    """START SOMETHING AND DO NOT WAIT FOR IT TO FINISH.

    A BROWSER THAT WAS NOT ALREADY RUNNING BECOMES THE BROWSER AND DOES NOT
    RETURN UNTIL IT IS CLOSED, SO WAITING WOULD MEAN WAITING ALL AFTERNOON. ONE
    THAT WAS RUNNING FORWARDS THE ADDRESS AND EXITS AT ONCE. BOTH ARE SUCCESS.

    THE EXIT CODE IS NOT THE TEST AND MUST NOT BE: OPERA SAYS "Opening in
    existing browser session." AND EXITS 24 HAVING DONE EXACTLY WHAT WAS ASKED.
    A BROWSER THAT COULD NOT DO IT SAYS SO ON STDERR, SO THAT IS THE TEST.
    """
    try:
        started = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            start_new_session=True,  # NOT OURS TO OUTLIVE. IT IS THE PERSON'S BROWSER.
            text=True,
        )
    except OSError as error:
        return f"Could not open it: {error}"

    try:
        _, complaint = started.communicate(timeout=EARLY_SECONDS)
    except subprocess.TimeoutExpired:
        return None  # STILL GOING, WHICH MEANS IT IS THE BROWSER NOW.

    said = (complaint or "").strip()

    return f"Could not open it: {said[:200]}" if said else None


def ask(command):
    """RUN SOMETHING SMALL AND HAND BACK WHAT IT SAID, OR None IF IT WOULD NOT."""
    try:
        done = subprocess.run(
            command, capture_output=True, text=True, timeout=ASK_TIMEOUT_SECONDS
        )
    except (OSError, subprocess.SubprocessError):
        return None

    return done.stdout if done.returncode == 0 else None


# THE DEFAULT BROWSER, BY PATH. NOTHING ABOVE THIS LINE NEEDS IT: `open` FINDS
# THE BROWSER ON ITS OWN AND IS ALWAYS THE BETTER ANSWER. IT IS HERE FOR THE ONE
# CALLER THAT CANNOT USE `open` AT ALL, THE BROWSER ERRAND, WHICH HAS TO START A
# BROWSER ITSELF AND THEREFORE HAS TO BE TOLD WHICH ONE THE PERSON USES.


def default_browser():
    """THE APP THAT OPENS LINKS ON THIS COMPUTER, OR None IF NOBODY EVER SAID.

    None IS NOT A FAILURE. IT MEANS THE CHOICE WAS NEVER CHANGED FROM WHATEVER
    CAME WITH THE MACHINE, AND EVERY CALLER HERE HAS SOMETHING SENSIBLE TO DO
    WITH THAT.
    """
    if sys.platform == MACOS:
        return mac_browser()

    if sys.platform == WINDOWS:
        return windows_browser()

    return linux_browser() if sys.platform.startswith(LINUX) else None


def drivable_browser():
    """THE DEFAULT BROWSER'S PROGRAM WHEN IT IS ONE THAT CAN BE DRIVEN, ELSE None.

    ONLY CHROMIUM BROWSERS SPEAK THE DEBUGGING PROTOCOL A BROWSER ERRAND STEERS
    THEM WITH. CHROME, EDGE, BRAVE, VIVALDI AND OPERA ALL DO. SAFARI AND FIREFOX
    DO NOT, AND SAYING SO HERE IS BETTER THAN LAUNCHING ONE AND WATCHING IT SIT
    THERE.
    """
    chosen = default_browser()

    return program(chosen) if chosen and engine(chosen) else None


def program(app):
    """THE THING TO ACTUALLY RUN, OUT OF WHATEVER THE PLATFORM CALLS AN APP."""
    if sys.platform != MACOS:
        return app  # ELSEWHERE THE ANSWER WAS ALREADY THE PROGRAM ITSELF.

    named = ask(PLUTIL_RAW + [MAC_EXECUTABLE_KEY, "raw", str(app / MAC_INFO)])

    if not named:
        return None

    # NOT ALWAYS THE BUNDLE'S OWN NAME: "Opera GX.app" RUNS A PROGRAM CALLED
    # "Opera", AND GUESSING FROM THE FOLDER WOULD FIND NOTHING.
    binary = app / MAC_BINARIES / named.strip()

    return binary if binary.exists() else None


def engine(app):
    """WHETHER THIS BROWSER IS A CHROMIUM ONE."""
    if sys.platform == MACOS:
        # EVERY CHROMIUM BUNDLE SHIPS ITS ENGINE AS A FRAMEWORK BESIDE THE
        # PROGRAM, AND NOTHING ELSE DOES. THAT IS A FACT ABOUT THE BUNDLE IN
        # FRONT OF US RATHER THAN A LIST OF BROWSERS WE HAPPEN TO HAVE HEARD OF,
        # SO A BROWSER NOBODY HAS THOUGHT OF YET STILL ANSWERS CORRECTLY.
        return any((Path(app) / MAC_FRAMEWORKS).glob(MAC_ENGINE))

    # NO BUNDLE TO LOOK INSIDE, SO THIS ONE IS A LIST AND WILL BE WRONG ABOUT
    # ANYTHING NEW. IT FAILS BY SAYING NO, WHICH COSTS A FALLBACK AND NOT A BUG.
    return Path(app).stem.lower() in CHROMIUM_NAMES


def mac_browser():
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

    return None  # NEVER CHANGED, SO THE SYSTEM'S OWN BROWSER IS STILL IT.


def mac_app(bundle):
    """THE .app FOR A BUNDLE ID. SPOTLIGHT KNOWS, AND WILL ONLY IGNORE CASE IF
    ASKED TO: LAUNCH SERVICES WRITES THE ID LOWERCASED AND THE BUNDLE ITSELF
    DOES NOT, SO AN EXACT MATCH FINDS NOTHING."""
    found = ask(MDFIND + [BUNDLE_QUERY.format(bundle=bundle)])

    for line in (found or "").splitlines():
        path = Path(line.strip())

        if path.suffix == APP and path.is_dir():
            return path

    return None


def windows_browser():
    """THE PROGRAM BEHIND THE https ASSOCIATION, OUT OF THE REGISTRY."""
    said = ask(WINDOWS_CHOICE)
    progid = registry_value(said, WINDOWS_PROGID)

    if not progid:
        return None

    command = registry_value(ask(["reg", "query", WINDOWS_COMMAND.format(progid=progid)]), None)

    return Path(quoted(command)) if command else None


def registry_value(said, name):
    """THE LAST FIELD OF THE MATCHING reg query LINE. None NAME TAKES THE FIRST LINE
    THAT HAS A VALUE AT ALL, WHICH IS HOW THE DEFAULT ENTRY IS WRITTEN."""
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


def linux_browser():
    """THE PROGRAM BEHIND THE CHOSEN .desktop ENTRY."""
    said = ask(LINUX_CHOICE)

    if not said:
        return None

    entry = desktop_entry(said.strip())

    if not entry:
        return None

    for line in entry.read_text(errors="ignore").splitlines():
        if line.startswith(LINUX_EXEC):
            # THE Exec LINE CARRIES PLACEHOLDERS LIKE %U FOR THE ADDRESS. WE ARE
            # AFTER THE PROGRAM AND NOT THE COMMAND, SO ONLY THE FIRST WORD.
            found = shutil.which(line[len(LINUX_EXEC) :].split()[0])

            return Path(found) if found else None

    return None


def desktop_entry(name):
    for folder in LINUX_DESKTOPS:
        entry = folder / name

        if entry.exists():
            return entry

    return None


# TOOLS. THE DESCRIPTIONS BELOW ARE READ BY THE MODEL, NOT BY US, SO THEY ARE
# WRITTEN AS PLAIN PROSE RATHER THAN AS COMMENTS.


@tool
def list_installed_apps() -> str:
    """List every application installed on this computer, by the name a person
    would say out loud. Use this when you are unsure whether an app exists or
    what it is called. If an app is not in this list, it is not installed."""
    installed = apps()

    return ", ".join(installed) if installed else "No applications found."


@tool
def system_info() -> str:
    """Report what this computer is: operating system and version, processor
    architecture, number of CPU cores, total memory, free disk space, hostname
    and the logged in user. Use this for questions about the machine itself."""
    total, _, free = shutil.disk_usage(Path.home())

    facts = [
        f"Operating system: {platform.system()} {platform.release()}",
        f"Architecture: {platform.machine()}",
        f"CPU cores: {os.cpu_count() or 'unknown'}",
        f"Memory: {gigabytes(memory_bytes())}",
        f"Disk: {gigabytes(free)} free of {gigabytes(total)}",
        f"Hostname: {platform.node()}",
        f"User: {getpass.getuser()}",
    ]

    return "\n".join(facts)


@tool
def open_app(name: str) -> str:
    """Open an installed application by name, for example "Visual Studio Code"
    or "Calculator". A short name like "chrome" is enough. Prefer this over a
    shell command whenever the user asks to open or launch an app.

    This opens things. Never use it to find out whether an app is installed:
    that is list_installed_apps, and it changes nothing on screen.

    This is for opening an application itself. If the user wants a web page, a
    video, a search or anything else with an address, use open_url instead: it
    goes to the browser they already use, and never opens the wrong one."""
    match, sure = resolve(name)

    if match is None:
        return f"There is no app called {name} on this computer."

    if not sure:
        return (
            f"There is no app called {name} on this computer. The nearest one "
            f"installed is {match}, which is a different app. Nothing was opened. "
            f"Ask whether {match} is what was meant before opening it."
        )

    if sys.platform == MACOS:
        problem = launch(MAC_OPEN_APP + [match])
    elif sys.platform == WINDOWS:
        problem = launch(WINDOWS_OPEN + [match])
    else:
        return "Opening apps is not supported on this platform."

    return problem or f"Opened {match}."


@tool
def open_path(path: str) -> str:
    """Open a file or folder in whatever application the system uses for it: a
    folder opens in the file browser, a document opens in its editor. Accepts
    paths like "~/Downloads" or "/Users/me/notes.txt". Use this when the user
    asks to open, show or bring up a folder or a file."""
    target = Path(path).expanduser()

    if not target.exists():
        return f"There is nothing at {target}."

    how = opener()

    if how is None:
        return "Opening paths is not supported on this platform."

    return launch(how + [str(target)]) or f"Opened {target}."


@tool
def open_url(url: str) -> str:
    """Open a web address in the browser the user already uses, exactly as if
    they had clicked the link themselves. Use this for anything on the web that
    an address alone will reach: a site, a video, a search, a web app. Accepts
    "youtube.com" or a full address.

    Their browser is already signed in to their accounts, so this is how you
    reach anything of theirs on the web. Prefer it over opening a browser
    application and typing, which is never right, and over the browser errand
    tool, which is for pages that take several steps to work through."""
    address = web_address(url)

    return hand_over(address) or f"Opened {address}."


TOOLS = [list_installed_apps, system_info, open_app, open_path, open_url]


if __name__ == "__main__":  # WHAT IS INSTALLED, AND WHICH BROWSER THE LINKS GO TO.
    chosen = default_browser()

    print(f"default browser: {chosen or 'never chosen, the system default'}")
    print(f"drivable: {drivable_browser() or 'no, an errand will pick its own'}\n")

    for name in apps():
        print(name)
