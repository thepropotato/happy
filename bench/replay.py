"""REPLAY A REAL EVENING FROM THE LOG WITH EVERY TOOL MOCKED, ON ONE CONTINUOUS THREAD.

    python3 bench/replay.py bench/suites/2026-09-04.json          # the whole evening
    python3 bench/replay.py bench/suites/2026-09-04.json 21 26    # only those rows

A SUITE IS THE LOG LIFTED INTO TURNS: WHAT WAS SAID, THE REAL TOOL RESULTS HANDED BACK AS
CANNED REPLIES, AND WHAT SHOULD HAVE HAPPENED. A TURN MARKED restart CLOSES AND REOPENS
HAPPY FIRST, SO THE NEXT ANSWER SHOWS WHETHER ANYTHING SURVIVED."""

import copy
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bench import sandbox

# BEFORE ANY HAPPY IMPORT, AND EMPTIED, SO A REPLAY STARTS FROM NOTHING EVERY TIME.
DB = sandbox.throwaway("replay.db")
DB.unlink(missing_ok=True)

from bench import scoring
from brain.thinking import Happy
from memory import settings

THREAD = "replay"

MARK = {"pass": "PASS", "partial": "PART", "fail": "FAIL"}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def knobs(args):
    """--effort medium BECOMES brain.effort, medium; ANY --name value PAIR IS A brain.name."""
    pairs = []

    for index, each in enumerate(args):
        if each.startswith("--") and index + 1 < len(args):
            pairs.append((f"brain.{each[2:]}", args[index + 1]))

    return pairs


def opened(tools):
    """A HAPPY ON THE ONE THREAD. A SECOND CALL IS A CLOSE AND A REOPEN."""
    happy = Happy(tools=tools)
    happy.thread = THREAD

    return happy


def one(happy, turn, replies, calls):
    """ONE TURN ON THE RUNNING THREAD, SCORED."""
    calls.clear()
    replies.clear()
    replies.update(copy.deepcopy(turn.get("replies", {})))

    started = time.perf_counter()

    try:
        reply = happy.say(turn["said"])
        broke = None
    except Exception as error:
        reply, broke = "", f"{type(error).__name__}: {error}"

    seconds = time.perf_counter() - started
    called = list(calls)
    verdict, why = ("fail", broke) if broke else scoring.score(turn, called, reply)

    return dict(
        row=turn["row"], said=turn["said"], verdict=verdict, why=why,
        called=[each["name"] for each in called], args=[each["args"] for each in called],
        reply=reply[:400], seconds=round(seconds, 1), restart=bool(turn.get("restart")),
    )


def main():
    suite = load(sys.argv[1])
    only = {int(each) for each in sys.argv[2:] if each.isdigit()}

    # --effort medium, OR ANY OTHER KNOB, SET ON THE THROWAWAY DATABASE BEFORE THE FIRST TURN.
    for name, value in knobs(sys.argv[2:]):
        settings.put(name, value)
        print(f"{name} = {value}")

    replies = {}
    tools, calls = sandbox.harness(replies)
    sandbox.assert_no_real_tools(tools)
    print(f"{suite['name']}: {len(tools)} tools mocked, db -> {DB}\n", flush=True)

    happy = opened(tools)
    results = []

    for turn in suite["turns"]:
        if only and turn["row"] not in only:
            continue

        if turn.get("restart"):
            happy = opened(tools)
            print("  -- closed and reopened --", flush=True)

        got = one(happy, turn, replies, calls)
        results.append(got)
        print(
            f"[{MARK[got['verdict']]}] {got['row']:>3} {got['seconds']:>5}s  "
            f"{got['said'][:48]:<48} {got['why'][:70]}",
            flush=True,
        )

    counts, scored = scoring.tally(results)
    print(
        f"\n{counts['pass']} pass, {counts['partial']} partial, {counts['fail']} fail "
        f"-> {scored}/{len(results)} ({100 * scored / max(len(results), 1):.0f}%)"
    )

    out = Path(__file__).resolve().parent / "runs" / f"replay-{Path(sys.argv[1]).stem}.json"
    out.write_text(json.dumps(dict(counts=counts, score=scored, results=results), indent=2))
    print(f"report -> {out}")


if __name__ == "__main__":
    main()
