"""WHAT CAME BACK, SQUEEZED DOWN TO SOMETHING THAT CAN BE SAID OUT LOUD."""

import json
import re

MOST = 600  # ROUGHLY WHAT A PERSON WILL SIT THROUGH BEFORE ASKING SOMETHING NARROWER.

# LONG ENOUGH FOR THE LONGEST DESCRIPTION WE ACTUALLY SHIP, AND THERE ONLY SO A
# RUNAWAY DOCSTRING CANNOT QUIETLY EAT THE WINDOW.
MOST_BLURB = 4000

MORE = "… and more."

NOTHING = "Nothing came back."

FAILED = "That did not work."

PICTURE = "(a picture)"

# NO UNDERSCORE: IT IS ITALICS, BUT IT IS ALSO EVERY TOOL NAME WE HAVE, AND
# search_emails STRIPPED TO searchemails IS WORSE THAN ITALICS.
MARKDOWN = re.compile(r"[*`#>]+")

LINKS = re.compile(r"\[([^\]]*)\]\([^)]*\)")

SPACE = re.compile(r"\s+")

# SPACES AND TABS, NOT NEWLINES. A DESCRIPTION IS READ AND ITS SHAPE IS PART OF IT.
BLANK = re.compile(r"[ \t]+")


def shortened(result):
    """A CallToolResult AS THE ONE SHORT LINE THE MODEL AND THE PERSON GET."""
    body = stripped(reading(result))

    if result.isError:
        return f"{FAILED} {body}".strip() if body else FAILED

    return body or NOTHING


def reading(result):
    """THE PART OF AN ANSWER WORTH KEEPING, STRUCTURED FIRST WHERE THERE IS ANY."""
    laid = laying(getattr(result, "structuredContent", None))

    if laid:
        return laid

    kept = [each.text for each in result.content if getattr(each, "type", None) == "text"]

    if kept:
        together = "\n".join(kept)

        # SERVERS PUT JSON IN THE TEXT AND NOWHERE ELSE, AND A WALL OF BRACES IS
        # THE WORST THING THAT CAN GO INTO SOMEBODY'S EARS.
        return laying(parsed(together)) or together

    # SAYING NOTHING CAME BACK WHEN SOMETHING DID WOULD HAVE THE MODEL RETRY.
    return PICTURE if result.content else ""


def parsed(text):
    try:
        return json.loads(text)
    except ValueError:
        return None


def laying(value):
    """AN ANSWER LAID OUT FLAT, ONCE THE WRAPPER AROUND IT IS OFF."""
    value = unwrapped(value)

    if isinstance(value, str):
        return value

    return flat(value)


def unwrapped(value):
    """A LONE result KEY IS HOW A PLAIN ANSWER IS CARRIED, NOT SOMETHING TO SAY."""
    if isinstance(value, dict) and list(value) == ["result"]:
        return unwrapped(value["result"])

    return value


def flat(structured):
    """A TOP LEVEL OBJECT AS key: value LINES. ANYTHING DEEPER STAYS AS JSON."""
    if not isinstance(structured, dict) or not structured:
        return ""

    lines = []

    for key, value in structured.items():
        if isinstance(value, (dict, list)):
            value = json.dumps(value, separators=(",", ":"))

        lines.append(f"{key}: {value}")

    return "\n".join(lines)


def stripped(text):
    """NO MARKDOWN, NO RUNS OF SPACE, AND NEVER LONGER THAN A PERSON WILL HEAR."""
    if not text:
        return ""

    text = LINKS.sub(r"\1", str(text))
    text = MARKDOWN.sub("", text)
    text = SPACE.sub(" ", text).strip()

    return clipped(text, MOST)


def blurb(description, service):
    """A TOOL'S DESCRIPTION, WHOLE, WITH THE SERVICE IT BELONGS TO ON THE FRONT."""
    return f"{service}. {clipped(squeezed(description or ''), MOST_BLURB)}".strip()


def squeezed(text):
    """RUNS OF SPACE OFF, AND EVERY LINE LEFT WHERE IT WAS."""
    return "\n".join(BLANK.sub(" ", line).strip() for line in str(text).splitlines()).strip()


def clipped(text, most):
    if len(text) <= most:
        return text

    return text[: most - len(MORE)].rstrip() + MORE
