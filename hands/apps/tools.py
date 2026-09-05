"""THE TOOLS. EVERY DOCSTRING HERE IS READ BY THE MODEL, NOT BY US."""

from pathlib import Path
from typing import Literal

from langchain_core.tools import tool

import memory
from hands import reasons
from hands.apps import installed, judging, machine, opening, whereabouts
from hands.apps.running import launch

# THE ONE THING THIS FIELD IS ALLOWED TO SAY, WHICH IS THE POINT OF IT.
SEEING = "show"

CHECKING = "read"

# WHAT A READ SAYS BEFORE THE PAGE, WHEN READING IS WHAT WAS ASKED FOR.
MOVED = "Their screen did not move. The page says:"

# AND WHEN IT WAS AN OPEN THAT WAS TURNED INTO ONE, SO THE NEXT PAGE IS NOT OPENED EITHER.
TURNED = (
    "That was a question rather than something to look at, so their screen was left alone and "
    "the page was read here instead. Answer out of it and use \"read\" for the rest of this. "
    "The page says:"
)


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
    return whereabouts.report()


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
    """Open a web page in the browser the user already uses, exactly as if they
    had clicked it themselves. Give it the number of a search result, "1" for the
    first, a site's own name like "youtube.com", or an address they read out to
    you. To show one particular video, product or page, search_web for it first
    and open the result by its number.

    "because" takes one of two words and nothing else. Say "show" when they
    asked for the page itself, to watch or read or use, and it lands on their
    screen on top of what they were doing. Say "read" when you only want a fact
    off it and their screen should stay exactly where they left it.

    Their browser is already signed in to their accounts, so this is how you
    reach anything of theirs on the web. Never open a browser application and
    type into it instead."""
    from hands.web import handed  # LATE: apps IS IMPORTED BEFORE web.

    url, refusal = handed.resolve(url)

    if url is None:
        return reasons.no(refusal)

    # A PAGE OPENED TO ANSWER A QUESTION COVERS THEIR WORK OVER FOR NOTHING, AND THE WORDING
    # ABOVE HAS NEVER BEEN ENOUGH TO STOP IT, SO A SECOND AND MUCH SMALLER QUESTION DECIDES.
    if because == SEEING and not judging.wanted(memory.asking()):
        because = CHECKING
        turned = True
    else:
        turned = False

    if because == CHECKING:
        from hands.web.pages import page  # LATE: apps IS IMPORTED BEFORE web.

        try:
            return f"{TURNED if turned else MOVED}\n\n{page(url, 0)}"
        except Exception as error:
            return reasons.no(f"{error}")

    address = opening.web_address(url)

    return opening.hand_over(address) or f"Opened {address}."


TOOLS = [list_installed_apps, system_info, where_we_are, open_app, open_path, open_url]
