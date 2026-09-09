"""WHAT MUST STILL BE TRUE OF A TURN NOW THE GUARDS HANG ON A DSPy MODEL.

    python3 bench/guarding.py

NO MODEL RUNS HERE. EACH GUARD IS HANDED THE WORDS THAT SHOULD TRIP IT AND THE WORDS THAT
SHOULD NOT, AND THE JUDGEMENT IT MAKES IS THE ONE IN brain/wrapping.py RATHER THAN A COPY OF
IT — A GUARD THAT RESTATES ITS OWN RULE HERE WOULD PASS WHILE THE REAL ONE ROTS."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bench import sandbox

DB = sandbox.throwaway("guarding.db")

from brain import guarding, wrapping
from memory import conversation


def clean():
    """NOTHING RAN, NOTHING REFUSED: THE STATE A TURN STARTS IN."""
    wrapping.ran = []
    wrapping.refused = {}


def main():
    wrong = 0

    # keep_able: THE MODEL DECLINING A JOB IT HAS A TOOL FOR.
    clean()
    for why, words, want in (
        ("a turn that disowns a tool it has is sent back",
         "i cannot create a powerpoint for you", True),
        ("saying it cannot do something it truly has no tool for is left alone",
         "i cannot create a nuclear reactor", False),
        ("a plain answer is left alone", "it is half past four", False),
    ):
        got = guarding.disowned(words) is not None
        wrong += report(why, got, want)

    # keep_honest: A CLAIM WITH NOTHING BEHIND IT.
    clean()
    wrong += report("a claim with no tool run at all is sent back",
                    guarding.dishonest("i have sent that message") is not None, True)

    clean()
    wrapping.ran = True
    wrong += report("a claim after a tool ran is left alone",
                    guarding.dishonest("i have sent that message") is not None, False)

    # keep_at_it: GIVING UP WITH A DOOR STILL OPEN.
    clean()
    wrapping.refused = {"open_app": f"nothing yet. {wrapping.CARRY_ON}"}
    wrong += report("an apology while a tool waits is sent back",
                    guarding.gave_up("sorry, i was not able to do that") is not None, True)

    clean()
    wrong += report("an apology with no tool waiting is left alone",
                    guarding.gave_up("sorry, i was not able to do that") is not None, False)

    # keep_fresh: A QUESTION ABOUT SOMETHING THAT MOVES, ANSWERED OUT OF THE BACKCHAT. THE
    # MORNING'S "no unread messages" WAS STILL SITTING THERE AT THREE IN THE SHAPE A FRESH
    # ANSWER HAS, AND IT WAS SAID AGAIN WITH NOTHING CALLED.
    for why, said, want in (
        ("unread messages asked cold is sent back",
         "are there any unread messages on whatsapp ?", True),
        ("the screen asked cold is sent back", "whats on my screen", True),
        ("the calendar asked cold is sent back", "what's on my calendar today", True),
        ("a question with no moving answer is left alone", "who made you", False),
        ("an errand is left alone", "send athul a message saying hello", False),
    ):
        clean()
        conversation.here.set(conversation.begin(said))
        wrong += report(why, guarding.unchecked("no unread messages") is not None, want)

    # AND THE SAME QUESTION ONCE SOMETHING HAS ACTUALLY BEEN CALLED.
    clean()
    conversation.here.set(conversation.begin("are there any unread messages on whatsapp ?"))
    wrapping.ran.append("whatsapp_get_unread_messages")
    wrong += report("unread messages after a tool ran is left alone",
                    guarding.unchecked("no unread messages") is not None, False)

    # THE SHAPES DSPy HANDS BACK, WHICH ARE NOT THE ONES LANGCHAIN DID.
    for why, answer, want in (
        ("a bare string is read as what was said", ["it is four o'clock"], "it is four o'clock"),
        ("a message dict is read as what was said",
         [{"role": "assistant", "content": "It Is Four"}], "it is four"),
        ("nothing said reads as nothing", [], ""),
    ):
        wrong += report(why, guarding.spoken(answer), want)

    wrong += report("a round that asked for a tool is never turned back",
                    guarding.reaching([{"role": "assistant", "tool_calls": [{"id": "1"}]}]), True)
    wrong += report("a round that only spoke is open to the guards",
                    guarding.reaching([{"role": "assistant", "content": "hello"}]), False)

    # THE GUARDS MUST CALL THE REAL RULE AND NEVER A COPY OF IT.
    for name in ("DISOWNED_TOLD", "CARRY_ON", "GIVES_UP", "CLAIMED", "CLAIMS", "NOTHING_RAN",
                 "ASKED_FRESH", "ASKED_TOLD"):
        wrong += report(f"{name} is read off brain.wrapping", hasattr(wrapping, name), True)

    # keep_recent: THE OLDEST HALF GOES AT ONCE, BECAUSE ONE AT A TIME MOVES THE PREFIX
    # EVERY ROUND AND COSTS THE WHOLE CONTEXT EACH TIME.
    import hands
    from brain import erranding

    loop = erranding.built(hands.tools()[:2])

    for why, calls, want in (
        ("six calls drop to three", 6, 3),
        ("five calls drop to three", 5, 3),
        ("two calls drop to one", 2, 1),
    ):
        trajectory = {
            f"{field}_{i}": i
            for i in range(calls)
            for field in ("thought", "tool_name", "tool_args", "observation")
        }
        loop.truncate_trajectory(trajectory)
        wrong += report(why, len(trajectory) // 4, want)

    print(f"\n{wrong} wrong" if wrong else "\nall good")

    return 1 if wrong else 0


def report(why, got, want):
    if got != want:
        print(f"WRONG  {why}\n       wanted {want!r}, got {got!r}")

        return 1

    print(f"ok     {why}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
