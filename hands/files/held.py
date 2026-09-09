"""WHICH PATHS THE MODEL MAY ACT ON: THE ONES A TOOL HANDED IT, AND NOTHING IT WROTE ITSELF.

THE SAME SHAPE AS hands/web/handed.py, WHICH DOES THIS FOR ADDRESSES. A TOOL THAT FINDS
FILES CALLS offer(); A TOOL THAT ACTS ON ONE CALLS resolve(). A PATH THAT NO TOOL EVER
PRODUCED IS A GUESS, AND A GUESS THAT LOOKS LIKE A PATH IS THE ONE MISTAKE THAT LOOKS
EXACTLY LIKE SUCCESS UNTIL IT REACHES SOMEBODY ELSE'S PHONE."""

import threading
from pathlib import Path

from memory import conversation

# THIS NAMES THE NEXT STEP, SO IT CARRIES THE MARK THAT KEEPS A TURN ALIVE: WITHOUT IT THE
# REFUSAL COUNTS TOWARDS "ENOUGH SAID NO, STOP", AND A TURN BEING PUT RIGHT ON ITS WAY TO
# DOING THE JOB WOULD BE ENDED FOR BEING PUT RIGHT.
REFUSED = (
    "{said} is not a path any tool gave you, so nothing was done with it. Never write a "
    "path yourself: call find_files with the words they used for it, or list_folder on the "
    "folder they named, then use the exact path that comes back. This is a step of the job, "
    "not a refusal of it. Do not apologise and do not stop."
)

# THE SAME, WHEN SOMETHING WAS LISTED AND THE GUESS LOOKS LIKE ONE OF THEM. SHOWING THE REAL
# NAMES IS WORTH MORE THAN ANY RULE: THE MODEL INVENTED "offer_letter.pdf" WITH THE TRUE
# NAME SITTING IN ITS OWN CONTEXT FROM A LISTING TWO TURNS EARLIER.
NEARBY = (
    "{said} is not a path any tool gave you, so nothing was done with it. These were "
    "handed to you and are real:\n{names}\nUse one of those exactly as written, or look "
    "again with find_files. This is a step of the job, not a refusal of it. Do not "
    "apologise and do not stop."
)

# HOW MANY REAL PATHS TO PUT IN FRONT OF A GUESS.
MOST_SHOWN = 8

lock = threading.Lock()

# EVERY PATH ANY TOOL HAS HANDED OVER, AS TEXT, RESOLVED.
given = set()


def clean(said):
    """WHAT WAS WRITTEN, WITH THE DECORATION A MODEL PUTS ROUND A PATH TAKEN OFF."""
    said = str(said or "").strip().strip('"').strip("'")

    return said.removeprefix("file://")


def settled(said):
    """ONE PATH AS THE ONE STRING WE COMPARE BY, SO ~ AND A RELATIVE STEP CANNOT HIDE A MATCH."""
    try:
        return str(Path(clean(said)).expanduser().resolve())
    except (OSError, RuntimeError, ValueError):
        return clean(said)


def offer(path):
    """ONE PATH A TOOL FOUND, LISTED OR MADE, NOW ALLOWED TO BE ACTED ON."""
    said = clean(path)

    if not said:
        return

    with lock:
        given.add(settled(said))


def offered(paths):
    """EVERY PATH IN A LISTING AT ONCE."""
    for each in paths:
        offer(each)


def known(said):
    with lock:
        return settled(said) in given


def spoken(said):
    """WHETHER THE PERSON THEMSELVES SAID THIS PATH THIS TURN. THEIRS IS ALWAYS ALLOWED."""
    asked = (conversation.asking() or "").lower()
    bare = clean(said).lower()

    return bool(bare) and bare in asked


def named(said):
    """A BARE NAME OR A DESCRIPTION, NOT A PATH. locate() LOOKS THOSE UP, WHICH IS THE
    LOOKING WE WANT, SO THEY GO STRAIGHT THROUGH."""
    return "/" not in clean(said) and "\\" not in clean(said)


def elsewhere(said):
    """AN ADDRESS, NOT A PATH ON THIS MACHINE. WHETHER THE MODEL MAY OPEN ONE IS
    hands/web/handed.py's QUESTION AND IS ASKED WHERE ADDRESSES ARE USED."""
    return clean(said).lower().startswith(("http://", "https://", "data:"))


def resolve(said):
    """THE PATH BEHIND WHAT THE MODEL WROTE, OR None AND THE WORDS TO REFUSE IT WITH."""
    path = clean(said)

    if not path or elsewhere(path) or named(path) or known(path) or spoken(path):
        return path, None

    # A PATH THAT IS REALLY THERE AND WAS REALLY LISTED, UNDER A NAME WE NEVER SAW HANDED
    # OVER, IS STILL A GUESS — BUT ONE THAT EXISTS CANNOT SEND THE WRONG FILE, AND
    # REFUSING IT WOULD BREAK EVERY PATH THE PERSON TYPES INTO A ROUTINE.
    if Path(path).expanduser().exists():
        offer(path)

        return path, None

    return None, refusal(path)


def refusal(said):
    """THE WORDS TO TURN A GUESS BACK WITH, SHOWING THE REAL NAMES WHEN THERE ARE ANY."""
    near = alike(said)

    if near:
        return NEARBY.format(said=said, names="\n".join(f"- {each}" for each in near))

    return REFUSED.format(said=said)


def alike(said):
    """THE REAL PATHS WORTH PUTTING IN FRONT OF THIS GUESS: THE ONES FROM THE SAME FOLDER."""
    where = str(Path(clean(said)).expanduser().parent)

    with lock:
        same = sorted(each for each in given if str(Path(each).parent) == where)

    return same[:MOST_SHOWN] if same else sorted(given)[:MOST_SHOWN]
