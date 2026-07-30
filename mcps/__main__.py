"""THE CONNECTIONS FROM A TERMINAL: python -m mcps

    python -m mcps                     what is connected, and what it can do
    python -m mcps connect notion      sign in, in a real browser
    python -m mcps disconnect notion
    python -m mcps probe https://mcp.notion.com/mcp
    python -m mcps probe "npx -y @modelcontextprotocol/server-everything"
    python -m mcps call <where> <tool> '{"query": "dentist"}'

WHERE IS A URL, OR A WHOLE COMMAND IN ONE PAIR OF QUOTES.

probe SAYS WHAT A SERVER OFFERS. call PRINTS WHAT THE MODEL WOULD ACTUALLY SEE,
WHICH IS THE ONLY PLACE A SERVER THAT ANSWERS IN FIVE KILOBYTES OF JSON SHOWS UP
BEFORE IT IS BEING READ OUT LOUD TO SOMEBODY.
"""

import json
import shlex
import sys

from mcps import binding, loop, speaking
from mcps.session import Session, local, remote

USAGE = __doc__


def opening(where):
    """A URL IS SOMEWHERE ELSE. ANYTHING ELSE IS A PROGRAM ON THIS MACHINE."""
    if where.startswith(("http://", "https://")):
        return remote(where)

    words = shlex.split(where)

    return local(words[0], words[1:])


def probe(where):
    name, opener = where, opening(where)
    session = Session(name, opener)

    try:
        offered = loop.run(session.listing(), session.timeout)
    finally:
        loop.run(session.close(), 5)

    print(f"{name} — {len(offered)} tools\n")

    for tool in offered:
        print(f"  {binding.named('service', tool.name)}")
        print(f"    {speaking.blurb(tool.description, 'Service')}\n")


def call(where, tool, arguments):
    name, opener = where, opening(where)
    session = Session(name, opener)

    try:
        result = loop.run(session.call(tool, arguments), session.timeout)
    finally:
        loop.run(session.close(), 5)

    print("--- what the model sees ---")
    print(speaking.said(result))


def listing():
    """EVERY CONNECTION, WHETHER IT IS ON, AND WHAT THE MODEL WOULD SEE OF IT."""
    import mcps
    from mcps import directory, store, tokens

    rows = {row["name"]: row for row in store.every()}
    bound = {each.name for each in mcps.offering()}

    print(f"sign ins are kept in {tokens.where()}\n")

    for known in directory.known():
        row = rows.get(known["name"], {})
        state = "on" if row.get("enabled") else ("known" if row else "not set up")
        mine = sorted(each for each in bound if each.startswith(binding.tidy(known["label"])))

        print(f"  {known['label']:<18} {state:<10} {known['kind']}")
        print(f"    {row.get('state') or known['hint']}")

        if mine:
            print(f"    {', '.join(mine)}")

        print()


def main(argv):
    if argv and argv[0] in ("-h", "--help"):
        print(USAGE)

        return 0

    what, rest = (argv[0] if argv else "list"), argv[1:]

    import mcps

    if what == "list":
        listing()
    elif what == "connect" and rest:
        print(mcps.connect(rest[0]))
    elif what == "disconnect" and rest:
        mcps.disconnect(rest[0])
        print(f"{rest[0]} is signed out.")
    elif what == "probe" and rest:
        probe(rest[0])
    elif what == "call" and len(rest) >= 2:
        call(rest[0], rest[1], json.loads(rest[2]) if len(rest) > 2 else {})
    else:
        print(USAGE)

        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
