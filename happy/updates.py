"""Keeps an installed Happy current: finds a newer release on GitHub, fetches it in the background, checks it against
the release's SHA256SUMS.txt, and installs it while Happy is idle, then starts the new one.

Only a Happy installed from the DMG or the Windows installer updates itself; its launcher says where it lives
(HAPPY_BUNDLE on a Mac, HAPPY_INSTALLED on Windows). A copy run from source is updated with git.
"""

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from importlib import metadata
from pathlib import Path

import httpx

from happy import paths

log = logging.getLogger("happy.updates")

REPO = "thepropotato/happy"
LATEST = os.environ.get("HAPPY_UPDATE_URL") or f"https://api.github.com/repos/{REPO}/releases/latest"
ASSET = "Happy.dmg" if sys.platform == "darwin" else "Happy-Setup.exe"
DOWNLOADS = paths.HOME / "updates"


def current():
    """This Happy's version: the stamp an installed copy carries, else the package's own."""
    stamp = paths.REPO / ".app-version"
    if stamp.exists():
        return stamp.read_text(encoding="utf-8").strip()
    try:
        return metadata.version("happy")
    except metadata.PackageNotFoundError:
        return "0"


def numbers(version):
    return tuple(int(part) for part in re.findall(r"\d+", str(version).split("-")[0])[:3])


def newer(candidate, than):
    return numbers(candidate) > numbers(than)


def installed_at():
    """Where this Happy was installed from, when it can replace itself: the .app on a Mac, the program folder on Windows."""
    if sys.platform == "darwin":
        bundle = os.environ.get("HAPPY_BUNDLE") or ""
        return Path(bundle) if bundle.endswith(".app") and Path(bundle).is_dir() else None
    if sys.platform == "win32":
        folder = os.environ.get("HAPPY_INSTALLED") or ""
        return Path(folder) if folder and (Path(folder) / "launch.ps1").exists() else None
    return None


