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
    """NOTHING RAN, NOTHING REFUSED, NOTHING CORRECTED: THE STATE A TURN STARTS IN."""
    wrapping.ran = []
    wrapping.refused = {}
    wrapping.withdrawn = 0
    wrapping.corrected = False


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

    # AND THE SAME CLAIM WITHOUT THE "I". A TURN THAT CALLED NOTHING AT ALL SAID "GITHUB'S
    # OPEN, AND THE PROJECT PAGE IS UP AND READY TO GO" AND WENT STRAIGHT OUT: EVERY WORD OF
    # THE CLAIM LIST WAS FIRST PERSON OR POSSESSIVE, AND THIS NAMED THE THING INSTEAD.
    for why, said, want in (
        ("a claim about the thing rather than the doing is sent back",
         "Got it, the site is open, and the project page is up and ready to go.", True),
        ("a bare report of a page being up is sent back", "The page is up.", True),
        ("a plain fact is left alone", "It is half past four.", False),
        ("a count is left alone", "There are three unread messages.", False),
        ("owning it is left alone", "I could not find a project by that name.", False),
        ("a question is left alone", "Which one do you want?", False),
    ):
        clean()
        wrong += report(why, guarding.dishonest(said.lower()) is not None, want)

    # AND THE HALF-WAY CASE: A TOOL RAN, BUT NOT ONE THAT COULD HAVE DONE WHAT WAS CLAIMED.
    # A TURN CHECKED WHATSAPP AND THEN SAID THE PROJECT PAGE WAS UP AND READY TO VIEW. THE
    # HONESTY CHECK ASKED ONLY WHETHER *A* TOOL HAD RUN, AND ONE HAD.
    for why, said, already, want in (
        ("a page claimed up with only a chat checked is sent back",
         "Two chats have unread messages. And the project page is up and ready to view.",
         ["whatsapp_get_latest_received_message"], True),
        ("the same claim with an opening tool is left alone",
         "The project page is up.", ["open_url"], False),
        ("a send claimed with only a read is sent back",
         "I sent that to Jane.", ["whatsapp_get_unread_messages"], True),
        ("a send with a sending tool is left alone",
         "I sent that to Jane.", ["whatsapp_send_message"], False),
        ("a document claimed with only a search is sent back",
         "I saved the document.", ["search_web"], True),
        ("a count off a reading tool is left alone",
         "There are three unread messages.", ["whatsapp_get_unread_messages"], False),
        ("owning that it did not happen is left alone",
         "I could not open it.", ["open_url"], False),
    ):
        clean()
        wrapping.ran.extend(already)
        wrong += report(why, guarding.dishonest(said.lower()) is not None, want)

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

    # AND THE WORDINGS THE PHRASE LIST NEVER HELD. THE LIST WAS WRITTEN OFF THE SENTENCES THAT
    # HAPPENED TO GO WRONG, SO "did anyone message me" — WHICH THE PROMPT ITSELF NAMES AS A
    # THING TO GO AND CHECK — WALKED STRAIGHT PAST IT.
    for why, said in (
        ("did anyone message me is a question about something that moves", "did anyone message me"),
        ("what show is this is one too", "what show is this"),
        ("how far in am i is one too", "how far in am i"),
        ("any texts is one too", "any texts"),
        ("did i get any mail is one too", "did i get any mail"),
    ):
        wrong += report(why, wrapping.asked_fresh(said), True)

    # AND WHAT MUST NOT BE: AN ERRAND IS A JOB TO DO, NEVER A QUESTION TO GO AND CHECK.
    for why, said in (
        ("sending a message is an errand", "send athul a message saying hello"),
        ("placing a call is an errand", "call priya on whatsapp"),
        ("texting is an errand", "text dad i will be home by eight"),
    ):
        wrong += report(why, wrapping.instructing(said), True)

    # THE BACKSTOP UNDER THE LIST: A QUESTION ABOUT THE VERY THING A DEAD SITTING'S TOOL WENT
    # AND FOUND, WHATEVER WORDS IT IS ASKED IN. THIS IS WHAT SURVIVES REWORDING.
    stale = {"message", "unread", "screen", "activity", "mail"}

    def backstopped(said):
        return not wrapping.instructing(said) and bool(wrapping.about(said) & stale)

    for why, said, want in (
        ("a reworded question about the chats is caught", "gimme the rundown on my chats", True),
        ("a reworded question about the screen is caught", "whats the story with my screen", True),
        ("a reworded question about mail is caught", "so hows my inbox looking", True),
        ("a question needing no tool is left alone", "what is the capital of france", False),
        ("an errand about messages is left alone", "send athul a message saying hello", False),
        ("a plain fact is left alone", "who made you", False),
    ):
        wrong += report(why, backstopped(said), want)

    # AND THE SAME QUESTION ONCE SOMETHING HAS ACTUALLY BEEN CALLED.
    clean()
    conversation.here.set(conversation.begin("are there any unread messages on whatsapp ?"))
    wrapping.ran.append("whatsapp_get_unread_messages")
    wrong += report("unread messages after a tool ran is left alone",
                    guarding.unchecked("no unread messages") is not None, False)

    # AND THE SAME GUARD ON THE LANGCHAIN SIDE. THE TWO LOOPS ARE ONE SETTING APART AND THE
    # ONE HAPPY ACTUALLY RUNS IS brain.signatures FALSE, SO A GUARD ADDED ONLY TO THE DSPy
    # SIDE IS A GUARD THAT NEVER RUNS — WHICH IS EXACTLY WHAT HAPPENED: THE UNREAD QUESTION
    # WAS ANSWERED FROM THE MORNING'S BACKCHAT TWICE MORE WITH keep_fresh SITTING UNUSED.
    from langchain_core.messages import AIMessage, HumanMessage

    class Asked:
        def __init__(self, messages=None):
            self.messages = messages or [HumanMessage("q")]

        def override(self, messages=None):
            return Asked(messages)

    def rounds(said, reply, already, reaching=False):
        """HOW MANY TIMES THE MODEL WAS ASKED: TWO MEANS THE TURN WAS SENT BACK."""
        sent = []

        def handler(request):
            sent.append(request)

            if reaching and len(sent) == 1:
                asking = AIMessage("")
                asking.tool_calls = [{"name": "x", "args": {}, "id": "1", "type": "tool_call"}]

                return asking

            return AIMessage(reply)

        conversation.here.set(conversation.begin(said))
        clean()
        wrapping.ran.extend(already)
        wrapping.keep_fresh.wrap_model_call(Asked(), handler)

        return len(sent)

    for why, said, already, reaching, want in (
        ("unread asked with nothing run is sent back",
         "are there any unread messages on whatsapp ?", [], False, 2),
        ("a bare check is sent back", "check", [], False, 2),
        ("unread after a tool ran is left alone",
         "are there any unread messages on whatsapp ?", ["whatsapp_get_unread_messages"], False, 1),
        ("a round reaching for a tool is left alone",
         "are there any unread messages on whatsapp ?", [], True, 1),
        ("an errand is left alone", "send priya a message", [], False, 1),
    ):
        wrong += report(why, rounds(said, "no unread messages", already, reaching), want)

    # AND WHAT A TURNED-BACK ROUND LEAVES ON THE SCREEN. THE STREAM DRAWS EACH ROUND AS THE
    # MODEL TYPES IT, SO A GUARD ALWAYS ARRIVES AFTER THE WORDS ARE ALREADY SHOWN: WITHOUT
    # THE WITHDRAWAL THE PANEL READ "56 unread", THEN THE TOOL, THEN "56 unread" AGAIN, AND
    # THE FIRST ONE WAS THE GUESS THE GUARD EXISTS TO STOP.
    def withdrawn(reply, reaching=True):
        """HOW MANY CHARACTERS THE GUARD TAKES BACK AFTER TURNING A ROUND BACK."""
        sent = []

        def handler(request):
            sent.append(request)

            if len(sent) == 1:
                return AIMessage(reply)

            if reaching:
                asking = AIMessage("")
                asking.tool_calls = [{"name": "x", "args": {}, "id": "1", "type": "tool_call"}]

                return asking

            return AIMessage("")

        conversation.here.set(conversation.begin("are there any unread messages on whatsapp ?"))
        clean()
        wrapping.withdrawn = 0
        wrapping.keep_fresh.wrap_model_call(Asked(), handler)

        return wrapping.taken()

    guessed = "Yep—56 unread WhatsApp messages across five chats."

    wrong += report("a turned-back round is taken back off the screen",
                    withdrawn(guessed), len(guessed))

    # WHICH TURNS WAIT BEFORE THEY DRAW. UNDRAWING IS STILL A FLICKER — THE WORDS WERE ON
    # THE SCREEN AND THAT IS WHAT WAS SEEN — SO A QUESTION A GUARD MAY HOLD IS NOT DRAWN
    # UNTIL IT IS PAST THE GUARDS. EVERY OTHER TURN MUST STILL TYPE AS IT ALWAYS DID.
    clean()

    for why, said, want in (
        ("the unread question waits before it draws",
         "are there any unread messages on whatsapp ?", True),
        ("a bare check waits", "check", True),
        ("the screen question waits", "whats on my screen", True),
        ("an errand draws as it types", "send priya a message", False),
        ("playing something draws as it types", "play badass on youtube", False),
        ("an ordinary question draws as it types", "who made you", False),
    ):
        wrong += report(why, wrapping.held(said), want)

    # AND ONCE A TURN HAS BEEN CORRECTED, EVERY LATER ROUND OF IT WAITS TOO.
    clean()
    wrapping.corrected = True
    wrong += report("a turn already corrected waits from then on",
                    wrapping.held("play badass on youtube"), True)
    clean()

    # A NAME A FUNCTION BOTH ASSIGNS AND CALLS IS LOCAL FOR THE WHOLE FUNCTION, SO THE CALL
    # THROWS "cannot access local variable" NO MATTER THAT A MODULE-LEVEL ONE EXISTS.
    # say_streaming CALLS taken() AT THE TOP AND ASSIGNS taken FOR THE CLOCK AT THE BOTTOM,
    # WHICH BROKE EVERY GUARDED TURN WHILE EVERY TEST HERE WENT ON PASSING — THE MIDDLEWARE
    # SWALLOWS WHAT THE GUARD RAISES, SO NOTHING THAT CALLS A GUARD CAN SEE IT. READING THE
    # SOURCE IS THE ONLY THING THAT CAN.
    import ast
    import inspect

    def shadowed(module):
        """EVERY FUNCTION IN module THAT ASSIGNS A NAME IT ALSO CALLS."""
        tree = ast.parse(inspect.getsource(module))
        known = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}

        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                known |= {each.asname or each.name.split(".")[0] for each in node.names}

        found = []

        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            declared = set()

            for sub in ast.walk(fn):
                if isinstance(sub, ast.Global):
                    declared |= set(sub.names)

            assigned = {t.id for s in ast.walk(fn) if isinstance(s, ast.Assign)
                        for t in s.targets if isinstance(t, ast.Name)}
            called = {s.func.id for s in ast.walk(fn)
                      if isinstance(s, ast.Call) and isinstance(s.func, ast.Name)}

            for name in sorted((assigned & called & known) - declared):
                found.append(f"{fn.name}() assigns and calls {name}")

        return found

    from brain import thinking

    for module in (wrapping, guarding, thinking):
        wrong += report(f"nothing in {module.__name__} shadows a name it calls",
                        shadowed(module), [])

    # A SEND-BACK THAT CAME TO NOTHING KEEPS THE FIRST ANSWER, SO THERE IS NOTHING TO UNSAY.
    wrong += report("a send-back that came to nothing withdraws nothing",
                    withdrawn(guessed, reaching=False), 0)

    # AND IT IS READ ONCE: A SECOND READ WOULD UNSAY WORDS NOBODY WROTE.
    wrong += report("a withdrawal is read once and then gone", wrapping.taken(), 0)

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
                 "ASKED_FRESH", "ASKED_TOLD", "ASKED_AGAIN"):
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
