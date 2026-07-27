"""THE TOOLS. EVERY DOCSTRING HERE IS READ BY THE MODEL, NOT BY US."""

from pathlib import Path

from langchain_core.tools import tool

from hands.apps import installed, machine, opening
from hands.apps.running import launch


@tool
def list_installed_apps() -> str:
    """List every application installed on this computer, by the name a person
    would say out loud. Use this when you are unsure whether an app exists or
    what it is called. If an app is not in this list, it is not installed."""
    apps = installed.apps()

    return ", ".join(apps) if apps else "No applications found."


@tool
def system_info() -> str:
    """Report what this computer is: operating system and version, processor
    architecture, number of CPU cores, total memory, free disk space, hostname
    and the logged in user. Use this for questions about the machine itself."""
    return machine.facts()


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
    match, sure = installed.resolve(name)

    if match is None:
        return f"There is no app called {name} on this computer."

    if not sure:
        return (
            f"There is no app called {name} on this computer. The nearest one "
            f"installed is {match}, which is a different app. Nothing was opened. "
            f"Ask whether {match} is what was meant before opening it."
        )

    how = opening.app_opener()

    if how is None:
        return "Opening apps is not supported on this platform."

    return launch(how + [match]) or f"Opened {match}."


@tool
def open_path(path: str) -> str:
    """Open a file or folder in whatever application the system uses for it: a
    folder opens in the file browser, a document opens in its editor. Accepts
    paths like "~/Downloads" or "/Users/me/notes.txt". Use this when the user
    asks to open, show or bring up a folder or a file."""
    target = Path(path).expanduser()

    if not target.exists():
        return f"There is nothing at {target}."

    how = opening.opener()

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
    application and typing, which is never right."""
    address = opening.web_address(url)

    return opening.hand_over(address) or f"Opened {address}."


TOOLS = [list_installed_apps, system_info, open_app, open_path, open_url]
