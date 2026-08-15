"""THE CONNECTIONS FROM A TERMINAL: python -m mcps

    python -m mcps                     what is connected, and what it can do
    python -m mcps connect google      sign in, in a real browser
    python -m mcps disconnect google
    python -m mcps probe notion        what one of the servers offers, right now
    python -m mcps call notion search '{"query": "dentist"}'

probe STARTS A SERVER AND SAYS WHAT IT OFFERS. call PRINTS WHAT THE MODEL WOULD
ACTUALLY SEE, WHICH IS THE ONLY PLACE A SERVER THAT ANSWERS IN FIVE KILOBYTES OF
JSON SHOWS UP BEFORE IT IS BEING READ OUT LOUD TO SOMEBODY.
"""

import json
import sys

from mcps import binding, loop, registry, shortening
from mcps.session import Session, local

USAGE = __doc__


def opened(name):
    """ONE OF THE SERVERS HAPPY SHIPS, STARTED ON ITS OWN FOR A LOOK AT IT."""
    where = registry.server(name)

    if where is None:
        raise SystemExit(f"There is nothing called {name}.")

    return Session(registry.label(name), local(sys.executable, [str(where)]))


def probe(name):
    session = opened(name)

    try:
        offered = loop.run(session.listing(), session.timeout)
    finally:
        loop.run(session.close(), 5)

    print(f"{registry.label(name)} — {len(offered)} tools\n")

    for tool in offered:
        print(f"  {binding.named(name, tool.name)}")
        print(f"    {shortening.blurb(tool.description, registry.label(name))}\n")


def call(name, tool, arguments):
    session = opened(name)

    try:
        result = loop.run(session.call(tool, arguments), session.timeout)
    finally:
        loop.run(session.close(), 5)

    print("--- what the model sees ---")
    print(shortening.shortened(result))


def listing():
    """EVERY SERVICE, WHETHER IT IS ON, AND WHAT THE MODEL WOULD SEE OF IT."""
    import mcps
    from mcps import store, tokens

    rows = {row["name"]: row for row in store.every()}
    bound = {each.name for each in mcps.offering()}

    print(f"sign ins are kept in {tokens.sitting()}\n")

    for known in registry.known():
        row = rows.get(known["name"], {})
        state = "connected" if row.get("tools") else "not connected"
        mine = sorted(each for each in bound if each.startswith(binding.tidy(known["label"])))

        print(f"  {known['label']:<12} {state:<12} {known['kind']}")
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
