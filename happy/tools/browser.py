"""Browser tabs: listing, switching, closing, opening and reading them."""

import html
import io
import re
import sys
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import unquote, urlparse

import httpx

from happy.system import Failed, native
from happy.tools import tool

CHROMIUM = ["Google Chrome", "Brave Browser", "Microsoft Edge", "Arc", "Chromium", "Vivaldi", "Google Chrome Canary"]
BROWSERS = CHROMIUM + ["Safari"]

CHROME_LIST = """
tell application "{app}"
  set out to ""
  set wi to 0
  repeat with w in windows
    set wi to wi + 1
    set ti to 0
    set act to active tab index of w
    repeat with t in tabs of w
      set ti to ti + 1
      set out to out & wi & (character id 9) & ti & (character id 9) & (ti = act) & (character id 9) & (title of t) & (character id 9) & (URL of t) & linefeed
    end repeat
  end repeat
  return out
end tell"""

SAFARI_LIST = """
tell application "Safari"
  set out to ""
  set wi to 0
  repeat with w in windows
    set wi to wi + 1
    set ti to 0
    set cur to index of current tab of w
    repeat with t in tabs of w
      set ti to ti + 1
      set out to out & wi & (character id 9) & ti & (character id 9) & (ti = cur) & (character id 9) & (name of t) & (character id 9) & (URL of t) & linefeed
    end repeat
  end repeat
  return out
end tell"""


def front_browser():
    """The browser in front, or else the one that is open."""
    front = native.frontmost()
    if front in BROWSERS:
        return front
    running = native.running_apps()
    for name in BROWSERS:
        if name in running:
            return name
    return None


def quote(text):
    return text.replace("\\", "\\\\").replace('"', '\\"')


def list_tabs(app):
    out = native.osascript((SAFARI_LIST if app == "Safari" else CHROME_LIST).replace("{app}", app))
    tabs = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 5:
            tabs.append({"window": int(parts[0]), "tab": int(parts[1]), "active": parts[2] == "true",
                         "title": parts[3], "url": parts[4]})
    return tabs


def matching(tabs, words):
    words = words.lower().strip()
    if not words:
        return []
    return [t for t in tabs if words in t["title"].lower() or words in t["url"].lower()]


def current(tabs):
    actives = [t for t in tabs if t["active"]]
    return min(actives, key=lambda t: t["window"]) if actives else None


def close(app, tab):
    native.osascript(f'tell application "{app}" to close tab {tab["tab"]} of window {tab["window"]}')


def focus(app, tab):
    if app == "Safari":
        script = f'tell application "Safari" to set current tab of window {tab["window"]} to tab {tab["tab"]} of window {tab["window"]}'
    else:
        script = f'tell application "{app}" to set active tab index of window {tab["window"]} to {tab["tab"]}'
    native.osascript(script)
    native.osascript(f'tell application "{app}" to set index of window {tab["window"]} to 1')
    native.osascript(f'tell application "{app}" to activate')


def keys_only(action):
    combos = {"close": "ctrl+w", "new": "ctrl+t", "reopen": "ctrl+shift+t", "reload": "f5",
              "back": "alt+left", "forward": "alt+right"}
    if action not in combos:
        raise Failed(f"{action} needs a Mac for now")
    native.press(combos[action])
    return f"Pressed {combos[action]}."


