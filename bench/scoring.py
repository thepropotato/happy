"""PASS, PARTIAL OR FAIL FOR ONE REPLAYED TURN, FROM WHAT WAS CALLED AND WHAT WAS SAID."""

import re

# A TOOL THAT TAKES AN ADDRESS, WHICH MAY ONLY EVER BE A RESULT NUMBER OR ONE A TOOL GAVE.
ADDRESSED = {"open_url", "read_page", "download"}

MARKDOWN = re.compile(r"^\s*(#|\||[-*] |\d+\. |```)", re.M)

# A ROW OF A SPREADSHEET WHOSE NUMBER CAME OUT OF NOWHERE: A NAME THAT IS ONLY A COUNTER,
# OR THE RUN OF DIGITS A MODEL REACHES FOR WHEN IT HAS NOT LOOKED ANYTHING UP.
PLACEHOLDER = re.compile(
    r"^(video|item|row|title|name)\s*\d+\s*,|,\s*(12345|67890|23456|34567|45678)\s*$",
    re.M | re.I,
)


def score(turn, called, reply):
    """THE VERDICT AND ONE LINE SAYING WHY."""
    names = [each["name"] for each in called]
    forbid = turn.get("forbid", [])
    expect = turn.get("expect", [])
    then = turn.get("then", [])

    if "*" in forbid and names:
        return "fail", f"called {names} when it should have just answered"

    for bad in forbid:
        if bad != "*" and bad in names:
            return "fail", f"called forbidden {bad}"

    if expect and not any(good in names for good in expect):
        return "fail", f"called {names or 'nothing'}, wanted one of {expect}"

    troubles = checks(turn.get("check", {}), called, reply)

    if then and not any(each in names for each in then):
        troubles.append(f"never followed with one of {then}")

    if troubles:
        return "partial", "; ".join(troubles)

    return "pass", f"called {names}" if names else "answered without calling anything"


def checks(wanted, called, reply):
    """EVERY CHECK THAT DID NOT HOLD, IN WORDS."""
    low = (reply or "").lower()
    found = []

    if wanted.get("numbers_only") and invented(called):
        found.append(f"wrote an address itself: {invented(called)}")

    if wanted.get("no_question") and "?" in reply:
        found.append("ended on a question")

    if wanted.get("no_markdown") and MARKDOWN.search(reply or ""):
        found.append("answered in markdown")

    words = wanted.get("contains_any")

    if words and not any(each.lower() in low for each in words):
        found.append(f"reply mentions none of {words}")

    for each in wanted.get("not_contains", []):
        if each.lower() in low:
            found.append(f"reply says {each!r}")

    names = [each["name"] for each in called]
    went = [each["name"] for each in called if not each.get("refused")]

    # A CALL A GUARD TURNED BACK NEVER HAPPENED, SO IT IS NOT COUNTED AGAINST A LIMIT. THE
    # TURN THAT TRIED TO WRITE A DECK SAYING "Directed by Simon Curtis", WAS STOPPED, WENT AND
    # READ, AND WROTE "Joe Wright" INSTEAD IS THE BEHAVIOUR WANTED — NOT TWO GOES AT ONE TOOL.
    for name, most in (wanted.get("at_most") or {}).items():
        if went.count(name) > most:
            found.append(f"called {name} {went.count(name)} times, more than {most}")

    # SAME REASONING AS at_most: A CALL THAT WAS TURNED BACK NEVER HAPPENED. THE GUARD EXISTS
    # PRECISELY TO CATCH A WRITE THAT CAME BEFORE THE LOOKING, AND THE TURN THAT TRIES, IS
    # STOPPED, LOOKS AND THEN WRITES PROPERLY HAS DONE THE RIGHT THING IN THE END.
    for name, first in (wanted.get("before") or {}).items():
        if name in went and (first not in went or went.index(first) > went.index(name)):
            found.append(f"called {name} before {first} had said anything")

    if wanted.get("no_invented_rows"):
        made_up = invented_rows(called)

        if made_up:
            found.append(f"wrote a row nothing looked up: {made_up}")

    return found


def invented_rows(called):
    """THE FIRST MADE-UP SPREADSHEET ROW WRITTEN TO DISK, OR None. A FILE IS WORSE THAN A
    SENTENCE: A WRONG NUMBER SPOKEN IS GONE, AND A WRONG NUMBER SAVED IS BELIEVED LATER."""
    for each in called:
        if each["name"] not in ("write_file", "edit_file"):
            continue

        text = str(each["args"].get("text") or each["args"].get("replace") or "")
        found = PLACEHOLDER.search(text)

        if found:
            return found.group(0).strip()

    return None


def invented(called):
    """THE FIRST ADDRESS THE MODEL WROTE OUT ITSELF, OR None.

    A CALL THE GUARD TURNED BACK IS THE ONLY KIND THAT COUNTS. open_url NAMES THE ADDRESS IT
    OPENED IN ITS OWN RESULT, AND READING THAT SAME LINE BACK IS USING WHAT A TOOL GAVE, NOT
    WRITING ONE — JUDGING IT ON THE SHAPE OF THE ARGUMENT ALONE MARKED THE RIGHT BEHAVIOUR
    AS THE WRONG ONE, WHICH IS WHAT THE GUARD IS FOR AND THIS IS NOT."""
    for each in called:
        if each["name"] not in ADDRESSED:
            continue

        url = str(each["args"].get("url", ""))

        if url and not url.strip().isdigit() and each.get("refused"):
            return url

    return None


def tally(results):
    """HOW MANY OF EACH VERDICT, AND THE SCORE OUT OF THE TOTAL."""
    counts = {each: sum(1 for r in results if r["verdict"] == each) for each in ("pass", "partial", "fail")}

    return counts, counts["pass"] + 0.5 * counts["partial"]
