"""WHAT THE MODEL IS ACTUALLY HANDED: python -m hands

    python -m hands              every tool, in the order the model sees them
    python -m hands --full       the same, with the whole description of each
    python -m hands --prompt     the system prompt, word for word
    python -m hands mail         only the tools whose name or words match

THE ONLY HONEST ANSWER TO "WHY DID IT NOT USE THE GMAIL TOOL" IS THE LIST IT WAS
GIVEN AND THE WORDS THAT CAME WITH THEM, SO THIS PRINTS EXACTLY THAT AND NOTHING
IT COULD NOT HAVE SEEN. A TOOL MISSING HERE IS MISSING FROM THE MODEL TOO.
"""

import sys

import hands

WIDE = 34

MOST = 100


def owner():
    """WHICH MODULE EACH TOOL CAME FROM, WHICH THE FLAT LIST NO LONGER SAYS."""
    from mcps import registry

    found = {}

    for module in hands.MODULES:
        name = module.__name__.split(".")[-1]

        for each in getattr(module, "TOOLS", []):
            found[each.name] = name

        offering = getattr(module, "offering", None)

        if offering:
            for each in offering():
                found.setdefault(each.name, connected(each.name, registry) or name)

    return found


def connected(name, registry):
    """A REMOTE TOOL IS NAMED AFTER ITS SERVICE, SO THE SERVICE IS IN THE NAME."""
    for known in registry.known():
        if name.startswith(f"{known['name']}_"):
            return known["name"]

    return None


def listing(matching=None, full=False):
    tools = hands.tools()
    where = owner()
    shown = 0
    group = None

    for each in tools:
        if matching and matching not in f"{each.name} {each.description}".lower():
            continue

        here = where.get(each.name, "?")

        if here != group:
            group = here
            print(f"\n  {group}")

        shown += 1
        print(f"    {each.name:<{WIDE}} {said(each.description, full)}")

        if full:
            print(f"    {'':<{WIDE}} {shape(each)}")

    print(f"\n  {shown} of {len(tools)} tools" if matching else f"\n  {len(tools)} tools")


def said(description, full):
    words = " ".join(str(description or "").split())

    return words if full else clipped(words, MOST)


def shape(each):
    """THE ARGUMENTS, WHICH IS THE OTHER HALF OF WHAT THE MODEL IS DECIDING FROM."""
    try:
        held = each.args_schema

        if not isinstance(held, dict):
            held = held.model_json_schema()

        asked = list((held or {}).get("properties") or {})
    except Exception:
        return "(arguments unreadable)"

    return f"({', '.join(asked)})" if asked else "(no arguments)"


def clipped(words, most):
    return words if len(words) <= most else words[: most - 1].rstrip() + "…"


def prompt():
    from brain.prompt import system_prompt

    print(system_prompt())


def main(argv):
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)

        return 0

    if argv and argv[0] == "--prompt":
        prompt()

        return 0

    full = "--full" in argv
    rest = [each for each in argv if not each.startswith("-")]

    listing(rest[0].lower() if rest else None, full)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