@tool(label="Tabs: {action} {match}")
def browser_tabs(
    action: Literal["list", "close", "switch", "new", "reload", "back", "forward", "reopen"],
    match: Annotated[str, "words from the tab's title or address; empty means the tab in front"] = "",
    url: Annotated[str, "address for a new tab"] = "",
):
    """List, close, switch to, reload or open browser tabs. Close with an empty match closes the tab in front."""
    if sys.platform != "darwin":
        return keys_only(action)
    app = front_browser()
    if not app:
        return "No browser is open."
    if action == "reopen":
        native.osascript(f'tell application "{app}" to activate')
        native.press("cmd+shift+t")
        return "Reopened the last closed tab."
    tabs = list_tabs(app)
    if action == "list":
        if not tabs:
            return f"{app} has no tabs open."
        return f"{app} tabs:\n" + "\n".join(f"{'* ' if t['active'] else ''}{t['title']} — {t['url']}" for t in tabs)
    if action == "new":
        address = url or "about:blank"
        if app == "Safari":
            native.osascript(f'tell application "Safari" to tell front window to set current tab to (make new tab with properties {{URL:"{quote(address)}"}})')
        else:
            native.osascript(f'tell application "{app}" to tell front window to make new tab with properties {{URL:"{quote(address)}"}}')
        native.osascript(f'tell application "{app}" to activate')
        return f"Opened a new tab{' at ' + address if url else ''}."
    chosen = matching(tabs, match) if match else [t for t in [current(tabs)] if t]
    if not chosen:
        return f"No tab matches {match}." if match else "No tab is open."
    if action == "close":
        for tab in sorted(chosen, key=lambda t: (t["window"], -t["tab"])):
            close(app, tab)
        titles = ", ".join(t["title"] or t["url"] for t in chosen[:3])
        return f"Closed {len(chosen)} tab{'s' if len(chosen) > 1 else ''}: {titles}."
    tab = chosen[0]
    if action == "switch":
        focus(app, tab)
        return f"Switched to {tab['title']}."
    verbs = {"reload": "reload", "back": "go back", "forward": "go forward"}
    if app == "Safari":
        script = {"reload": 'tell application "Safari" to do JavaScript "location.reload()" in current tab of front window',
                  "back": 'tell application "Safari" to do JavaScript "history.back()" in current tab of front window',
                  "forward": 'tell application "Safari" to do JavaScript "history.forward()" in current tab of front window'}[action]
    else:
        script = f'tell application "{app}" to {verbs[action]} tab {tab["tab"]} of window {tab["window"]}'
    native.osascript(script)
    return f"Did {action} on {tab['title']}."


def text_of(page):
    page = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|header|form)[^>]*>.*?</\1>", " ", page)
    page = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h\d|tr)>", "\n", page)
    page = html.unescape(re.sub(r"<[^>]+>", " ", page))
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in page.splitlines()]
    return "\n".join(line for line in lines if len(line) > 1)


def page_text(app, tab):
    """The page's words, read through the browser if it allows, otherwise fetched."""
    script = (f'tell application "Safari" to do JavaScript "document.body.innerText" in tab {tab["tab"]} of window {tab["window"]}'
              if app == "Safari" else
              f'tell application "{app}" to execute tab {tab["tab"]} of window {tab["window"]} javascript "document.body.innerText"')
    try:
        text = native.osascript(script)
        if text and text != "missing value":
            return text
    except Failed:
        pass
    if tab["url"].startswith("file://"):
        body = Path(unquote(urlparse(tab["url"]).path)).read_bytes()
    else:
        body = httpx.get(tab["url"], follow_redirects=True, timeout=15,
                         headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 Safari/605.1.15"}).content
    if body.startswith(b"%PDF"):
        from happy.tools.files import pdf_text

        return pdf_text(io.BytesIO(body))
    return text_of(body.decode("utf-8", "replace"))


@tool(label="Reading {match}")
def read_tab(match: Annotated[str, "words from the tab's title or address; empty means the tab in front"] = ""):
    """Read the page or article open in the browser. Use it for 'this article', 'this page' and 'summarise this'."""
    if sys.platform != "darwin":
        return "Reading tabs needs a Mac for now."
    app = front_browser()
    if not app:
        return "No browser is open."
    tabs = list_tabs(app)
    tab = (matching(tabs, match) or [None])[0] if match else current(tabs)
    if not tab:
        return f"No tab matches {match}."
    text = page_text(app, tab)
    return f"{tab['title']} — {tab['url']}\n\n{text[:6000]}"
