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
from langchain_core.messages import HumanMessage, RemoveMessage
from langgraph.checkpoint.memory import InMemorySaver

import hands
import memory
from brain import intent, model as brain
from brain.model import LLMError
from brain.prompt import system_prompt
from brain.watching import MODEL, Stuck, fresh, keep_count, keep_recent, keep_record, tell, watches
from memory import settings

PROFILE = "profile"
TOOLS_STAT = "tools"

# WIDER THAN ANY SINGLE PROFILE — A GENERIC SIGNAL THAT THE TURN PROBABLY NEEDED A TOOL.
ACTION_HINTS = {
    "send", "text", "message", "call", "ring", "email", "mail", "slack",
    "whatsapp", "open", "play", "search", "watch", "remember", "forget",
    "turn on", "turn off", "book", "buy", "find", "show", "read", "attach",
}

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

        # KEYED BY PROFILE FROZENSET; CLEARED ENTIRELY ON SETTINGS CHANGE.
        self.graphs = {}

        self.assemble()

    def assemble(self, profile=None):
        """THE GRAPH, BUILT OUT OF WHATEVER THE SETTINGS SAY RIGHT NOW.

        profile IS A frozenset OF INTENT LABELS OR None FOR THE FULL DEFAULT.
        """
        self.model = self.given or brain.create()
        bound_tools = hands.tools(profile) if self.handed is None else self.handed
        built_prompt = self.wording or system_prompt(profile)
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
        self.graphs[profile] = (graph, built_prompt, bound_tools)
        self.version = stamp()

        # KEEP WARM() POINTING AT THE DEFAULT GRAPH.
        if profile is None:
            self.tools = bound_tools
            self.prompt = built_prompt
            self.graph = graph

        return graph, built_prompt, bound_tools

    def graph_for(self, profile):
        """THE CACHED GRAPH FOR THIS PROFILE, BUILT ON FIRST USE."""
        if self.version != stamp():
            self.graphs.clear()
            self.assemble()

        if profile not in self.graphs:
            self.assemble(profile)

        return self.graphs[profile]

    def refit(self):
        """REBUILD ONLY IF A SETTING THE GRAPH IS MADE OF HAS MOVED SINCE."""
        if self.version != stamp():
            self.graphs.clear()
            self.assemble()

    def warm(self):
        brain.warm(self.model, self.prompt, self.tools)

    def say(self, speech, **about):
        """THE WHOLE REPLY AS ONE STRING."""
        profile = intent.classify(speech)
        graph, prompt, bound = self.graph_for(profile)
        log_context(prompt, bound)

        memory.begin(speech, **about)
        fresh()
        started = time.perf_counter()
        before = 0

        try:
            state_before = self.graph.get_state(self.config())
            before = len((state_before.values.get("messages") or []))
        except Exception:
            pass

        try:
            done = graph.invoke(self.turn(speech), self.config())
        except Stuck as stuck:
            memory.close(str(stuck), time.perf_counter() - started)

            return str(stuck)
        except Exception as error:
            raise LLMError(brain.reason(error))

        # IF A NARROW PROFILE WAS USED AND AN ACTION WORD FIRED BUT NO TOOL RAN,
        # RETRY ONCE WITH THE FULL TOOL SET — THE CLASSIFIER PICKED TOO NARROW.
        if profile is not None and action_hinted(speech) and not acted(done["messages"], before):
            # TRIM THE FAILED ATTEMPT SO THE RETRY REPLACES IT, NOT ADDS ALONGSIDE IT.
            trim_since(graph, self.config(), before, done["messages"])
            graph, prompt, bound = self.graph_for(None)
            log_context(prompt, bound)
            fresh()

            try:
                done = graph.invoke(self.turn(speech), self.config())
            except Exception as retry_error:
                raise LLMError(brain.reason(retry_error))

        reply = worded(done["messages"][-1].text.strip())
        memory.close(reply, time.perf_counter() - started)

        return reply

    def say_streaming(self, speech, **about):
        """THE REPLY IN PIECES, FOR HANDING SENTENCES TO THE VOICE AS THEY LAND."""
        profile = intent.classify(speech)
        graph, prompt, bound = self.graph_for(profile)
        log_context(prompt, bound)
        memory.begin(speech, **about)
        fresh()
        reply = ""
        tool_ran = False
        before = 0
        started = time.perf_counter()

        try:
            state_before = graph.get_state(self.config())
            before = len((state_before.values.get("messages") or []))
        except Exception:
            pass

        try:
            for chunk, note in graph.stream(
                self.turn(speech), self.config(), stream_mode="messages"
            ):
                if self.stopping.is_set():
                    break

                if note.get("langgraph_node") == "tools":
                    tool_ran = True

                piece = spoken(chunk, note)

                if piece:
                    reply += piece
                    memory.progress(len(reply))

                    yield piece

                if self.stopping.is_set():
                    break

            # IF A NARROW PROFILE WAS USED, AN ACTION WORD FIRED, AND NO TOOL RAN,
            # THE CLASSIFIER PICKED TOO NARROW — RETRY WITH THE FULL TOOL SET.
            if (profile is not None
                    and action_hinted(speech)
                    and not tool_ran
                    and not self.stopping.is_set()):
                reply = ""
                # TRIM THE FAILED ATTEMPT SO THE RETRY REPLACES IT, NOT ADDS ALONGSIDE IT.
                current = graph.get_state(self.config())
                trim_since(graph, self.config(), before, current.values.get("messages") or [])
                graph, prompt, bound = self.graph_for(None)
                log_context(prompt, bound)
                fresh()

                # ACCUMULATE INTO reply HERE SO THE FINALLY BLOCK RECORDS THE FULL TEXT.
                for piece in self._stream_graph(graph, speech, ""):
                    reply += piece
                    yield piece

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

    def _stream_graph(self, graph, speech, prior_reply):
        """STREAM FROM graph, APPENDING TO prior_reply. USED FOR THE RETRY PATH."""
        for chunk, note in graph.stream(
            self.turn(speech), self.config(), stream_mode="messages"
        ):
            if self.stopping.is_set():
                return

            piece = spoken(chunk, note)

            if piece:
                prior_reply += piece
                memory.progress(len(prior_reply))

                yield piece

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

    def turn(self, speech):
        return {"messages": [HumanMessage(speech)]}

    def config(self):
        return {"configurable": {"thread_id": self.thread}}


def log_context(prompt, bound):
    """EMIT PROMPT LENGTH AND TOOL COUNT SO THE STATS TABLE CAN SHOW SAVINGS."""
    tell(PROFILE, None, 0, {"prompt_chars": len(prompt), "tools": len(bound)})


def action_hinted(speech):
    """TRUE WHEN THE SPEECH CONTAINS AN ACTION WORD AS A DISTINCT WORD OR PHRASE."""
    lowered = (speech or "").lower()
    return any(intent.word_match(hint, lowered) for hint in ACTION_HINTS)


def trim_since(graph, config, before, messages):
    """REMOVE MESSAGES ADDED SINCE before SO A RETRY DOESN'T DOUBLE THE HISTORY."""
    added = (messages or [])[before:]

    if added:
        graph.update_state(config, {"messages": [RemoveMessage(id=m.id) for m in added]})


def acted(messages, before_count):
    """TRUE WHEN AT LEAST ONE ToolMessage APPEARS AFTER before_count IN messages."""
    from langchain_core.messages import ToolMessage

    return any(
        isinstance(m, ToolMessage)
        for m in (messages or [])[before_count:]
    )


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