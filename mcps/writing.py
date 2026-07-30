"""WHICH OF THESE TOOLS CHANGES SOMETHING OUT THERE, AND ASKING FIRST WHEN IT DOES.

THE RULE IS THE CAUTIOUS WAY ROUND: NOT "GATE THE ONES THAT WRITE" BUT "ANYTHING
NOT KNOWN TO ONLY LOOK, ASKS". A SERVER WE HAVE NEVER SEEN CAN NAME ITS TOOLS
ANYTHING, AND SENDING A MAIL OR EMPTYING A LIST IS NOT SOMETHING TO GET BACK FROM.
"""

import conscience
from memory import settings

# THE STARTS OF NAMES THAT ONLY EVER LOOK AT SOMETHING.
READING = (
    "search",
    "list",
    "get",
    "fetch",
    "read",
    "find",
    "describe",
    "view",
    "show",
    "query",
    "lookup",
    "count",
)

REASON = "reaches out to a service and may change something there"


def reads(name, annotations=None):
    """TRUE ONLY WHEN THIS IS KNOWN TO JUST LOOK.

    readOnlyHint CAN MAKE THIS STRICTER AND NEVER LOOSER. IT IS A CLAIM BY THE
    SERVER, SO IT IS TAKEN AS A WARNING AND NOT AS PERMISSION.
    """
    if getattr(annotations, "readOnlyHint", None) is False:
        return False

    plain = str(name).lower().lstrip("_")

    return plain.startswith(READING)


def permitted(service, name, arguments, annotations=None):
    """TRUE WHEN THIS CALL MAY GO AHEAD."""
    if reads(name, annotations):
        return True

    if not settings.get("mcps.confirm", True):
        return True

    return conscience.allowed(wording(service, name, arguments), REASON)


def wording(service, name, arguments):
    """WHAT THE PERSON IS BEING ASKED ABOUT, IN WORDS AND NOT IN JSON."""
    doing = str(name).replace("_", " ").replace("-", " ").strip()
    about = ", ".join(f"{key} {value}" for key, value in sorted((arguments or {}).items()))

    return f"{doing} on {service}" + (f" — {about}" if about else "")
