"""PASS, PARTIAL OR FAIL FOR ONE REPLAYED TURN, FROM WHAT WAS CALLED AND WHAT WAS SAID."""

import re

# A TOOL THAT TAKES AN ADDRESS, WHICH MAY ONLY EVER BE A RESULT NUMBER OR ONE A TOOL GAVE.
ADDRESSED = {"open_url", "read_page", "download"}

MARKDOWN = re.compile(r"^\s*(#|\||[-*] |\d+\. |```)", re.M)


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

    return found


def invented(called):
    """THE FIRST ADDRESS THE MODEL WROTE OUT ITSELF, OR None."""
    for each in called:
        if each["name"] not in ADDRESSED:
            continue

        url = str(each["args"].get("url", ""))

        if url and not url.strip().isdigit():
            return url

    return None


def tally(results):
    """HOW MANY OF EACH VERDICT, AND THE SCORE OUT OF THE TOTAL."""
    counts = {each: sum(1 for r in results if r["verdict"] == each) for each in ("pass", "partial", "fail")}

    return counts, counts["pass"] + 0.5 * counts["partial"]
