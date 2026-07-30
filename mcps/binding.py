"""A TOOL ON A SERVER SOMEWHERE, TURNED INTO ONE THE GRAPH CAN CALL LIKE ANY OTHER.

THE GRAPH IS SYNCHRONOUS AND THE PROTOCOL IS NOT, SO WHAT IS HANDED OVER IS AN
ORDINARY FUNCTION THAT PUTS THE WORK ON mcps.loop AND WAITS. NAMES ARE ALWAYS
PREFIXED WITH THE SERVICE, NEVER ONLY WHEN TWO OF THEM CLASH: A TOOL WHOSE NAME
CHANGES THE DAY A SECOND SERVICE IS CONNECTED STRANDS EVERY CALL ALREADY MADE.
"""

import re

from langchain_core.tools import StructuredTool

from mcps import loop, speaking, writing
from mcps.session import Unreachable

UNTIDY = re.compile(r"[^a-z0-9_]+")

LONGEST = 64

ANYTHING = {"type": "object", "properties": {}}

REFUSED = "Cancelled, the user said no. Do not try to do it another way."

ASLEEP = "{service} is not connected right now."

BROKE = "{service} could not be reached. It may need connecting again in the panel."


def named(service, tool):
    """service_tool, IN THE ONLY SHAPE A MODEL IS ALLOWED TO SEE."""
    together = f"{tidy(service)}_{tidy(tool)}".strip("_")

    return together[:LONGEST]


def tidy(word):
    return UNTIDY.sub("_", str(word).lower()).strip("_")


def wanted(offered, allowed=None, cap=0):
    """THE TOOLS WORTH BINDING: THE CHOSEN ONES, OR THE FIRST FEW OF WHATEVER CAME.

    A CAP ON ITS OWN PICKS AT RANDOM, BECAUSE NOTHING PROMISES WHAT ORDER A
    SERVER LISTS ITS TOOLS IN. A HAND WRITTEN LIST IS WHAT MAKES A SERVICE USEFUL
    RATHER THAN MERELY CONNECTED, SO THE CAP IS ONLY THE BACKSTOP BEHIND IT.
    """
    if allowed:
        chosen = [each for each in offered if each.name in set(allowed)]

        if chosen:
            return chosen

    return offered[:cap] if cap else offered


def bind(service, session, offered, allowed=None, cap=0, taken=None):
    """EVERY TOOL FROM ONE SERVER AS SOMETHING hands.tools() CAN HAND TO THE MODEL."""
    spoken = set(taken or [])
    built = []

    for tool in wanted(offered, allowed, cap):
        name = named(service, tool.name)

        # A CLASH IS SKIPPED, NEVER SHADOWED: NOBODY ELSE'S read_file WINS.
        if name in spoken:
            continue

        spoken.add(name)
        built.append(one(service, session, tool, name))

    return built


def one(service, session, tool, name):
    return StructuredTool(
        name=name,
        description=speaking.blurb(tool.description, service),
        args_schema=tool.inputSchema or ANYTHING,
        func=calling(service, session, tool),
    )


def calling(service, session, tool):
    """THE ORDINARY FUNCTION THE GRAPH CALLS, AND EVERYTHING THAT CAN GO WRONG IN IT."""

    def call(**arguments):
        annotations = getattr(tool, "annotations", None)

        if not writing.permitted(service, tool.name, arguments, annotations):
            return REFUSED

        try:
            result = loop.run(session.call(tool.name, arguments), session.timeout)
        except Unreachable:
            return ASLEEP.format(service=service)
        except TimeoutError:
            return f"{service} took too long to answer."
        except Exception:
            return BROKE.format(service=service)

        return speaking.said(result)

    return call
