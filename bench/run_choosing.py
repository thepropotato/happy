"""RUN THE CHOOSING CASES AGAINST HAPPY WITH EVERY TOOL MOCKED, N TIMES, AND REPORT A SPREAD.

    python3 bench/run_choosing.py                 # every case, three times
    python3 bench/run_choosing.py --times 5       # five
    python3 bench/run_choosing.py B1 B2 R3        # only these, still three times
    python3 bench/run_choosing.py --effort medium # any brain knob

ONE RUN IS NOT A SCORE. THE SUITE SWINGS RUN TO RUN, SO A NUMBER WITHOUT A SPREAD BESIDE IT
CANNOT BE COMPARED TO YESTERDAY'S, AND THE TUNED AND HELD-OUT HALVES ARE REPORTED APART SO A
CHANGE FITTED TO THE TEST SHOWS UP AS THE TWO NUMBERS PARTING."""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bench import sandbox

# BEFORE ANY HAPPY IMPORT, SO THE REAL DATABASE IS NEVER THE ONE THAT OPENS.
DB = sandbox.throwaway("choosing.db")

from bench import choosing
from brain.thinking import Happy
from memory import settings

WORTH = {"pass": 1.0, "partial": 0.5, "fail": 0.0}

MARK = {"pass": "PASS", "partial": "PART", "fail": "FAIL"}


def knobs(args):
    """--effort medium BECOMES brain.effort, medium. THE SAME SHAPE replay.py TAKES."""
    skip = {"--times"}

    return [(f"brain.{each[2:]}", args[index + 1])
            for index, each in enumerate(args)
            if each.startswith("--") and each not in skip and index + 1 < len(args)]


def one(case, tools, calls):
    """ONE CASE ON A THREAD OF ITS OWN: NOTHING CARRIES IN, NOTHING CARRIES OUT."""
    calls.clear()
    happy = Happy(tools=tools)
    happy.thread = f"choosing-{case['id']}-{time.time()}"

    started = time.perf_counter()

    try:
        reply = happy.say(case["said"])
        broke = None
    except Exception as error:
        reply, broke = "", f"{type(error).__name__}: {error}"

    seconds = time.perf_counter() - started
    called = list(calls)
    verdict, why = ("fail", broke) if broke else choosing.score(case, called)

    return dict(id=case["id"], category=case["category"], said=case["said"], held=choosing.held(case),
                verdict=verdict, why=why, called=[each["name"] for each in called],
                reply=(reply or "")[:300], seconds=round(seconds, 1))


def share(results):
    """THE SCORE AS A FRACTION, PARTIALS COUNTING HALF."""
    if not results:
        return 0.0

    return sum(WORTH[each["verdict"]] for each in results) / len(results)


def main():
    args = sys.argv[1:]
    times = int(args[args.index("--times") + 1]) if "--times" in args else 3

    for key, value in knobs(args):
        settings.put(key, value)

    only = [each for each in args if not each.startswith("--")
            and not each.replace(".", "").isdigit()]
    # A KNOB'S VALUE IS NOT A CASE ID.
    values = {args[index + 1] for index, each in enumerate(args)
              if each.startswith("--") and index + 1 < len(args)}
    only = [each for each in only if each not in values]

    chosen = [each for each in choosing.CASES if not only or each["id"] in only]

    tools, calls = sandbox.harness()
    sandbox.assert_no_real_tools(tools)

    print(f"{len(tools)} tools mocked, {len(chosen)} cases, {times} runs each, db -> {DB}\n",
          flush=True)

    runs = []

    for attempt in range(times):
        print(f"--- run {attempt + 1} of {times} ---", flush=True)
        results = []

        for case in chosen:
            got = one(case, tools, calls)
            results.append(got)
            flag = " held" if got["held"] else ""
            print(f"  {MARK[got['verdict']]}  {got['id']:<4}{flag:<5} {got['why']}", flush=True)

        runs.append(results)
        print(f"  scored {share(results):.1%}\n", flush=True)

    report(runs, times)

    where = Path(__file__).resolve().parent / "runs" / f"choosing-{int(time.time())}.json"
    where.write_text(json.dumps(runs, indent=2), encoding="utf-8")
    print(f"\nwritten to {where}")

    return 0


def report(runs, times):
    """THE SCORE, ITS SPREAD, AND THE TUNED AND HELD-OUT HALVES SIDE BY SIDE."""
    scores = [share(each) for each in runs]
    low, high = min(scores), max(scores)

    print("=" * 60)
    print(f"overall   {sum(scores) / len(scores):.1%}   "
          f"low {low:.1%}  high {high:.1%}  spread {high - low:.1%}")

    tuned = [share([r for r in each if not r["held"]]) for each in runs]
    kept = [share([r for r in each if r["held"]]) for each in runs]

    print(f"tuned     {sum(tuned) / len(tuned):.1%}")
    print(f"held out  {sum(kept) / len(kept):.1%}")

    gap = sum(tuned) / len(tuned) - sum(kept) / len(kept)

    if gap > 0.15:
        print(f"\n  the tuned half leads the held-out half by {gap:.0%}. that is the shape of a\n"
              f"  prompt fitted to the cases it is scored on rather than to the job.")

    print()

    for name, _ in choosing.GROUPS:
        each = [share([r for r in run if r["category"] == name]) for run in runs]
        print(f"  {name:<12} {sum(each) / len(each):.1%}")

    # A CASE THAT FAILED EVERY TIME IS A REGRESSION. ONE THAT FAILED SOMETIMES IS THE SUITE
    # BEING NOISY, AND SAYING SO IS THE DIFFERENCE BETWEEN A BUG AND A COIN FLIP.
    print()
    counted = {}

    for run in runs:
        for got in run:
            counted.setdefault(got["id"], []).append(got["verdict"])

    always = [name for name, seen in counted.items() if all(each == "fail" for each in seen)]
    sometimes = [name for name, seen in counted.items()
                 if "fail" in seen and not all(each == "fail" for each in seen)]

    if always:
        print(f"  failed every run:  {', '.join(sorted(always))}")

    if sometimes:
        print(f"  failed some runs:  {', '.join(sorted(sometimes))}  (noise, not a regression)")

    if not always and not sometimes:
        print("  nothing failed in any run")


if __name__ == "__main__":
    sys.exit(main())
