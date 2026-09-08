"""WHAT MUST BE TRUE OF THE PROMPT AND THE TOOLS BEFORE A MODEL IS EVER ASKED ANYTHING.

    python3 bench/shape.py            # every check
    python3 bench/shape.py --bless    # accept the prompt as it now stands

NO MODEL RUNS HERE, SO THE ANSWER IS THE SAME EVERY TIME AND ARRIVES IN A SECOND. A REPLAY
SWINGS A FULL POINT RUN TO RUN AND CANNOT TELL YOU A DOCSTRING WENT MISSING; THIS CAN, AND
IT IS THE ONLY SCORE IN bench/ THAT NEVER NEEDS RUNNING TWICE."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bench import sandbox

# BEFORE ANY HAPPY IMPORT, OR THE REAL HISTORY IS THE ONE THAT OPENS.
DB = sandbox.throwaway("shape.db")

from brain import prompt
from hands import reasons, tools as hands_tools

GOLDEN = Path(__file__).resolve().parent / "golden" / "prompt.md"

COUNTS = Path(__file__).resolve().parent / "golden" / "tools.json"

# A DOCSTRING SHORTER THAN THIS IS NOT A DESCRIPTION, IT IS A NAME SAID TWICE.
SHORTEST = 120

# TWO TOOLS WHOSE FIRST LINES SHARE THIS MUCH OF THEIR WORDS ARE TWO TOOLS THE MODEL WILL
# ONE DAY CONFUSE. MEASURED ON THE OPENING SENTENCE, WHICH IS WHAT DECIDES A CHOICE.
TOO_ALIKE = 0.75

# THE PROMPT TARGETS A LOCAL MODEL AND IS WRITTEN IN SHORT LITERAL DIRECTIVES. AN XML TAG
# IN IT IS SOMEBODY WRITING FOR A DIFFERENT MODEL BY HABIT.
TAGS = ("<system>", "<instructions>", "<example>", "<task>", "<context>", "<rules>")


def first(text):
    """THE OPENING SENTENCE OF A DOCSTRING, WHICH IS THE PART THAT DECIDES A CHOICE."""
    said = " ".join((text or "").split())

    return said.split(". ")[0].lower()


def alike(one, other):
    """HOW MUCH TWO SENTENCES SHARE, 0 TO 1, ON THE WORDS IN THEM."""
    left, right = set(one.split()), set(other.split())

    if not left or not right:
        return 0.0

    return len(left & right) / len(left | right)


def every_tool_describes_itself(found):
    """A TOOL THE MODEL CANNOT READ IS A TOOL THE MODEL CANNOT PICK."""
    troubles = []

    for each in found:
        said = (each.description or "").strip()

        if not said:
            troubles.append(f"{each.name} has no description at all")
        elif len(said) < SHORTEST:
            troubles.append(f"{each.name} is described in {len(said)} characters, under {SHORTEST}")

    return troubles


def no_two_tools_read_alike(found):
    """THE FAILURE THIS CATCHES IS A CHOICE BETWEEN TWO THINGS THAT SAY THE SAME THING."""
    troubles = []
    openings = [(each.name, first(each.description)) for each in found]

    for index, (name, said) in enumerate(openings):
        for other, theirs in openings[index + 1:]:
            shared = alike(said, theirs)

            if shared >= TOO_ALIKE:
                troubles.append(f"{name} and {other} open alike ({shared:.0%})")

    return troubles


def every_name_is_its_own(found):
    """TWO TOOLS OF ONE NAME MEANS ONE OF THEM IS NEVER CALLED AND NOBODY IS TOLD."""
    seen, troubles = {}, []

    for each in found:
        if each.name in seen:
            troubles.append(f"{each.name} is registered twice")

        seen[each.name] = True

    return troubles


def every_tool_asks_why(found):
    """reasons.widened GIVES EVERY TOOL A why. ONE WITHOUT IT SLIPPED PAST THE WIDENING,
    AND THE PANEL HAS NOTHING TO SHOW FOR THE CALL."""
    return [f"{each.name} never asks for {reasons.WHY}"
            for each in found if reasons.WHY not in (each.args or {})]


def the_prompt_is_plain(text):
    """NO XML, BECAUSE THE PROMPT TARGETS A LOCAL MODEL AND NOT A CLOUD ONE."""
    return [f"the prompt contains {tag}" for tag in TAGS if tag in text.lower()]


def the_prompt_has_not_moved(text):
    """THE ONE CHECK THAT GUARDS THE PREFIX CACHE: THE BYTES ARE THE BYTES, OR THEY ARE NOT.

    A PROMPT CHANGE IS OFTEN RIGHT. WHAT IS NEVER RIGHT IS NOT KNOWING ONE HAPPENED, WHICH IS
    HOW A DOCSTRING EDIT FLIPS A ROUTING NOBODY WAS LOOKING AT."""
    if not GOLDEN.exists():
        return [f"nothing to compare against yet — run --bless to write {GOLDEN.name}"]

    was = GOLDEN.read_text(encoding="utf-8")

    if was == text:
        return []

    return [f"the prompt moved: {len(was)} characters became {len(text)}. "
            f"diff it against {GOLDEN}, and --bless once it is the prompt you meant"]


def the_toolset_has_not_moved(found):
    """A TOOL GAINED OR LOST MOVES THE PREFIX AS SURELY AS A WORD OF THE PROMPT DOES."""
    now = sorted(each.name for each in found)

    if not COUNTS.exists():
        return [f"nothing to compare against yet — run --bless to write {COUNTS.name}"]

    was = json.loads(COUNTS.read_text(encoding="utf-8"))

    gone = [name for name in was if name not in now]
    new = [name for name in now if name not in was]

    troubles = []

    if gone:
        troubles.append(f"tools went missing: {', '.join(gone)}")

    if new:
        troubles.append(f"tools appeared: {', '.join(new)}")

    return troubles


CHECKS = [
    ("every tool describes itself", every_tool_describes_itself, "tools"),
    ("no two tools read alike", no_two_tools_read_alike, "tools"),
    ("every name is its own", every_name_is_its_own, "tools"),
    ("every tool asks why", every_tool_asks_why, "tools"),
    ("the toolset has not moved", the_toolset_has_not_moved, "tools"),
    ("the prompt is plain", the_prompt_is_plain, "prompt"),
    ("the prompt has not moved", the_prompt_has_not_moved, "prompt"),
]


def bless(text, found):
    """ACCEPT WHAT IS THERE NOW AS WHAT OUGHT TO BE THERE."""
    GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN.write_text(text, encoding="utf-8")
    COUNTS.write_text(json.dumps(sorted(each.name for each in found), indent=2), encoding="utf-8")

    print(f"blessed: {len(text)} characters of prompt, {len(found)} tools")


def main():
    found = hands_tools()
    text = prompt.system_prompt()

    if "--bless" in sys.argv:
        return bless(text, found)

    print(f"{len(found)} tools, {len(text)} characters of prompt\n")

    failed = 0

    for name, check, against in CHECKS:
        troubles = check(text if against == "prompt" else found)

        if troubles:
            failed += 1
            print(f"FAIL  {name}")

            for line in troubles:
                print(f"        {line}")
        else:
            print(f"pass  {name}")

    print()

    if failed:
        print(f"{failed} of {len(CHECKS)} checks failed")
    else:
        print(f"all {len(CHECKS)} checks passed")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
