"""THE GRAPH."""

import time
import threading

from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

import hands
import memory
from brain import model as brain, persona, resuming
from brain.model import LLMError
from brain.prompt import system_prompt
from brain.wrapping import (
    LIMIT,
    MODEL,
    Stuck,
    amiss,
    doings,
    fresh,
    keep_count,
    keep_going,
    keep_recent,
    keep_record,
    keep_trying,
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
                keep_record,
                keep_going,
                ModelCallLimitMiddleware(run_limit=settings.get("brain.calls")),
                # LAST, SO IT SITS CLOSEST TO THE MODEL: A GO THROWN AWAY OVER BAD
                # JSON IS NOT A ROUND ANYBODY ASKED FOR AND IS NOT COUNTED AS ONE.
                keep_trying,
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

        straight = self.direct(speech, context)

        if straight is not None:
            memory.close(straight, time.perf_counter() - started)
            self.carry(speech, straight)

            return straight

        try:
            done = graph.invoke(self.turn(speech, context), self.config())
        except Stuck as stuck:
            memory.close(str(stuck), time.perf_counter() - started)

            return str(stuck)
        except Exception as error:
            raise LLMError(brain.reason(error))

        # A ROUND THAT THOUGHT AND THEN SAID NOTHING, NOR ASKED FOR A TOOL, STILL ENDS ON WORDS.
        reply = worded(done["messages"][-1].text.strip()) or NOTHING
        memory.close(reply, time.perf_counter() - started)

        return reply

    def say_streaming(self, speech, context=None, **about):
        """THE REPLY IN PIECES, FOR HANDING SENTENCES TO THE VOICE AS THEY LAND."""
        graph, prompt, bound = self.ready()
        memory.begin(speech, **about)
        fresh()
        reply = ""
        started = time.perf_counter()

        straight = self.direct(speech, context)

        if straight is not None:
            memory.close(straight, time.perf_counter() - started)
            self.carry(speech, straight)

            yield straight

            return

        try:
            for chunk, note in graph.stream(
                self.turn(speech, context), self.config(), stream_mode="messages"
            ):
                if self.stopping.is_set():
                    break

                piece = spoken(chunk, note)

                if piece:
                    reply += piece
                    memory.progress(len(reply))

                    yield piece

                if self.stopping.is_set():
                    break

            # NOT ONE WORD CAME OUT, SO WHATEVER ENDED THE RUN ENDED IT SOMEWHERE THE STREAM
            # CANNOT SEE.
            if not reply.strip() and not self.stopping.is_set():
                last = self.ending() or NOTHING
                reply += last

                yield last
        except Stuck as stuck:
            # NOT A FAILURE OF HAPPY'S, SO IT IS SAID RATHER THAN SHOWN AS TROUBLE.
            reply += str(stuck)

            yield str(stuck)
        except Exception as error:
            # SHOWN IN THE BACKEND'S WORDS FOR WHOEVER READS THE LOG, SAID IN HAPPY'S
            # FOR WHOEVER IS IN THE ROOM. A TURN NEVER ENDS ON SILENCE.
            amiss(brain.reason(error))
            reply += BROKE

            yield BROKE
        finally:
            taken = time.perf_counter() - started
            tell(MODEL, None, taken)

            # THE YIELDS ABOVE CANNOT RUN WHEN THE CONSUMER LET GO OF THIS GENERATOR PART WAY
            # THROUGH, AND A ROW WITH NO REPLY IN IT READS AS HAPPY SAYING NOTHING AT ALL. SO
            # THE LAST WORD IS SETTLED HERE, WHERE IT IS WRITTEN DOWN, AS WELL AS THERE.
            if not reply.strip() and not self.stopping.is_set():
                reply = self.ending() or NOTHING

            said = reply.strip()

            memory.close(said or None, taken)
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


def spoken(chunk, note):
    """THE TEXT IN A CHUNK THAT A PERSON SHOULD HEAR, OR None."""
    if note.get("langgraph_node") != MODEL_NODE:
        return None

    # A CHUNK CARRYING TOOL CALLS CAN CARRY TEXT TOO, AND THAT TEXT IS THE ONLY
    # WARNING BEFORE THE PANEL GOES QUIET FOR AS LONG AS THE TOOL TAKES.
    return chunk.text or None
