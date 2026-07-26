"""
THE GRAPH. SPEECH IN, A SPOKEN ANSWER OUT, TOOLS CALLED ALONG THE WAY.

ONE LOOP: THE MODEL SEES EVERY TOOL AT ONCE, CALLS WHAT IT NEEDS, READS WHAT
CAME BACK, ANSWERS. THE MODULES UNDER agents/ ARE NAMESPACES FEEDING THAT ONE
LOOP AND NOT MINDS OF THEIR OWN, BECAUSE A ROUTER THAT PICKS AN AGENT THAT THEN
THINKS FOR ITSELF COSTS TWO MORE ROUND TRIPS, AND ON A MODEL RUNNING HERE THAT
IS SEVERAL SECONDS OF A PERSON WAITING FOR A SENTENCE.

HISTORY LIVES IN THE CHECKPOINTER UNDER ONE THREAD, TRIMMED ON THE WAY IN SO A
LONG AFTERNOON DOES NOT SLOWLY FILL THE CONTEXT.
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

import agents
import chat
import llm
from llm import LLMError  # RE-EXPORTED, CALLERS SHOULD NOT NEED TWO IMPORTS.

# HOW MANY MESSAGES OF BACKCHAT TO CARRY. COUNTED, NOT WEIGHED, BECAUSE COUNTING
# IS FREE AND A TOKEN COUNT WOULD MEAN A TOKENISER PER MODEL.
HISTORY_MESSAGES = 24

# HOW MANY TIMES THE MODEL MAY GO ROUND BEFORE IT HAS TO ANSWER. A LOOP THAT
# KEEPS GOING IS A PERSON STARING AT A SILENT ASSISTANT, WHICH IS WORSE THAN A
# HALF ANSWER.
MAX_MODEL_CALLS = 6

MODEL_NODE = "model"  # WHERE THE SPOKEN WORDS COME FROM. TOOL OUTPUT IS NOT SPOKEN.

THREAD = "happy"

TOOL = "tool"
MODEL = "model"

# WHOEVER WANTS TO KNOW WHERE THE TIME WENT. THE TERMINAL DOES, AND THE BRAIN
# SHOULD NOT HAVE TO KNOW THAT A TERMINAL EXISTS, SO IT IS A CALLBACK.
report = None


def watches(handler):
    """BE TOLD HOW LONG EACH PART TOOK.

    handler(kind, name, seconds) -> None, WHERE kind IS "tool" OR "model".
    """
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
    """EVERY TOOL CALL GOES IN THE CONVERSATION, WITH WHAT IT WAS ASKED AND HOW LONG."""
    started = time.perf_counter()
    result = handler(request)
    taken = time.perf_counter() - started

    call = request.tool_call
    chat.used(call.get("name"), call.get("args"), text(result), taken)
    tell(TOOL, call.get("name"), taken)

    return result


def text(result):
    """WHAT A TOOL ACTUALLY SAID, OUT OF WHATEVER WRAPPER IT CAME BACK IN."""
    return getattr(result, "content", result)


def recent(messages):
    kept = trim_messages(
        messages,
        token_counter=len,
        max_tokens=HISTORY_MESSAGES,
        strategy="last",
        start_on="human",  # NEVER OPEN ON A TOOL REPLY WHOSE CALL WAS TRIMMED AWAY.
        include_system=False,
        allow_partial=False,
    )

    return kept or messages[-1:]  # TRIMMING TO NOTHING WOULD ASK THE MODEL ABOUT NOTHING.


class Happy:
    """THE ASSISTANT. ONE PER SESSION, IT REMEMBERS WITHIN THAT SESSION."""

    def __init__(self, model=None, tools=None, prompt=None):
        self.model = model or llm.create()
        self.graph = create_agent(
            model=self.model,
            tools=agents.tools() if tools is None else tools,
            system_prompt=prompt or llm.system_prompt(),
            middleware=[
                keep_recent,
                keep_record,
                ModelCallLimitMiddleware(run_limit=MAX_MODEL_CALLS),
            ],
            checkpointer=InMemorySaver(),
        )
        self.thread = THREAD

    def warm(self):
        llm.warm(self.model)

    def say(self, speech, **about):
        """THE WHOLE REPLY AS ONE STRING."""
        chat.said(speech, **about)

        try:
            done = self.graph.invoke(self.turn(speech), self.config())
        except Exception as error:
            raise LLMError(llm.reason(error))

        reply = done["messages"][-1].text.strip()
        chat.replied(reply)

        return reply

    def say_streaming(self, speech, **about):
        """THE REPLY IN PIECES, FOR HANDING SENTENCES TO TTS AS THEY LAND."""
        chat.said(speech, **about)
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
            raise LLMError(llm.reason(error))
        finally:
            tell(MODEL, None, time.perf_counter() - started)

            # RECORDED EVEN WHEN THE ANSWER WAS CUT OFF. HALF A SENTENCE IS
            # STILL WHAT HAPPY SAID, AND THE GAP IS WORTH SEEING LATER.
            if reply.strip():
                chat.replied(reply.strip())

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


def create(**kwargs):
    return Happy(**kwargs)


def caveat():
    """WHAT THE BACKEND IN USE CANNOT DO, OR None. RE-EXPORTED FOR THE SAME
    REASON LLMError IS: NOBODY SHOULD NEED TWO IMPORTS TO START HAPPY."""
    return llm.caveat()


if __name__ == "__main__":  # THE SAME BRAIN, TYPED AT INSTEAD OF SPOKEN TO.
    happy = Happy()
    print(f"{llm.MODEL} AT {llm.url()}, TOOLS: {', '.join(agents.names())}. CTRL+C TO QUIT.\n")

    try:
        while True:
            said = input("you: ").strip()

            if not said:
                continue

            print("happy: ", end="", flush=True)

            try:
                for part in happy.say_streaming(said):
                    print(part, end="", flush=True)
            except LLMError as problem:  # FIX OLLAMA IN THE OTHER WINDOW AND ASK AGAIN.
                print(problem)

            print("\n")

    except (KeyboardInterrupt, EOFError):
        print("\nBye")
