"""A TOOL ON ONE OF THE SERVERS, TURNED INTO ONE THE GRAPH CAN CALL LIKE ANY OTHER."""

import re

from langchain_core.tools import StructuredTool

from hands import reasons
from mcps import loop, shortening
from mcps.session import Unreachable

UNTIDY = re.compile(r"[^a-z0-9_]+")

LONGEST = 64

ANYTHING = {"type": "object", "properties": {}}

ASLEEP = "{service} is not connected right now."

BROKE = "{service} could not be reached. It may need connecting again in the panel."


def named(service, tool):
    """service_tool, IN THE ONLY SHAPE A MODEL IS ALLOWED TO SEE."""
    together = f"{tidy(service)}_{tidy(tool)}".strip("_")

    return together[:LONGEST]


def tidy(word):
    return UNTIDY.sub("_", str(word).lower()).strip("_")


def bind(service, session, offered, taken=None):
    """EVERY TOOL FROM ONE SERVER AS SOMETHING hands.tools() CAN HAND TO THE MODEL."""
    spoken = set(taken or [])
    built = []

    for tool in offered:
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
        description=shortening.blurb(tool.description, service),
        args_schema=tool.inputSchema or ANYTHING,
        func=calling(service, session, tool),
    )


def calling(service, session, tool):
    """THE ORDINARY FUNCTION THE GRAPH CALLS, AND EVERYTHING THAT CAN GO WRONG IN IT."""

    def call(**arguments):
        try:
            result = loop.run(session.call(tool.name, arguments), session.timeout)
        except Unreachable:
            return reasons.no(ASLEEP.format(service=service))
        except TimeoutError:
            return reasons.no(f"{service} took too long to answer.")
        except Exception:
            return reasons.no(BROKE.format(service=service))

        return reasons.no(shortening.said(result)) if result.isError else shortening.said(result)

    return call
