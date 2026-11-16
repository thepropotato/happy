"""The page inside the person's own Chrome, worked through agent-browser over the DevTools protocol; the browser's own bar and menus stay with the OS controls."""

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from happy.system import Failed

log = logging.getLogger("happy.web")

BROWSERS = ("google chrome", "chrome", "brave", "microsoft edge", "edge", "arc", "chromium", "vivaldi")
FIELDS = {"textbox", "searchbox", "combobox", "spinbutton"}
LISTED = {"button", "link", "checkbox", "radio", "tab", "menuitem", "switch", "option", "slider", "treeitem"} | FIELDS
KINDS = {"textbox": "text field", "searchbox": "search field", "combobox": "combo box", "spinbutton": "number field",
         "menuitem": "menu item", "radio": "option", "treeitem": "tree item"}
# A FAILED CONNECTION IS NOT RETRIED FOR A MINUTE: EACH TRY CAN WAIT ON CHROME'S PERMISSION PROMPT.
RETRY_AFTER = 60
last_failure = 0.0
INSPECT = "chrome://inspect/#remote-debugging"
# WHERE EACH BROWSER KEEPS ITS PROFILES; DevToolsActivePort APPEARS THERE ONLY WHILE REMOTE DEBUGGING IS ON.
PROFILES = {
    "darwin": [Path.home() / "Library/Application Support" / d for d in
               ("Google/Chrome", "BraveSoftware/Brave-Browser", "Microsoft Edge", "Chromium", "Vivaldi", "Arc/User Data")],
    "win32": [Path(os.environ.get("LOCALAPPDATA", "")) / d / "User Data" for d in
              ("Google/Chrome", "BraveSoftware/Brave-Browser", "Microsoft/Edge", "Chromium", "Vivaldi")],
}
told = False


@dataclass
class Control:
    role: str
    label: str
    value: str
    enabled: bool
    frame: tuple | None
    element: str
    depth: int = 0

    @property
    def kind(self):
        return KINDS.get(self.role, self.role)

    @property
    def field(self):
        return self.role in FIELDS

    @property
    def listed(self):
        return self.role in LISTED


