"""THE TOOLS. EVERY DOCSTRING HERE IS READ BY THE MODEL, NOT BY US."""

from pathlib import Path
from typing import Literal

from langchain_core.tools import tool

from hands import reasons
from hands.apps import installed, machine, opening, whereabouts
from hands.apps.running import launch

# THE ONE THING THIS FIELD IS ALLOWED TO SAY, WHICH IS THE POINT OF IT.
SEEING = "show"

CHECKING = "read"


@tool
def list_installed_apps() -> str:
    """List every application installed on this computer, by the name a person
    would say out loud. Use this when you are unsure whether an app exists or
    what it is called. If an app is not in this list, it is not installed."""
    apps = installed.apps()

    return ", ".join(apps) if apps else reasons.no("No applications found.")


@tool
def system_info() -> str:
    """Report what this computer is: operating system and version, processor
    architecture, number of CPU cores, total memory, free disk space, hostname
    and the logged in user. Use this for questions about the machine itself."""
    return machine.facts()


@tool
def where_we_are() -> str:
    """Where in the world this computer is: its country, its time zone, the
    local date and time, and the language it is set to.

    Call this before you look for somewhere to watch, listen to, buy or book
    anything. What is available, what it costs and which service carries it all
    depend on the country, and a search made without it comes back answered for
    somewhere else. Put the country into the words you search with.

    Call it too for anything about the time or the date here — what time it is,
    what day it is, whether something has already started. You are not told the
    time, so this is the only way you know it."""
    return whereabouts.where()


@tool
def open_app(name: str) -> str:
    """Open an installed application by name, for example "Visual Studio Code"
    or "Calculator". A short name like "chrome" is enough. Prefer this over a
    shell command whenever the user asks to open or launch an app.

    Check already_open first. Starting an app to do something the person already
    has open — a show paused in a tab, a document in the editor — is the wrong
    answer, and opening an app so they can search it themselves is not doing it.

    This opens things. Never use it to find out whether an app is installed:
    that is list_installed_apps, and it changes nothing on screen.

    This is for opening an application itself. If the user wants a web page, a
    video, a search or anything else with an address, use open_url instead: it
    goes to the browser they already use, and never opens the wrong one."""
    match, sure = installed.resolve(name)

    if match is None:
        return reasons.no(f"There is no app called {name} on this computer.")

    if not sure:
        return (
            f"There is no app called {name} on this computer. The nearest one "
            f"installed is {match}, which is a different app. Nothing was opened. "
            f"Ask whether {match} is what was meant before opening it."
        )

    how = opening.app_opener()

    if how is None:
        return reasons.no("Opening apps is not supported on this platform.")

    complaint = launch(how + [match])

    if complaint:
        return reasons.no(complaint)

    # EVERY TOOL AFTER THIS ONE READS WHATEVER IS IN FRONT, SO IF IT IS NOT THIS
    # APP THE MODEL HAS TO BE TOLD RATHER THAN LEFT CLICKING IN SOMEBODY ELSE'S.
    if not opening.raised(match):
        return (
            f"I started {match} but it did not come to the front, so anything on "
            f"screen right now belongs to another app. Do not click yet."
        )

    return f"Opened {match}. It is now the window in front."


@tool
def open_path(path: str) -> str:
    """Open a file or folder in whatever application the system uses for it: a
    folder opens in the file browser, a document opens in its editor. Accepts
    paths like "~/Downloads" or "/Users/me/notes.txt". Use this when the user
    asks to open, show or bring up a folder or a file."""
    target = Path(path).expanduser()

    if not target.exists():
        return reasons.no(f"There is nothing at {target}.")

    how = opening.opener()

    if how is None:
        return reasons.no("Opening paths is not supported on this platform.")

    return launch(how + [str(target)]) or f"Opened {target}."


@tool
def open_url(url: str, because: Literal[SEEING, CHECKING]) -> str:
    """Open a web address in the browser the user already uses, exactly as if
    they had clicked the link themselves. Use this for anything on the web that
    an address alone will reach: a site, a video, a search, a web app. Accepts
    "youtube.com" or a full address.

    "because" takes one of two words and nothing else. Say "show" when they
    asked for the page itself, to watch or read or use, and it lands on their
    screen on top of what they were doing. Say "read" when you only want a fact
    off it and their screen should stay exactly where they left it. The sentence
    saying what you are doing goes in "why", the same as every tool.

    Their browser is already signed in to their accounts, so this is how you
    reach anything of theirs on the web. Prefer it over opening a browser
    application and typing, which is never right."""
    if because == CHECKING:
        from hands.web.pages import page  # LATE: apps IS IMPORTED BEFORE web.

        try:
            return f"Their screen did not move. The page says:\n\n{page(url, 0)}"
        except Exception as error:
            return reasons.no(f"{error}")

    address = opening.web_address(url)

    return opening.hand_over(address) or f"Opened {address}."


TOOLS = [list_installed_apps, system_info, where_we_are, open_app, open_path, open_url]
