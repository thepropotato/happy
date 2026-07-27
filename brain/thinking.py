"""THE GRAPH. SPEECH IN, A SPOKEN ANSWER OUT, TOOLS CALLED ALONG THE WAY.

ONE LOOP: THE MODEL SEES EVERY TOOL AT ONCE, CALLS WHAT IT NEEDS, READS WHAT
CAME BACK, ANSWERS. A ROUTER THAT PICKS AN AGENT THAT THEN THINKS FOR ITSELF
COSTS TWO MORE ROUND TRIPS, WHICH IS SECONDS OF A PERSON WAITING FOR A SENTENCE.

HISTORY LIVES IN THE CHECKPOINTER UNDER ONE THREAD, TRIMMED ON THE WAY IN.
"""

import time

from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelCallLimitMiddleware,
    wrap_model_call,
    wrap_tool_call,
)
from langchain_core.messages import HumanMessage, trim_messages
from langgraph.checkpoint.memory import InMemorySaver

import hands
import memory
from brain import model as brain
from brain.model import LLMError
from brain.prompt import system_prompt
from memory import settings

MODEL_NODE = "model"  # WHERE SPOKEN WORDS COME FROM. TOOL OUTPUT IS NOT SPOKEN.

BRAIN = "brain"  # THE ONLY GROUP OF SETTINGS THIS IS BUILT OUT OF.

THREAD = "happy"

TOOL = "tool"
MODEL = "model"

report = None


def watches(handler):
    """BE TOLD HOW LONG EACH PART TOOK. handler(kind, name, seconds)."""
    global report

    report = handler


def tell(kind, name, seconds):
    if report:
        report(kind, name, seconds)


@wrap_model_call
def keep_recent(request, handler):
    """ONLY THE LAST STRETCH OF THE CONVERSATION GOES TO THE MODEL."""
    return handler(request.override(messages=recent(request.messages)))


@wrap_tool_call
def keep_record(request, handler):
    """EVERY TOOL CALL GOES IN THE CONVERSATION, WITH ITS ARGUMENTS AND ITS TIME."""
    started = time.perf_counter()
    result = handler(request)
    taken = time.perf_counter() - started

    call = request.tool_call
    memory.used(call.get("name"), call.get("args"), text(result), taken)
    tell(TOOL, call.get("name"), taken)

    return result


def text(result):
    """WHAT A TOOL ACTUALLY SAID, OUT OF WHATEVER WRAPPER IT CAME BACK IN."""
    return getattr(result, "content", result)


def recent(messages):
    """ONLY THE LAST STRETCH. COUNTED, NOT WEIGHED: A TOKEN COUNT WOULD MEAN A
    TOKENISER PER MODEL."""
    kept = trim_messages(
        messages,
        token_counter=len,
        max_tokens=settings.get("brain.history"),
        strategy="last",
        start_on="human",  # NEVER OPEN ON A TOOL REPLY WHOSE CALL WAS TRIMMED.
        include_system=False,
        allow_partial=False,
    )

    return kept or messages[-1:]


class Happy:
    """THE ASSISTANT. ONE PER SESSION, IT REMEMBERS WITHIN THAT SESSION."""

    def __init__(self, model=None, tools=None, prompt=None):
        self.given = model  # HANDED ONE IN MEANS NEVER BUILDING ONE FROM SETTINGS.
        self.tools = hands.tools() if tools is None else tools
        self.prompt = prompt or system_prompt()
        self.thread = THREAD

        # OUTLIVES EVERY REBUILD, SO CHANGING A SETTING MID CONVERSATION DOES NOT
        # COST THE CONVERSATION.
        self.kept = InMemorySaver()

        self.version = None
        self.assemble()

    def assemble(self):
        """THE GRAPH, BUILT OUT OF WHATEVER THE BRAIN SETTINGS SAY RIGHT NOW."""
        self.model = self.given or brain.create()
        self.graph = create_agent(
            model=self.model,
            tools=self.tools,
            system_prompt=self.prompt,
            middleware=[
                keep_recent,
                keep_record,
                # HOW MANY TIMES THE MODEL MAY GO ROUND BEFORE IT HAS TO ANSWER. A
                # LOOP THAT KEEPS GOING IS A PERSON STARING AT A SILENT ASSISTANT.
                ModelCallLimitMiddleware(run_limit=settings.get("brain.calls")),
            ],
            checkpointer=self.kept,
        )
        self.version = settings.version(BRAIN)

    def refit(self):
        """REBUILD ONLY IF A BRAIN SETTING HAS MOVED SINCE THE GRAPH WAS BUILT."""
        if self.version != settings.version(BRAIN):
            self.assemble()

    def warm(self):
        brain.warm(self.model)

    def say(self, speech, **about):
        """THE WHOLE REPLY AS ONE STRING."""
        self.refit()
        memory.said(speech, **about)

        try:
            done = self.graph.invoke(self.turn(speech), self.config())
        except Exception as error:
            raise LLMError(brain.reason(error))

        reply = done["messages"][-1].text.strip()
        memory.replied(reply)

        return reply

    def say_streaming(self, speech, **about):
        """THE REPLY IN PIECES, FOR HANDING SENTENCES TO THE VOICE AS THEY LAND."""
        self.refit()
        memory.said(speech, **about)
        reply = ""
        started = time.perf_counter()

        try:
            for chunk, note in self.graph.stream(
                self.turn(speech), self.config(), stream_mode="messages"
            ):
                piece = spoken(chunk, note)

                if piece:
                    reply += piece

                    yield piece
        except Exception as error:
            raise LLMError(brain.reason(error))
        finally:
            tell(MODEL, None, time.perf_counter() - started)

            # RECORDED EVEN WHEN THE ANSWER WAS CUT OFF. HALF A SENTENCE IS STILL
            # WHAT HAPPY SAID.
            if reply.strip():
                memory.replied(reply.strip())

    def forget(self):
        """A CLEAN SLATE. A NEW THREAD IS CHEAPER THAN EMPTYING THE OLD ONE."""
        self.thread = f"{THREAD}-{id(object())}"

    def turn(self, speech):
        return {"messages": [HumanMessage(speech)]}

    def config(self):
        return {"configurable": {"thread_id": self.thread}}


def spoken(chunk, note):
    """THE TEXT IN A CHUNK THAT A PERSON SHOULD HEAR, OR None."""
    if note.get("langgraph_node") != MODEL_NODE:
        return None

    # THE TURN THAT DECIDES ON A TOOL ARRIVES HERE TOO, AS HALF BUILT ARGUMENTS.
    # READING IT OUT WOULD BE THE ASSISTANT MUTTERING JSON.
    if getattr(chunk, "tool_call_chunks", None) or getattr(chunk, "tool_calls", None):
        return None

    return chunk.text or None
