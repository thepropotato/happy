"""The page inside the person's own Chrome, worked through agent-browser over the DevTools protocol; the browser's own bar and menus stay with the OS controls."""

import json
import logging
import shutil
import subprocess
import time
from dataclasses import dataclass

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
        done = subprocess.run(["agent-browser", "--auto-connect", "--json", *args], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise Failed("Chrome did not answer in time. If it is asking to allow remote debugging, allow it.") from None
    try:
        reply = json.loads(done.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise Failed((done.stderr or done.stdout).strip()[:300] or "agent-browser gave no answer.") from None
    if not reply.get("success"):
        raise Failed(str(reply.get("error") or "agent-browser could not do that.")[:300])
    return reply.get("data") or {}


def is_browser(name):
    return any(b in (name or "").lower() for b in BROWSERS)


def usable(app):
    """True when the page in this app can be worked through agent-browser right now."""
    global last_failure
    if not shutil.which("agent-browser") or not is_browser(app) or time.monotonic() - last_failure < RETRY_AFTER:
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


def controls(win, roles=None, budget=None):
    data = run("snapshot", "-i")
    win.url = data.get("origin", "")
    found = []
    for ref, entry in sorted(data.get("refs", {}).items(), key=lambda kv: int(kv[0].lstrip("e") or 0)):
        role, name = entry.get("role", ""), (entry.get("name") or "").strip()
        if role in FIELDS and not name:
            name = KINDS.get(role, role)
        if role in LISTED and name:
            found.append(Control(role, name, "", True, None, f"@{ref}"))
    return found


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
