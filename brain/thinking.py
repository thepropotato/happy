"""THE GRAPH."""

import time
import threading

from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

import hands
import memory
from face import show
from brain import model as brain, persona, resuming
from brain.model import LLMError
from brain.prompt import system_prompt
from sound import earcon
from brain import wrapping
from brain.wrapping import (
    LIMIT,
    MODEL,
    Stuck,
    amiss,
    doings,
    fresh,
    keep_able,
    keep_at_it,
    keep_count,
    keep_finishing,
    keep_fresh,
    keep_going,
    keep_honest,
    keep_looking,
    keep_named,
    keep_opened,
    keep_opening,
    keep_reading,
    keep_recent,
    keep_record,
    keep_trying,
    keep_thinking,
    tell,
    troubles,
    watches,
)
from memory import routines, settings

MODEL_NODE = "model"

# mcps IS HERE BECAUSE CONNECTING A SERVICE ADDS TOOLS.
GROUPS = ("brain", "mcps")

THREAD = "happy"

RAN_OUT = (
    "I ran out of steps before I got that finished. Ask me again and I will carry "
    "on from where I got to."
)

# NOBODY IS EVER LEFT WITHOUT AN ANSWER: A TURN THAT PRODUCED NO WORDS OF ITS OWN
# ENDS ON ONE OF THESE INSTEAD OF ON SILENCE.
NOTHING = (
    "I got tangled up on that one and never got an answer out. Ask me again and I "
    "will have another go at it."
)

BROKE = "Something went wrong at my end on that one, so I did not get it done."


def said(done):
    """THE WORDS OUT OF WHICHEVER LOOP ANSWERED."""
    if isinstance(done, dict):
        return done["messages"][-1].text.strip()

    return (getattr(done, "reply", "") or "").strip()


def stamp():
    """WHERE EVERY GROUP THE GRAPH IS MADE OF STANDS RIGHT NOW."""
    return (*(settings.version(each) for each in GROUPS), routines.version())


