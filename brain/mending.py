"""A TOOL CALL THE MODEL PUNCTUATED WRONGLY, PUT RIGHT WITHOUT ASKING IT AGAIN.

THE MODEL WILL NEVER ALWAYS WRITE VALID JSON: TEMPERATURE IS 0, THE PROMPT IS BIG, AND THE
MODEL IS SMALL. SO A MALFORMED CALL IS NOT TREATED AS A FAILURE TO REPORT BUT AS A SHAPE TO
MEND, AND ONLY WHERE THERE IS EXACTLY ONE WAY TO READ IT. ANYTHING THAT COULD BE READ TWO
WAYS IS LEFT ALONE FOR THE ROUND TO ASK ABOUT, BECAUSE A GUESSED ARGUMENT IS WORSE THAN A
RETRY."""

import json
import re

# HOW THE BACKEND QUOTES WHAT THE MODEL ACTUALLY WROTE: raw='{"contact":["Swish"],{...}'.
WROTE = re.compile(r"raw='(.*?)',\s*err=", re.DOTALL)

# THE MISTAKE gpt-oss MAKES UNDER THE BIG PROMPT: A BRACE OPENED WHERE A KEY WAS DUE, AS IN
# {"contact":["Swish"],{"limit":3}. THE KEYS AFTER IT BELONG TO THE OBJECT ALREADY OPEN, SO
# THE BRACE IS SURPLUS. THE CLOSING FORM }, { IS THE SAME MISTAKE WITH THE OBJECT SHUT FIRST.
SPLICED = re.compile(r"(\}\s*)?,\s*\{")


def wrote(said):
    """WHAT THE MODEL ACTUALLY WROTE, LIFTED OUT OF THE BACKEND'S COMPLAINT, OR None."""
    found = WROTE.search(said)

    return found.group(1) if found else None


def mended(raw):
    """THE ARGUMENTS THE MODEL MEANT, OR None IF THERE IS MORE THAN ONE WAY TO READ THEM."""
    if not raw or not raw.strip():
        return None

    for attempt in (raw, unspliced(raw), closed(raw), closed(unspliced(raw))):
        args = loaded(attempt)

        if args is not None:
            return args

    return None


def loaded(text):
    """text AS A JSON OBJECT, OR None. ONLY AN OBJECT WILL DO: TOOL ARGUMENTS ARE NAMED."""
    if text is None:
        return None

    try:
        args = json.loads(text)
    except ValueError:
        return None

    return args if isinstance(args, dict) else None


def unspliced(raw):
    """THE SURPLUS BRACE DROPPED, SO EVERY KEY SITS IN THE ONE OBJECT THE CALL MEANT.

    ONLY WHERE THE OBJECT IT OPENS WOULD BE A KEY: INSIDE A LIST, , { STARTS A REAL OBJECT
    AND DROPPING THE BRACE WOULD THROW IT AWAY."""
    out = []
    open_now = []
    inside = False
    escaped = False
    at = 0

    while at < len(raw):
        letter = raw[at]

        if inside:
            inside = not (letter == '"' and not escaped)
            escaped = letter == "\\" and not escaped
            out.append(letter)
            at += 1
            continue

        if letter == '"':
            inside = True
            out.append(letter)
            at += 1
            continue

        # A SPLICE ONLY COUNTS DIRECTLY INSIDE THE OUTERMOST OBJECT, WHERE A KEY WAS DUE.
        found = SPLICED.match(raw, at)

        if found and open_now == ["{"] and out:
            out.append(",")
            at = found.end()
            continue

        if letter in "[{":
            open_now.append(letter)
        elif letter in "]}" and open_now:
            open_now.pop()

        out.append(letter)
        at += 1

    return "".join(out)


def closed(raw):
    """AN ANSWER THAT STOPPED MID-WAY FINISHED OFF, OR None IF IT STOPPED MID-KEY.

    A STRING LEFT OPEN IS SHUT, THEN EVERY BRACKET STILL OPEN. A TRAILING COMMA OR A KEY
    WITH NO VALUE IS DROPPED, BECAUSE THE VALUE IT WANTED IS NOT KNOWN AND MAKING ONE UP
    WOULD CALL THE TOOL ON SOMETHING THE MODEL NEVER SAID."""
    if raw is None:
        return None

    shut = []
    inside = False
    escaped = False

    for letter in raw:
        if inside:
            inside = not (letter == '"' and not escaped)
            escaped = letter == "\\" and not escaped
            continue

        if letter == '"':
            inside = True
        elif letter in "[{":
            shut.append("]" if letter == "[" else "}")
        elif letter in "]}" and shut:
            shut.pop()

    whole = raw + ('"' if inside else "")

    # THE LAST KEY IS ONLY HALF-WRITTEN IF NOTHING GAVE IT A VALUE; CUT BACK TO THE COMMA.
    whole = trimmed(whole)

    if whole is None:
        return None

    return whole + "".join(reversed(shut))


# A KEY NOTHING WAS EVER GIVEN TO, AT THE END OF WHAT WAS WRITTEN: THE "order_newout?" IN
# {"limit":3,"order_newout?"}. THE BRACES AFTER IT ARE ALLOWED, AND KEPT.
DANGLING = re.compile(r",\s*\"[^\"]*\"\s*:?\s*([\]\}]*)$")

# A COMMA NOTHING FOLLOWS BUT THE BRACES THAT SHUT THE CALL.
TRAILING = re.compile(r",\s*([\]\}]*)$")


def trimmed(whole):
    """THE HALF-WRITTEN LAST KEY CUT OFF, OR None IF CUTTING IT LEAVES NOTHING TO CALL."""
    whole = DANGLING.sub(r"\1", whole)
    whole = TRAILING.sub(r"\1", whole)

    # NOTHING BUT BRACES LEFT MEANS EVERY ARGUMENT WAS THE HALF-WRITTEN ONE.
    return None if whole.strip().strip("{}[]") == "" else whole


def fitting(args, wanted):
    """WHETHER MENDED ARGUMENTS FIT THE TOOL, SO A MEND IS NEVER CALLED ON A GUESS.

    wanted IS THE TOOL'S JSON SCHEMA. EVERY REQUIRED ARGUMENT MUST BE THERE AND NO NAME MAY
    BE ONE THE TOOL DOES NOT TAKE; A MEND THAT INVENTS EITHER IS NOT A MEND."""
    if args is None:
        return False

    if not wanted:
        return True

    known = wanted.get("properties") or {}
    needed = wanted.get("required") or []

    if known and any(name not in known for name in args):
        return False

    return all(name in args for name in needed)
