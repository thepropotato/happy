"""RUN TOOLCALL-15 AGAINST HAPPY WITH EVERY TOOL MOCKED. WRITES A JSON REPORT."""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bench import sandbox

# BEFORE ANY HAPPY IMPORT, SO THE REAL DATABASE IS NEVER THE ONE THAT OPENS.
DB = sandbox.throwaway("toolcall15.db")

import toolcall15
from brain.thinking import Happy


def one(scenario, tools, calls):
    """ONE SCENARIO: A FRESH CALL LOG, ONE TURN, THEN SCORED."""
    calls.clear()
    happy = Happy(tools=tools)
    happy.thread = f"bench-{scenario['id']}-{time.time()}"

    started = time.perf_counter()
    try:
        reply = happy.say(scenario["said"])
        broke = None
    except Exception as error:
        reply, broke = "", f"{type(error).__name__}: {error}"
    seconds = time.perf_counter() - started

    called = list(calls)
    verdict, why = ("fail", broke) if broke else toolcall15.score(scenario, called)

    return dict(id=scenario["id"], category=scenario["category"], said=scenario["said"],
                verdict=verdict, why=why, called=[c["name"] for c in called],
                args=[c["args"] for c in called], reply=reply[:300], seconds=round(seconds, 1))


def main():
    tools, calls = sandbox.harness()
    sandbox.assert_no_real_tools(tools)
    print(f"{len(tools)} tools mocked, db -> {DB}\n", flush=True)

    only = sys.argv[1:]
    chosen = [s for s in toolcall15.SCENARIOS if not only or s["id"] in only]
    results = []

    for scenario in chosen:
        got = one(scenario, tools, calls)
        results.append(got)
        mark = {"pass": "PASS", "partial": "PART", "fail": "FAIL"}[got["verdict"]]
        print(f"[{mark}] {got['id']} {got['category']:<11} {got['seconds']:>5}s  "
              f"{got['said'][:44]:<44} {got['why'][:60]}", flush=True)

    tally = {v: sum(1 for r in results if r["verdict"] == v) for v in ("pass", "partial", "fail")}
    scored = tally["pass"] + 0.5 * tally["partial"]

    print(f"\n{tally['pass']} pass, {tally['partial']} partial, {tally['fail']} fail "
          f"-> {scored}/{len(results)} ({100 * scored / len(results):.0f}%)")

    out = Path(__file__).resolve().parent / "runs" / "toolcall15.json"
    out.write_text(json.dumps(dict(tally=tally, score=scored, results=results), indent=2))
    print(f"report -> {out}")


if __name__ == "__main__":
    main()