def login_command():
    """How Happy is started at login: through the installed app, so it can set up and update, else straight from source."""
    where = installed_at()
    if where and sys.platform == "darwin":
        return ["/usr/bin/open", "-a", str(where)]
    if where and sys.platform == "win32":
        return [str(Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"),
                "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", str(where / "launch.ps1")]
    return [sys.executable, "-m", "happy", "run", "--quiet"]


def latest():
    """The newest published release as {"version", "url", "sums"}, or None when there is none for this computer."""
    reply = httpx.get(LATEST, timeout=20, follow_redirects=True, headers={"Accept": "application/vnd.github+json"})
    reply.raise_for_status()
    release = reply.json()
    files = {asset["name"]: asset["browser_download_url"] for asset in release.get("assets", [])}
    if ASSET not in files or "SHA256SUMS.txt" not in files:
        return None
    return {"version": release.get("tag_name", "").lstrip("v"), "url": files[ASSET], "sums": files["SHA256SUMS.txt"],
            "notes": (release.get("body") or "")[:2000]}


def fetch(release, progress=lambda done, whole: None):
    """Downloads the release's file for this computer and returns its path, only if its SHA-256 matches the published one."""
    sums = httpx.get(release["sums"], timeout=20, follow_redirects=True).text
    wanted = next((line.split()[0].lower() for line in sums.splitlines() if line.strip().endswith(ASSET)), None)
    if not wanted:
        raise ValueError(f"the release lists no checksum for {ASSET}")
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    target = DOWNLOADS / f"{release['version']}-{ASSET}"
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == wanted:
        return target
    partial = target.with_suffix(target.suffix + ".part")
    digest = hashlib.sha256()
    with httpx.stream("GET", release["url"], timeout=60, follow_redirects=True) as reply:
        reply.raise_for_status()
        whole, done = int(reply.headers.get("content-length") or 0), 0
        with open(partial, "wb") as out:
            for chunk in reply.iter_bytes(1 << 20):
                out.write(chunk)
                digest.update(chunk)
                done += len(chunk)
                progress(done, whole)
    # A FILE THAT DOES NOT MATCH THE PUBLISHED CHECKSUM IS NEVER OPENED, LET ALONE INSTALLED.
    if digest.hexdigest() != wanted:
        partial.unlink(missing_ok=True)
        raise ValueError("the download did not match its published checksum")
    partial.replace(target)
    for old in DOWNLOADS.glob(f"*-{ASSET}"):
        if old != target:
            old.unlink(missing_ok=True)
    return target


def quiet():
    return {"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS} if sys.platform == "win32" else {}


def install_mac(dmg, bundle):
    """Swaps the .app for the one in the DMG: copied beside it first, so a failure leaves the old one whole."""
    mount = Path(tempfile.mkdtemp(prefix="happy-update-"))
    try:
        subprocess.run(["hdiutil", "attach", "-nobrowse", "-noautoopen", "-readonly", "-mountpoint", str(mount), str(dmg)],
                       check=True, capture_output=True, timeout=120)
        fresh = bundle.with_name(bundle.name + ".new")
        stale = bundle.with_name(bundle.name + ".old")
        shutil.rmtree(fresh, ignore_errors=True)
        shutil.rmtree(stale, ignore_errors=True)
        subprocess.run(["ditto", str(mount / "Happy.app"), str(fresh)], check=True, capture_output=True, timeout=300)
        bundle.rename(stale)
        fresh.rename(bundle)
        shutil.rmtree(stale, ignore_errors=True)
    finally:
        subprocess.run(["hdiutil", "detach", "-quiet", str(mount)], capture_output=True, timeout=60)
        shutil.rmtree(mount, ignore_errors=True)
    # THE NEW HAPPY STARTS ONCE THIS ONE HAS GONE; ITS LAUNCHER SEES THE NEW VERSION AND SHOWS THE UPDATE WINDOW.
    subprocess.Popen(["/bin/sh", "-c", 'sleep 3; /usr/bin/open -n "$1"', "relaunch", str(bundle)],
                     start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def install_windows(setup, folder):
    """Runs the new installer silently once this Happy has gone, then opens Happy the way the Start menu does."""
    def quoted(path):
        # A POWERSHELL STRING IN SINGLE QUOTES ONLY ESCAPES A QUOTE, BY DOUBLING IT, AS IN A NAME LIKE O'BRIEN.
        return "'" + str(path).replace("'", "''") + "'"

    launcher = folder / "launch.ps1"
    script = (f"Start-Sleep 3; Start-Process {quoted(setup)} -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART' -Wait; "
              f"& powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File {quoted(launcher)}")
    subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-Command", script],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **quiet())


def install(downloaded):
    """Installs a fetched update; True when the new Happy is on its way and this one should quit."""
    where = installed_at()
    if not where:
        return False
    if sys.platform == "darwin":
        if not os.access(where.parent, os.W_OK):
            raise PermissionError(f"Happy can't replace itself in {where.parent}")
        install_mac(downloaded, where)
    else:
        install_windows(downloaded, where)
    return True


def remember(state):
    try:
        (paths.HOME / "update.json").write_text(json.dumps(state), encoding="utf-8")
    except OSError:
        pass


def recalled():
    try:
        return json.loads((paths.HOME / "update.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


class Keeper:
    """The background half: checks soon after Happy starts and then every few hours, fetches what is newer, and
    installs it once Happy has been quiet a while, so an update never lands in the middle of a conversation."""

    FIRST = 60
    EVERY = 6 * 3600
    QUIET = 5 * 60

    def __init__(self, quiet_for, quit, changed=lambda state: None):
        import threading

        self.quiet_for = quiet_for
        self.quit = quit
        self.changed = changed
        self.wake = threading.Event()
        self.own = installed_at() is not None
        self.state = {"version": current(), "state": "idle", "text": "", "own": self.own}
        done = recalled()
        if done.get("to") and done.get("to") == current():
            self.state.update(state="updated", text=f"Updated from {done.get('from')} to {current()}.")
            remember({})

    def start(self):
        import threading

        threading.Thread(target=self.run, name="updates", daemon=True).start()

    def check_now(self):
        self.wake.set()

    def tell(self, state, text=""):
        self.state = {**self.state, "state": state, "text": text}
        self.changed(self.state)

    def run(self):
        self.wake.wait(self.FIRST)
        while True:
            self.wake.clear()
            try:
                self.cycle()
            except Exception as error:
                log.warning("could not update: %s", error)
                self.tell("failed", f"Couldn't check for updates: {error}")
            self.wake.wait(self.EVERY)

    def cycle(self):
        from happy.config import Config

        self.tell("checking", "Checking for updates…")
        release = latest()
        if not release or not newer(release["version"], current()):
            return self.tell("current", f"Happy {current()} is the newest.")
        version = release["version"]
        if not self.own:
            return self.tell("available", f"Happy {version} is out. This copy runs from source, so update it with git pull.")
        if Config().get("auto_update") is False:
            return self.tell("available", f"Happy {version} is out. Turn on automatic updates, or download it from the website.")
        shown = [0]

        def progress(done, whole):
            percent = done * 100 // whole if whole else 0
            if percent >= shown[0] + 10:
                shown[0] = percent
                self.tell("downloading", f"Downloading Happy {version} ({percent}%)…")

        self.tell("downloading", f"Downloading Happy {version}…")
        downloaded = fetch(release, progress)
        # READY, BUT ONLY INSTALLED ONCE NOTHING HAS BEEN SAID OR ASKED FOR A WHILE.
        self.tell("ready", f"Happy {version} is ready. It installs the next time Happy is quiet for a few minutes.")
        while self.quiet_for() < self.QUIET and not self.wake.is_set():
            self.wake.wait(30)
        self.wake.clear()
        self.tell("installing", f"Installing Happy {version}. Happy restarts in a moment…")
        remember({"from": current(), "to": version})
        if install(downloaded):
            self.quit()
        else:
            remember({})
            self.tell("failed", "This copy of Happy can't replace itself; download the new version from the website.")
