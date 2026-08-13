"""THE SAME BRAIN, TYPED AT INSTEAD OF SPOKEN TO: python -m brain

WITH --trials IT TALKS TO ITSELF INSTEAD: THE SAME SENTENCES SAID FIVE TIMES
EACH, TO SEE WHETHER THE SAME QUESTION GETS THE SAME ANSWER. FOUR REPEATS BY
HAND IS HOW A FIX GETS CALLED DONE AND THEN FALLS OVER ON THE NEXT SENTENCE
SOMEBODY SAYS. WHAT IS WANTED IS A NUMBER PER SENTENCE: HOW OFTEN IT LOOKED
BEFORE ANSWERING, AND HOW MANY DIFFERENT ANSWERS CAME BACK FROM THE ONE ASKING.
"""

import json
import statistics
import sys
import time

import hands
from brain import model
from brain.model import LLMError
from brain.thinking import Happy
from memory import storage

TRIALS = "--trials"

TIMES = 5

# WHAT THIS PERSON ACTUALLY SAID, LIFTED OUT OF THE LOG. THE DULL ONES BELONG
# HERE TOO: MAKING "HI" CALL SOMETHING IS THE COST OF MAKING ANYTHING CALL.
SAYINGS = (
    "what am i doing ?",
    "do you know what episode im on ?",
    "how many episodes are left till the battle of the bastards episode ?",
    "Tell me how many episodes I still have left in this series ?",
    "how many total episodes does game of thrones have ? and i how many do I still have left ?",
    "How tall is the Eiffel Tower ?",
    "are there any unread messages on whatsapp ?",
    "hi",
    "thanks",
)


def main():
    happy = Happy()

    print(f"{model.name()} AT {model.url()}, TOOLS: {', '.join(hands.names())}. CTRL+C TO QUIT.\n")

    while True:
        said = input("you: ").strip()

        if not said:
            continue

        print("happy: ", end="", flush=True)

        try:
            for part in happy.say_streaming(said):
                print(part, end="", flush=True)
        except LLMError as problem:
            print(problem)

        print("\n")


def trials(times=TIMES, sayings=SAYINGS):
    """EVERY SENTENCE times TIMES, EACH ON A CLEAN THREAD.

    THE CLEAN THREAD IS THE WHOLE MEASUREMENT. WITHOUT IT THE SECOND ASKING
    READS THE FIRST ONE'S ANSWER OUT OF THE HISTORY AND SCORES A LOOK THAT
    NEVER HAPPENED, WHICH IS HOW A BROKEN THING LOOKS PERFECT FIVE TIMES.
    """
    happy = Happy()
    happy.say("hi")  # WARM, SO THE FIRST ROW IS NOT THE ONE PAYING FOR THE WEIGHTS.

    print(f"{times} repeats each, a clean thread every time\n")
    print(f"{'looked':>6} {'answers':>8} {'seconds':>8}  what was said")

    for saying in sayings:
        print(f"{'':>6} {'':>8} {'':>8}  {saying}")
        report(*trial(happy, saying, times))


def trial(happy, saying, times):
    """ONE SENTENCE, SAID times TIMES. GIVES BACK LOOKS, ANSWERS AND SECONDS."""
    looks, answers, taken = [], [], []

    for _ in range(times):
        happy.forget()
        mark = last()
        started = time.perf_counter()

        try:
            answers.append(happy.say(saying))
        except Exception as error:
            answers.append(f"BROKE: {type(error).__name__}")

        taken.append(time.perf_counter() - started)
        looks.append(called(mark))

    return looks, answers, taken


def report(looks, answers, taken):
    """ONE ROW. THE TOOLS ARE NAMED ONLY WHERE THEY WERE NOT ALWAYS THE SAME."""
    rate = f"{sum(1 for each in looks if each)}/{len(looks)}"
    kinds = {", ".join(each) or "nothing" for each in looks}

    print(
        f"{rate:>6} {len(set(answers)):>8} {statistics.mean(taken):>7.1f}s"
        f"  ↳ {' | '.join(sorted(kinds))}"
    )


def called(mark):
    """WHICH TOOLS THE TURNS AFTER mark CALLED, STRAIGHT OUT OF THE RECORD."""
    rows = storage.read("select tools from messages where id > ?", (mark,))

    return [each["name"] for row in rows for each in json.loads(row["tools"])]


def last():
    return storage.read("select coalesce(max(id), 0) as top from messages")[0]["top"]


if __name__ == "__main__":
    try:
        trials() if TRIALS in sys.argv else main()
    except (KeyboardInterrupt, EOFError):
        print("\nBye")
