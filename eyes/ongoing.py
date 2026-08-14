"""WHETHER THE THING SOMEBODY JUST ASKED FOR IS ALREADY GOING ON THIS COMPUTER."""

from eyes import tabs
from eyes.attention import windows

# TOO SMALL TO TELL TWO THINGS APART, AND PEOPLE DROP THEM ANYWAY.
FILLER = {"the", "a", "an", "of", "on", "in", "at", "to", "my", "and", "for", "is", "it"}

MOST = 12


def keywords(about):
    """WHAT ACTUALLY HAS TO APPEAR SOMEWHERE FOR THIS TO BE THE SAME THING."""
    return [word for word in "".join(
        letter if letter.isalnum() or letter.isspace() else " " for letter in about.lower()
    ).split() if word not in FILLER]


def hit(wanted, *fields):
    """TRUE WHEN EVERY WORD ASKED FOR TURNS UP IN ONE OF THESE."""
    haystack = " ".join(field.lower() for field in fields if field)

    return bool(wanted) and all(word in haystack for word in wanted)


def matches(about):
    """EVERY OPEN WINDOW AND TAB THAT IS PLAINLY THE THING ASKED ABOUT."""
    wanted = keywords(about)
    open_tabs = tabs.open_now()

    # A BROWSER NAMES ITS WINDOW AFTER ITS FRONT TAB, AND THE TAB CARRIES THE
    # ADDRESS, SO THE WINDOW ROW WOULD BE THE SAME THING SAID WORSE.
    fronting = {title for _, title, _ in open_tabs}
    found = []

    for name, title in windows():
        if title not in fronting and hit(wanted, name, title):
            found.append(f'{name} — "{title}"' if title else name)

    for browser, title, address in open_tabs:
        if hit(wanted, title, address):
            found.append(
                f'{browser} tab — "{title}" ({address})' if address
                else f'{browser} tab — "{title}"'
            )

    return found


def everything():
    """EVERY WINDOW AND TAB, FOR WHEN NOTHING MATCHED AND THE MODEL SHOULD JUDGE."""
    open_tabs = tabs.open_now()
    fronting = {title for _, title, _ in open_tabs}

    listed = [
        f'{name} — "{title}"' if title else name
        for name, title in windows()[:MOST]
        if title not in fronting
    ]

    return listed + [f'{browser} tab — "{title}"' for browser, title, _ in open_tabs[:MOST]]
