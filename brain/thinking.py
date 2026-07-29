"""THE GRAPH. SPEECH IN, A SPOKEN ANSWER OUT, TOOLS CALLED ALONG THE WAY.

ONE LOOP: THE MODEL SEES EVERY TOOL AT ONCE, CALLS WHAT IT NEEDS, READS WHAT
CAME BACK, ANSWERS. A ROUTER THAT PICKS AN AGENT THAT THEN THINKS FOR ITSELF
COSTS TWO MORE ROUND TRIPS, WHICH IS SECONDS OF A PERSON WAITING FOR A SENTENCE.

HISTORY LIVES IN THE CHECKPOINTER UNDER ONE THREAD, TRIMMED ON THE WAY IN.
"""

import time

from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

import hands
import memory
from brain import model as brain
from brain.model import LLMError
from brain.prompt import system_prompt
from brain.watching import MODEL, keep_recent, keep_record, tell, watches
from memory import settings

MODEL_NODE = "model"  # WHERE SPOKEN WORDS COME FROM. TOOL OUTPUT IS NOT SPOKEN.

# THE GROUPS THE GRAPH IS BUILT OUT OF. mcps IS HERE BECAUSE CONNECTING A SERVICE
# ADDS TOOLS, AND A TOOL THAT ONLY ARRIVES AFTER A RESTART IS NOT CONNECTED.
GROUPS = ("brain", "mcps")

THREAD = "happy"


def stamp():
    """WHERE EVERY GROUP THE GRAPH IS MADE OF STANDS RIGHT NOW."""
    return tuple(settings.version(each) for each in GROUPS)


class Happy:
    """THE ASSISTANT. ONE PER SESSION, IT REMEMBERS WITHIN THAT SESSION."""

    def __init__(self, model=None, tools=None, prompt=None):
        self.given = model  # HANDED ONE IN MEANS NEVER BUILDING ONE FROM SETTINGS.

        # HELD, NOT RESOLVED. WHAT IS ON OFFER CHANGES WHILE HAPPY IS RUNNING, SO
        # ASKING ONCE HERE WOULD PIN THE GRAPH TO WHATEVER WAS TRUE AT STARTUP.
        self.handed = tools
        self.wording = prompt

        self.thread = THREAD

        # OUTLIVES EVERY REBUILD, SO CHANGING A SETTING MID CONVERSATION DOES NOT
        # COST THE CONVERSATION.
        self.kept = InMemorySaver()

        self.version = None
        self.assemble()

    def assemble(self):
        """THE GRAPH, BUILT OUT OF WHATEVER THE SETTINGS SAY RIGHT NOW."""
        self.model = self.given or brain.create()
        self.tools = hands.tools() if self.handed is None else self.handed
        self.prompt = self.wording or system_prompt()
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
        self.version = stamp()

    def refit(self):
        """REBUILD ONLY IF A SETTING THE GRAPH IS MADE OF HAS MOVED SINCE."""
        if self.version != stamp():
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
