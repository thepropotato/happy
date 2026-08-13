"""THE GRAPH. SPEECH IN, A SPOKEN ANSWER OUT, TOOLS CALLED ALONG THE WAY.

ONE LOOP: THE MODEL SEES EVERY TOOL AT ONCE, CALLS WHAT IT NEEDS, READS WHAT
CAME BACK, ANSWERS. A ROUTER THAT PICKS AN AGENT THAT THEN THINKS FOR ITSELF
COSTS TWO MORE ROUND TRIPS, WHICH IS SECONDS OF A PERSON WAITING FOR A SENTENCE.

HISTORY LIVES IN THE CHECKPOINTER UNDER ONE THREAD, TRIMMED ON THE WAY IN.
"""

import time
import threading

from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

import hands
import memory
from brain import model as brain
from brain.model import LLMError
from brain.prompt import system_prompt
from brain.watching import MODEL, Stuck, fresh, keep_count, keep_recent, keep_record, tell, watches
from memory import settings

MODEL_NODE = "model"

# mcps IS HERE BECAUSE CONNECTING A SERVICE ADDS TOOLS.
GROUPS = ("brain", "mcps")

THREAD = "happy"

# HOW THE CALL LIMIT SAYS SO, IN ITS OWN WORDS: "Model call limits exceeded: run
# limit (14/14)". EVERY WORD HERE IS READ OUT LOUD, AND THAT IS A COUNTER.
LIMIT = "Model call limits exceeded"

RAN_OUT = (
    "I ran out of steps before I got that finished. Ask me again and I will carry "
    "on from where I got to."
)


def stamp():
    """WHERE EVERY GROUP THE GRAPH IS MADE OF STANDS RIGHT NOW."""
    return tuple(settings.version(each) for each in GROUPS)


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

    def assemble(self):
        """THE GRAPH, BUILT OUT OF WHATEVER THE SETTINGS SAY RIGHT NOW.

        ONE GRAPH, ONE PROMPT, ONE TOOL LIST — AND THAT IS THE POINT, NOT AN
        OVERSIGHT. THE STANDING PROMPT AND THE TOOL SCHEMAS ARE THE FIRST TWELVE
        THOUSAND TOKENS OF EVERY REQUEST, AND A SERVER THAT HAS READ THEM ONCE
        ANSWERS IN HALF A SECOND INSTEAD OF TEN. IT ONLY HOLDS THAT READING FOR
        A COUPLE OF DISTINCT PROMPTS AT A TIME, SO HANDING IT A SECOND SHAPE —
        A NARROWER TOOL LIST, AN EXTRA PARAGRAPH — COSTS MORE THAN EVERY TOKEN
        IT SAVES. WHATEVER IS BUILT HERE IS WHAT warm() READS AT STARTUP.
        """
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
                ModelCallLimitMiddleware(run_limit=settings.get("brain.calls")),
            ],
            checkpointer=self.kept,
        )
        # A SERVICE CONNECTING MID SESSION MOVES THE PREFIX, SO THE READING DONE
        # AT STARTUP IS NOW THE WRONG READING. GET THE NEW ONE READ WHILE NOBODY
        # IS TALKING, OR THE NEXT THING SAID PAYS TEN TO TWENTY SECONDS FOR IT.
        # THE FIRST BUILD IS NOT WARMED HERE: main.py DOES THAT ONE ALOUD.
        moved = self.version is not None and shape(built_prompt, bound_tools) != shape(self.prompt, self.tools)

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
            done = graph.invoke(self.turn(speech, context), self.config())
        except Stuck as stuck:
            memory.close(str(stuck), time.perf_counter() - started)

            return str(stuck)
        except Exception as error:
            raise LLMError(brain.reason(error))

        reply = worded(done["messages"][-1].text.strip())
        memory.close(reply, time.perf_counter() - started)

        return reply

    def say_streaming(self, speech, context=None, **about):
        """THE REPLY IN PIECES, FOR HANDING SENTENCES TO THE VOICE AS THEY LAND."""
        graph, prompt, bound = self.ready()
        memory.begin(speech, **about)
        fresh()
        reply = ""
        started = time.perf_counter()

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

            # NOT ONE WORD CAME OUT, SO WHATEVER ENDED THE RUN ENDED IT SOMEWHERE
            # THE STREAM CANNOT SEE. SAY WHAT IT LEFT BEHIND RATHER THAN GO QUIET.
            # BUT NOT WHEN THE PERSON STOPPED IT THEMSELVES — THAT SILENCE IS THE POINT.
            if not reply.strip() and not self.stopping.is_set():
                last = self.ending()

                if last:
                    reply += last

                    yield last
        except Stuck as stuck:
            # NOT A FAILURE OF HAPPY'S, SO IT IS SAID RATHER THAN SHOWN AS TROUBLE.
            reply += str(stuck)

            yield str(stuck)
        except Exception as error:
            raise LLMError(brain.reason(error))
        finally:
            taken = time.perf_counter() - started
            tell(MODEL, None, taken)

            memory.close(reply.strip() or None, taken)

    def ending(self):
        """THE RUN'S LAST WORD WHEN THE STREAM CARRIED NONE, OR "" IF THERE IS NONE.

        A RUN THAT STOPS ANYWHERE BUT THE MODEL LEAVES ITS LAST MESSAGE AS A STATE
        UPDATE, AND stream_mode "messages" ONLY CARRIES WHAT AN LLM ACTUALLY
        GENERATED. SO IT WAS DROPPED WHOLE: NOTHING SPOKEN, NOTHING SHOWN, AND A
        NULL REPLY WRITTEN DOWN. RUNNING OUT OF ROUNDS IS THE ONE THAT HAPPENS,
        AND FROM WHERE A PERSON SITS IT LOOKED LIKE HAPPY DYING MID SENTENCE.
        """
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
        """WHAT WAS SAID, WITH WHERE IT WAS SAID IN FRONT OF IT WHEN THAT IS KNOWN.

        ONE MESSAGE AND NOT TWO, SO NOTHING DOWNSTREAM HAS TO KNOW THIS HAPPENED.
        THE BARE WORDS ARE STILL WHAT GETS CLASSIFIED, SHOWN AND REMEMBERED: A
        TURN IS NOT A DIFFERENT TURN FOR HAVING ARRIVED SOMEWHERE.
        """
        return {"messages": [HumanMessage(f"{context}\n\n{speech}" if context else speech)]}

    def config(self):
        return {"configurable": {"thread_id": self.thread}}


def shape(prompt, bound):
    """THE PREFIX AS THE SERVER SEES IT. THE TOOL OBJECTS THEMSELVES ARE REMADE
    ON EVERY BUILD, SO COMPARING THEM SAYS EVERYTHING MOVED WHEN NOTHING DID."""
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