class Happy:
    """THE ASSISTANT. ONE PER SESSION, IT REMEMBERS WITHIN THAT SESSION."""

    def __init__(self, model=None, tools=None, prompt=None):
        self.given = model
        self.stopping = threading.Event()

        # HELD, NOT RESOLVED: WHAT IS ON OFFER CHANGES WHILE HAPPY IS RUNNING.
        self.handed = tools
        self.wording = prompt

        self.thread = THREAD

        # OUTLIVES EVERY REBUILD, SO A SETTING CHANGE DOES NOT COST THE CONVERSATION.
        self.kept = InMemorySaver()

        self.version = None

        self.assemble()
        self.resume()

    def resume(self):
        """WHAT WAS SAID BEFORE THIS SESSION GOES ON THE THREAD FIRST, SO A FOLLOW-UP TO
        YESTERDAY HAS SOMETHING BEHIND IT. THE TABLE IS THE CONVERSATION; THIS IS A READ OF IT."""
        try:
            earlier = resuming.messages()

            if earlier:
                self.graph.update_state(self.config(), {"messages": earlier})
        except Exception:
            pass

    def assemble(self):
        """THE GRAPH, BUILT OUT OF WHATEVER THE SETTINGS SAY RIGHT NOW."""
        self.model = self.given or brain.create()
        bound_tools = hands.tools() if self.handed is None else self.handed
        built_prompt = self.wording or system_prompt()
        graph = create_agent(
            model=self.model,
            tools=bound_tools,
            system_prompt=built_prompt,
            middleware=[
                keep_recent,
                keep_count,
                keep_named,
                keep_record,
                keep_going,
                # AFTER THE TOOLS HAVE RUN AND BEFORE THE WORDS GO OUT: THE LAST THING THAT
                # CAN STOP A TURN TELLING SOMEBODY A THING HAPPENED WHEN IT DID NOT.
                keep_honest,
                # AND THE OTHER HALF OF THE SAME JOB: A TURN MAY NOT SAY SORRY AND STOP
                # WHILE A GUARD IS STILL HOLDING THE DOOR OPEN FOR IT.
                keep_at_it,
                # AND A TURN MAY NOT TALK ITSELF OUT OF A JOB IT HAS A TOOL FOR.
                keep_able,
                # NOR END ON WHAT IT IS ABOUT TO DO, WITH THE DOING LEFT UNDONE.
                keep_finishing,
                # NOR HAND THE JOB BACK BY NAMING A LINK ONLY IT CAN SEE.
                keep_opening,
                # NOR ANSWER A QUESTION ABOUT WHAT IS IN FRONT OF THEM OUT OF ITS OWN MEMORY.
                # THE WRITING TOOLS GUARD THIS FOR FILES; A SPOKEN ANSWER PASSES ONLY HERE.
                keep_looking,

                # AND THE SAME FOR WHAT MOVES WHERE NOBODY IS LOOKING: A MAILBOX, A CHAT,
                # A CALENDAR. THE SCREEN GUARD ABOVE DOES NOT COVER THOSE.
                keep_fresh,

                # AND NOR SUMMARISE A FILE WITHOUT READING ALL OF IT WHEN IT CAME IN CHUNKS.
                keep_reading,

                # A BIG SERVICE'S TOOLS ARE HIDDEN UNTIL THIS TURN HAS ASKED FOR THAT
                # SERVICE, SO A PROMPT DOES NOT CARRY SEVENTY-THREE SCHEMAS NOBODY WANTED.
                keep_opened,

                ModelCallLimitMiddleware(run_limit=settings.get("brain.calls")),
                # LAST, SO IT SITS CLOSEST TO THE MODEL: A GO THROWN AWAY OVER BAD
                # JSON IS NOT A ROUND ANYBODY ASKED FOR AND IS NOT COUNTED AS ONE.
                keep_trying,
                keep_thinking,
            ],
            checkpointer=self.kept,
        )
        # A SERVICE CONNECTING MID SESSION MOVES THE PREFIX, SO THE READING DONE AT STARTUP
        # IS NOW THE WRONG READING.
        moved = self.version is not None and prefix(built_prompt, bound_tools) != prefix(self.prompt, self.tools)

        self.version = stamp()
        self.tools = bound_tools
        self.prompt = built_prompt
        self.graph = graph

        if moved:
            self.rewarm()

        return graph, built_prompt, bound_tools

    def rewarm(self):
        """READ THE NEW PREFIX ON A THREAD OF ITS OWN. NOBODY WAITS ON THIS."""
        threading.Thread(target=self.quietly, daemon=True).start()

    def quietly(self):
        """warm(), WITH ANY TROUBLE SWALLOWED — A FAILED WARM COSTS ONLY TIME."""
        try:
            self.warm()
        except Exception:
            pass

    def ready(self):
        """THE GRAPH, REBUILT FIRST IF A SETTING IT IS MADE OF HAS MOVED."""
        if self.version != stamp():
            self.assemble()

        return self.graph, self.prompt, self.tools

    def refit(self):
        """REBUILD ONLY IF A SETTING THE GRAPH IS MADE OF HAS MOVED SINCE."""
        if self.version != stamp():
            self.assemble()

    def warm(self):
        brain.warm(self.model, self.prompt, self.tools)

    def say(self, speech, context=None, **about):
        """THE WHOLE REPLY AS ONE STRING."""
        graph, prompt, bound = self.ready()

        memory.begin(speech, **about)
        fresh()
        started = time.perf_counter()

        try:
            straight = self.direct(speech, context)

            if straight is not None:
                memory.close(straight, time.perf_counter() - started)
                self.carry(speech, straight)

                return straight

            try:
                done = self.round(graph, speech, context)
            except Stuck as stuck:
                memory.close(str(stuck), time.perf_counter() - started)

                return str(stuck)
            except Exception as error:
                raise LLMError(brain.reason(error))

            # A ROUND THAT THOUGHT AND THEN SAID NOTHING, NOR ASKED FOR A TOOL, STILL ENDS ON WORDS.
            reply = worded(said(done)) or NOTHING
            memory.close(reply, time.perf_counter() - started)

            return reply
        finally:
            earcon.stop()

    def round(self, graph, speech, context):
        """ONE TURN, RUN BY WHICHEVER LOOP THE SETTINGS NAME.

        BOTH ARE BUILT AND BOTH CARRY THE SAME GUARDS; WHICH ONE ANSWERS IS ONE SETTING, SO
        bench/replay.py CAN SCORE EITHER WITHOUT THE CODE MOVING."""
        if not settings.get("brain.signatures"):
            return graph.invoke(self.turn(speech, context), self.config())

        from brain import asking, erranding  # LATE: erranding READS THE PROMPT AND THE TOOLS.

        import dspy

        dspy.configure(lm=asking.ready(asking.THINKING))

        loop = erranding.built(self.tools, self.prompt, settings.get("brain.calls"))

        return loop(said=speech)

    def say_streaming(self, speech, context=None, **about):
        """THE REPLY IN PIECES, FOR HANDING SENTENCES TO THE VOICE AS THEY LAND.

        ONLY THE CLOSING ROUND IS SPOKEN. A ROUND THAT GOES ON TO CALL A TOOL IS MID-JOB
        WHATEVER IT WROTE, AND WHAT IT WROTE READS AS AN ANNOUNCEMENT OF SOMETHING NOT DONE
        YET — "THE SITE IS UP, LET ME PULL UP THE PROJECT" WHILE THAT PAGE IS STILL A TOOL
        CALL AWAY. THAT SOUNDS LIKE THE END OF THE TURN AND IS NOT ONE, SO IT IS SHOWN ON THE
        PANEL AND NEVER HANDED TO THE VOICE. THE EARCON FILLS THE WHOLE GAP INSTEAD."""
        graph, prompt, bound = self.ready()
        memory.begin(speech, **about)
        fresh()

        # EVERYTHING SAID ACROSS THE WHOLE TURN, FOR THE ENDING() FALLBACK AND MEMORY.
        reply = ""

        # WHAT THE ROUND IN HAND HAS WRITTEN. THROWN AWAY UNSPOKEN THE MOMENT THAT ROUND
        # DECIDES TO CALL A TOOL, AND SPOKEN ONLY IF THE STREAM ENDS WITH IT STILL HERE,
        # WHICH IS WHAT MAKES IT THE CLOSING ANSWER.
        unspoken = ""

        # WHAT HAS BEEN WRITTEN BUT NOT YET DRAWN. ON A TURN A GUARD MAY HOLD, WORDS WAIT
        # HERE UNTIL THE ROUND IS PAST THE GUARDS RATHER THAN GOING STRAIGHT ONTO THE PANEL
        # TO BE TAKEN OFF AGAIN A SECOND LATER.
        undrawn = ""

        # WHETHER ANYTHING AT ALL HAS GONE TO THE VOICE. reply CANNOT ANSWER THIS ANY MORE:
        # IT HOLDS THE MID-TURN WORDS TOO, AND THOSE ARE SHOWN AND NEVER SAID.
        said_aloud = False
        waiting = wrapping.held(speech)
        started = time.perf_counter()

        straight = self.direct(speech, context)

        if straight is not None:
            memory.close(straight, time.perf_counter() - started)
            self.carry(speech, straight)

            # NOTHING STREAMED THIS ONE, SO NOTHING HAS SHOWN IT YET.
            show.piece(straight)

            yield straight

            return

        try:
            for chunk, note in graph.stream(
                self.turn(speech, context), self.config(), stream_mode="messages"
            ):
                if self.stopping.is_set():
                    break

                # A GUARD TURNED THE LAST ROUND BACK, SO WHAT IT SAID IS NOT THE ANSWER ANY
                # MORE. IT IS TAKEN OFF THE PANEL AND NEVER SPOKEN: unspoken IS ONLY HANDED
                # TO THE VOICE WHEN THE STREAM ENDS, WHICH COMES AFTER THIS, SO A WITHDRAWN
                # ROUND DIES BEFORE IT IS EVER HEARD.
                given = wrapping.taken()

                if given:
                    reply = reply[:-given] if given < len(reply) else ""
                    unspoken = unspoken[:-given] if given < len(unspoken) else ""

                    # WORDS STILL WAITING WERE NEVER DRAWN, SO THEY ARE DROPPED RATHER THAN
                    # UNSAID, AND ONLY WHAT REALLY REACHED THE PANEL IS TAKEN BACK OFF IT.
                    kept = min(given, len(undrawn))
                    undrawn = undrawn[:-kept] if kept else undrawn

                    if given > kept:
                        show.unsay(given - kept)

                # A ROUND DECIDING TO CALL A TOOL IS NOT FINISHED, SO WHATEVER IT WROTE ON
                # THE WAY THERE IS AN ANNOUNCEMENT OF A STEP AND NOT AN ANSWER. IT IS SHOWN
                # AND THEN DROPPED UNSPOKEN, AND THE TURN'S ONE SPOKEN ANSWER IS WHATEVER
                # THE ROUND THAT CALLS NOTHING SAYS AT THE END.
                # A CHUNK MAY CARRY TEXT AND A TOOL CALL AT ONCE, SO THE ROUND IS JUDGED
                # BEFORE ITS OWN WORDS ARE TAKEN IN: OTHERWISE THE CLEAR BELOW RUNS AND THEN
                # THIS VERY CHUNK PUTS THE ANNOUNCEMENT STRAIGHT BACK.
                reaching = asking(chunk, note)

                if reaching and unspoken.strip():
                    # THIS ROUND IS PAST THE GUARDS: IT ASKED FOR A TOOL, WHICH IS THE ONE
                    # THING NONE OF THEM TURNS BACK. WHAT IT SAID CAN BE DRAWN NOW.
                    if undrawn:
                        show.piece(undrawn)
                        undrawn = ""

                    unspoken = ""

                piece = spoken(chunk, note)

                if piece:
                    reply += piece
                    memory.progress(len(reply))

                    # THE WORDS OF A ROUND THAT IS ALREADY REACHING FOR A TOOL ARE SHOWN AND
                    # NEVER HEARD, SO THEY GO NOWHERE NEAR THE VOICE.
                    if not reaching:
                        unspoken += piece

                    # SHOWN AS IT ARRIVES, NEVER YIELDED AS IT ARRIVES — UNLESS THIS IS A
                    # TURN A GUARD MAY TURN BACK, IN WHICH CASE IT WAITS RATHER THAN BEING
                    # DRAWN NOW AND UNDRAWN IN A SECOND.
                    if waiting:
                        undrawn += piece
                    else:
                        show.piece(piece)

                if self.stopping.is_set():
                    break

            # THE STREAM IS OVER, SO NOTHING IS GOING TO TURN THIS BACK NOW: WHATEVER WAS
            # HELD IS THE ANSWER AND GOES ON THE PANEL.
            if undrawn:
                show.piece(undrawn)
                undrawn = ""

            # THE ROUND IN HAND CALLED NOTHING AND THE STREAM IS OVER, WHICH IS WHAT MAKES
            # IT THE CLOSING ANSWER AND THE ONE THING SPOKEN ALL TURN.
            if unspoken.strip() and not self.stopping.is_set():
                said_aloud = True

                yield unspoken
                unspoken = ""

            # NOTHING WAS SPOKEN ALL TURN. EITHER NO ROUND SAID ANYTHING, OR EVERY ROUND
            # THAT DID WENT ON TO CALL A TOOL AND WAS DROPPED, WHICH LEAVES THE LAST TOOL'S
            # RESULT SITTING THERE WITH NOBODY SAYING WHAT CAME OF IT.
            if not said_aloud and not self.stopping.is_set():
                last = self.ending() or NOTHING
                reply += last

                show.piece(last)

                yield last
        except Stuck as stuck:
            # WHATEVER WAS BEING HELD WHEN THIS LANDED IS STILL WHAT WAS SAID, AND LOSING IT
            # WOULD LEAVE THE PANEL SHOWING NOTHING AT ALL.
            if undrawn:
                show.piece(undrawn)
                undrawn = ""

            reply += str(stuck)
            said_aloud = True
            show.piece(str(stuck))

            yield str(stuck)
        except Exception as error:
            if undrawn:
                show.piece(undrawn)
                undrawn = ""

            amiss(brain.reason(error))
            reply += BROKE
            show.piece(BROKE)

            yield BROKE
        finally:
            earcon.stop()
            taken = time.perf_counter() - started
            tell(MODEL, None, taken)

            said = reply.strip()

            memory.close(said or None, taken, spent=show.cost())
            self.settle(said)

    def direct(self, speech, context=None):
        """A ROUTINE ASKED FOR BY NAME, RUN WITHOUT THE MODEL DECIDING WHETHER TO."""
        from brain import running

        return None if context is not None else running.plainly(speech)

    def carry(self, speech, said):
        """A TURN THE GRAPH NEVER RAN, PUT ON THE CONVERSATION ANYWAY, SO "RENAME THAT" AND
        "RUN IT AGAIN" STILL HAVE SOMETHING BEHIND THEM."""
        try:
            self.graph.update_state(
                self.config(), {"messages": [HumanMessage(speech), AIMessage(said)]}
            )
        except Exception:
            pass

    def settle(self, said):
        """WHAT WAS ANSWERED GOES ON THE CONVERSATION EVEN WHEN THE RUN NEVER PUT IT THERE,
        SO THE NEXT TURN DOES NOT OPEN ON TWO QUESTIONS IN A ROW WITH NOTHING BETWEEN THEM."""
        if not said:
            return

        try:
            kept = self.graph.get_state(self.config()).values.get("messages") or []

            if kept and getattr(kept[-1], "type", "") == "ai":
                return

            self.graph.update_state(self.config(), {"messages": [AIMessage(said)]})
        except Exception:
            pass

    def ending(self):
        """THE RUN'S LAST WORD WHEN THE STREAM CARRIED NONE, OR "" IF THERE IS NONE."""
        try:
            kept = self.graph.get_state(self.config()).values.get("messages") or []
        except Exception:
            return ""

        last = kept[-1] if kept else None

        # A TOOL'S OWN OUTPUT IS NOT AN ANSWER, AND READING ONE OUT WOULD BE WORSE
        # THAN THE SILENCE THIS IS HERE TO FIX.
        if getattr(last, "type", "") != "ai":
            return ""

        return worded((last.text or "").strip())

    def stop(self):
        self.stopping.set()

    def start_turn(self):
        self.stopping.clear()

    def forget(self):
        """A CLEAN SLATE. A NEW THREAD IS CHEAPER THAN EMPTYING THE OLD ONE."""
        self.thread = f"{THREAD}-{id(object())}"

    def turn(self, speech, context=None):
        """WHAT WAS SAID, WITH WHERE IT WAS SAID IN FRONT OF IT AND HOW TO SAY IT BACK BEHIND."""
        said = f"{context}\n\n{speech}" if context else speech
        reminder = persona.nudge(settings.get("brain.persona"))

        return {"messages": [HumanMessage(f"{said}\n\n{reminder}" if reminder else said)]}

    def config(self):
        return {"configurable": {"thread_id": self.thread}}