def run(*args, timeout=25):
    """One agent-browser command against the person's running Chrome; its data, or Failed with its own words."""
    try:
        done = subprocess.run([binary() or "agent-browser", "--cdp", port(), "--json", *args], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise Failed("Chrome did not answer in time. If it is asking to allow remote debugging, allow it.") from None
    try:
        reply = json.loads(done.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise Failed((done.stderr or done.stdout).strip()[:300] or "agent-browser gave no answer.") from None
    if not reply.get("success"):
        raise Failed(str(reply.get("error") or "agent-browser could not do that.")[:300])
    return reply.get("data") or {}


def binary():
    """agent-browser on the PATH, or where setup put it, which an app started from the Dock has no PATH to."""
    found = shutil.which("agent-browser")
    placed = Path.home() / ".local/bin" / ("agent-browser.exe" if sys.platform == "win32" else "agent-browser")
    return found or (str(placed) if placed.exists() else None)


def is_browser(name):
    return any(b in (name or "").lower() for b in BROWSERS)


def port():
    """Chrome's debugging port from its profile; macOS can refuse that read even when the file is there, and 9222 is Chrome's own."""
    for place in PROFILES.get(sys.platform, []):
        try:
            first = (place / "DevToolsActivePort").read_text().split()[0]
            if first.isdigit():
                return first
        except (OSError, IndexError):
            continue
    return "9222"


def allowed():
    """True when a browser has remote debugging on; read from its profile, so Chrome's prompt is never set off."""
    return any((place / "DevToolsActivePort").exists() for place in PROFILES.get(sys.platform, []))


def not_let_in(app):
    """One line, once a run, when a page in Chrome went through accessibility only because Chrome has not let Happy in."""
    global told
    if told or not binary() or not is_browser(app) or allowed():
        return ""
    told = True
    where = "Allow Chrome pages under Permissions in Happy's settings" if sys.platform == "darwin" else \
        f"Switch on remote debugging at {INSPECT} in Chrome"
    return f" Chrome has not let Happy into its pages, so this went through accessibility, which sees less. {where} to let it in."


def open_inspect():
    """Opens Chrome's remote debugging switch in a new tab."""
    if sys.platform == "darwin":
        from happy.system import native

        native.osascript('tell application "Google Chrome"\n if (count of windows) = 0 then make new window\n'
                         f' tell front window to make new tab with properties {{URL:"{INSPECT}"}}\n activate\nend tell')
    else:
        subprocess.Popen(["cmd", "/c", "start", "chrome", INSPECT])


def usable(app):
    """True when the page in this app can be worked through agent-browser right now."""
    global last_failure
    if not binary() or not is_browser(app) or not allowed() or time.monotonic() - last_failure < RETRY_AFTER:
        return False
    try:
        run("get", "url", timeout=25)
        return True
    except Failed as error:
        last_failure = time.monotonic()
        log.info("agent-browser is not connected to Chrome, so the page goes through accessibility: %s", error)
        return False


class Window:
    """The page in the front tab, with the browser's own window kept for bringing it forward."""

    def __init__(self, outer):
        self.outer, self.app, self.pid, self.front = outer, outer.app, outer.pid, outer.front
        self.title = title(self)


def window(app=""):
    from happy.system import controls

    return Window(controls.window(app))


# ONE LINE OF THE SNAPSHOT: - checkbox "Remember me" [checked=true, ref=e2]: what a field holds
LINE = re.compile(r'^\s*-\s*(\w+)(?:\s+"((?:[^"\\]|\\.)*)")?\s*\[([^\]]*)\](?::\s*(.*))?$')


def controls(win, roles=None, budget=None):
    """The page's controls in the order the page shows them, each with its state, so a click can be seen to change it."""
    data = run("snapshot", "-i")
    win.url = data.get("origin", "")
    refs, seen, found = data.get("refs", {}), set(), []
    for line in str(data.get("snapshot", "")).splitlines():
        hit = LINE.match(line)
        attrs = dict(a.strip().partition("=")[::2] for a in hit.group(3).split(",")) if hit else {}
        ref = attrs.pop("ref", "")
        if ref in refs and ref not in seen:
            seen.add(ref)
            found.append(made(ref, refs[ref], attrs, hit.group(4) or ""))
    # A REF THE TEXT DID NOT SHOW STILL COUNTS, AFTER THE ONES IT DID.
    for ref, entry in sorted(refs.items(), key=lambda kv: int(kv[0].lstrip("e") or 0)):
        if ref not in seen:
            found.append(made(ref, entry, {}, ""))
    return [c for c in found if c is not None]


def made(ref, entry, attrs, held):
    role, name = entry.get("role", ""), (entry.get("name") or "").strip()
    if role in FIELDS and not name:
        name = KINDS.get(role, role)
    if role not in LISTED or not name:
        return None
    state = ", ".join(f"{k}={v}" for k, v in attrs.items() if k not in ("level",))
    value = held.strip() if role in FIELDS else state
    return Control(role, name, value, attrs.get("disabled") != "true", None, f"@{ref}")


def press(control, win):
    run("click", control.element)
    return "clicked"


def set_text(control, text, win, add=False):
    wanted = (control.value + text) if add else text
    run("fill", control.element, "--", wanted)
    return value(control) == wanted


def value(control):
    try:
        return str(run("get", "value", control.element).get("value", ""))
    except Failed:
        return ""


def enter(win):
    run("press", "Enter")


def bring_forward(win):
    from happy.system import controls

    controls.bring_forward(win.outer)
    win.front = True


def menu(win, path):
    from happy.system import controls

    return controls.menu(win.outer, path)


def scroll(win, where, inside=None):
    if where in ("top", "bottom"):
        run("press", "Home" if where == "top" else "End")
    else:
        run("scroll", where, "800")
    return {"top": 0.0, "bottom": 1.0}.get(where)


def title(win):
    try:
        return str(run("get", "title").get("title", ""))
    except Failed:
        return ""


def alive(thing):
    if isinstance(thing, Window):
        return True
    try:
        return bool(run("is", "visible", thing.element).get("visible"))
    except Failed:
        return False


def focused_field(win):
    return None