def prefix(prompt, bound):
    """THE PREFIX AS THE SERVER SEES IT."""
    return prompt, tuple(each.name for each in bound)


def missing_tool_error(error):
    """KEPT FOR CALLERS THAT MAY REFERENCE IT; ALWAYS FALSE — THIS NEVER FIRES."""
    return False


def worded(said):
    """A RUN THAT RAN OUT OF ROUNDS, IN HAPPY'S WORDS INSTEAD OF THE COUNTER'S."""
    return RAN_OUT if said.startswith(LIMIT) else said


def answer(reply, aside):
    """THE ANSWER ITSELF: WHAT CAME AFTER THE LAST TIME A ROUND WENT OFF TO CALL A TOOL.

    IF NOTHING CAME AFTER IT, THE PREAMBLE IS ALL THERE IS AND IT IS KEPT — SAYING SOMETHING
    HALF-FINISHED BEATS SAYING NOTHING, WHICH IS THE ONE THING A TURN MAY NOT DO."""
    if not aside or aside >= len(reply):
        return reply

    return reply[aside:] if reply[aside:].strip() else reply


def asking(chunk, note):
    """WHETHER THIS CHUNK IS A ROUND DECIDING TO CALL A TOOL, SO ANY WORDS SO FAR WERE ONLY
    THE THINKING OUT LOUD THAT CAME BEFORE IT."""
    if note.get("langgraph_node") != MODEL_NODE:
        return False

    return bool(getattr(chunk, "tool_calls", None) or getattr(chunk, "tool_call_chunks", None))


def spoken(chunk, note):
    """THE TEXT IN A CHUNK THAT A PERSON SHOULD HEAR, OR None."""
    if note.get("langgraph_node") != MODEL_NODE:
        return None

    # A CHUNK CARRYING TOOL CALLS CAN CARRY TEXT TOO, AND THAT TEXT IS THE ONLY
    # WARNING BEFORE THE PANEL GOES QUIET FOR AS LONG AS THE TOOL TAKES.
    return chunk.text or None