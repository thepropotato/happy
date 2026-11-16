"""A brain for any OpenAI-shaped endpoint: Ollama, LM Studio, OpenAI, OpenRouter, Groq, Gemini and the rest."""

import json
import logging
import re
import time

from openai import APIError, AsyncOpenAI
from posthog.ai.openai import AsyncOpenAI as PostHogAsyncOpenAI

from happy import tools
from happy.agent import Act, Acted, Backend, Problem, Text
from happy.agent.deeds import correction, unbacked
from happy.agent.prompt import stamped, system_prompt
from happy.observability import new_session_id, new_trace_id, provider_for
from happy.tools import Image

log = logging.getLogger("happy.agent")

STEPS = 10
FORGET_AFTER = 15 * 60
KEEP_TURNS = 12
RESULT_LIMIT = 4000
# THIS MUCH TEXT WITH NO WORD IN IT IS THE MODEL COLLAPSING INTO PUNCTUATION, NOT ANSWERING.
BABBLE = 40
# THE PROMPT AND TOOLS ALONE ARE ABOUT 2800 TOKENS, AND A SEARCH RESULT OR TWO PLUS A FEW TURNS IS MANY THOUSAND MORE.
WINDOW = 32768


def babbling(text):
    """Whether the end of what the model wrote is a run of dots and question marks with no word in it."""
    tail = text[-BABBLE:]
    return len(tail) == BABBLE and not any(c.isalnum() for c in tail) and sum(c in "?.…" for c in tail) >= BABBLE // 4


def sense(text):
    """Text up to the last word, plus the mark that closed it, with any collapse into punctuation after it dropped."""
    last = max((i for i, c in enumerate(text) if c.isalnum()), default=-1)
    if last < 0:
        return ""
    end = last + 1
    while end < len(text) and text[end] in ".!?)\"”'’":
        end += 1
    kept = text[:end]
    # AN ASIDE OPENED JUST BEFORE THE COLLAPSE NEVER CLOSES, SO IT GOES WITH IT.
    opened = kept.rfind("(")
    if opened > max(kept.rfind(")"), max(kept.rfind(m) for m in ".!?")):
        kept = kept[:opened].rstrip()
    return kept


def repair(raw):
    """Arguments a small model wrote, made into JSON when they almost are."""
    if not raw or not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except ValueError:
        pass
    fixed = raw.strip()
    fixed = re.sub(r"(\"[^\"]*\")\s*\*\s*(\d+)", lambda m: json.dumps(json.loads(m.group(1)) * int(m.group(2))), fixed)
    fixed = re.sub(r",\s*([}\]])", r"\1", fixed)
    if fixed.count("{") > fixed.count("}"):
        fixed += "}" * (fixed.count("{") - fixed.count("}"))
    try:
        return json.loads(fixed)
    except ValueError:
        return None


def unwrapped(args, params):
    """The real arguments, when a small model buried them in an envelope like {"called": true, "called_with": {...}}."""
    if not isinstance(args, dict) or not params or set(args) <= set(params):
        return args
    nested = [value for value in args.values() if isinstance(value, dict)]
    while nested:
        inner = nested.pop(0)
        if set(inner) & set(params) and set(inner) <= set(params):
            return inner
        nested += [value for value in inner.values() if isinstance(value, dict)]
    return args


class OpenAICompatible(Backend):
    def __init__(self, cfg, base_url, model, api_key="none", local=True, posthog_client=None, ai_session_id=None):
        self.cfg = cfg
        self.name = model
        self.model = model
        self.local = local
        self.posthog_client = posthog_client
        self.ai_session_id = ai_session_id or new_session_id("happy")
        self.ai_trace_id = None
        if posthog_client:
            self.client = PostHogAsyncOpenAI(
                base_url=base_url, api_key=api_key or "none", timeout=300, posthog_client=posthog_client
            )
        else:
            self.client = AsyncOpenAI(base_url=base_url, api_key=api_key or "none", timeout=300)
        self.provider = provider_for(base_url)
        self.ollama = ":11434" in base_url
        self.history = []
        self.last = 0.0
        self.cancelled = False
        self.done_calls = {}

    def ai_call_options(self, trace_id):
        """Observability context shared by every generation in one user turn."""
        if not self.posthog_client:
            return {}
        options = {
            "posthog_trace_id": trace_id,
            "posthog_properties": {"$ai_session_id": self.ai_session_id},
            "posthog_privacy_mode": False,
        }
        if self.provider:
            options["posthog_provider_override"] = self.provider
        return options

    def capture_tool_span(self, name, args, result, latency, failed=False):
        """Join a dispatched tool run to the model trace without affecting the tool."""
        if not self.posthog_client or not self.ai_trace_id:
            return
        properties = {
            "$ai_trace_id": self.ai_trace_id,
            "$ai_session_id": self.ai_session_id,
            "$ai_span_id": new_trace_id(),
            "$ai_span_name": name,
            "$ai_input_state": json.dumps(args, default=str),
            "$ai_output_state": result,
            "$ai_latency": latency,
        }
        if failed:
            properties["$ai_error"] = "tool_execution_failed"
        try:
            self.posthog_client.capture("$ai_span", properties=properties)
        except Exception as error:
            log.debug("could not capture tool span: %s", type(error).__name__)

    async def roomy(self):
        """The same model with a window that fits Happy; Ollama loads 4096 by default, which cut answers short and dropped turns."""
        import httpx

        native = str(self.client.base_url).rstrip("/").removesuffix("/v1")
        roomy = self.model if self.model.endswith("-happy") else (f"{self.model}-happy" if ":" in self.model else f"{self.model}:latest-happy")
        async with httpx.AsyncClient(base_url=native, timeout=120) as http:
            shown = await http.post("/api/show", json={"model": roomy})
            if shown.status_code == 200 and f"num_ctx {WINDOW}" in " ".join(shown.json().get("parameters", "").split()):
                return roomy
            made = await http.post("/api/create", json={"model": roomy, "from": self.model, "parameters": {"num_ctx": WINDOW}, "stream": False})
            if made.status_code != 200:
                log.warning("could not give %s a %d-token window: %s", self.model, WINDOW, made.text[:200])
                return self.model
        log.info("made %s, %s with a %d-token window", roomy, self.model, WINDOW)
        return roomy

    async def start(self):
        if self.ollama:
            try:
                self.model = await self.roomy()
            except Exception as error:
                log.warning("could not give %s a bigger window: %s", self.model, error)
        self.prepare()
        from happy import history

        for turn in history.since(FORGET_AFTER)[-6:]:
            self.history += [{"role": "user", "content": turn["request"]}, {"role": "assistant", "content": turn["reply"]}]
        self.last = time.time() if self.history else 0.0

    async def reset(self):
        self.history = []

    def heard(self, request, reply):
        if time.time() - self.last > FORGET_AFTER:
            self.history = []
        self.last = time.time()
        self.history += [{"role": "user", "content": stamped(request)}, {"role": "assistant", "content": reply}]

    def prepare(self):
        """The prompt and the tools, built once and again only when one of them changed, to keep the prefix cache."""
        self.tool_list = tools.available(local=True)
        self.schemas = [{"type": "function", "function": {"name": t.name, "description": t.description,
                                                          "parameters": t.schema}} for t in self.tool_list]
        self.system = {"role": "system", "content": system_prompt(self.cfg, local=self.local)}

    async def refresh(self):
        self.prepare()

    async def interrupt(self):
        self.cancelled = True

    def extra(self):
        return {"reasoning_effort": "low"} if "gpt-oss" in self.model else {}

    async def turn(self, text, emit):
        self.ai_trace_id = new_trace_id()
        self.cancelled = False
        tools.asked.set(text)
        tools.seen.set([])
        if time.time() - self.last > FORGET_AFTER:
            self.history = []
        self.last = time.time()
        self.history.append({"role": "user", "content": stamped(text)})
        if len(self.history) > KEEP_TURNS * 6:
            starts = [i for i, m in enumerate(self.history) if m["role"] == "user"]
            self.history = self.history[starts[-KEEP_TURNS]:]
        said = []
        nudged = corrected = False
        self.done_calls = {}
        for _ in range(STEPS):
            if self.cancelled:
                return "".join(said)
            try:
                content, calls, held = await self.step(emit, said)
            except APIError as error:
                message = str(error)
                if not nudged and ("tool" in message.lower() or "parse" in message.lower() or "json" in message.lower()):
                    nudged = True
                    self.history.append({"role": "user", "content": "Your last tool call could not be read. Call the tool again with plain JSON arguments, every value written out in full."})
                    continue
                emit(Problem(f"The model failed: {message[:200]}"))
                return "".join(said)
            if not calls and not (content or "").strip() and not nudged:
                nudged = True
                self.history.append({"role": "user", "content": "You gave no answer. Answer the request, using a tool if it needs one."})
                continue
            message = {"role": "assistant", "content": content or ""}
            if calls:
                message["tool_calls"] = calls
            self.history.append(message)
            if held and not calls and not corrected:
                corrected = True
                log.info("sent back an unbacked claim: %s", held[:200])
                self.history.append({"role": "user", "content": correction(unbacked(held, self.done()))})
                continue
            if held and not calls:
                said.append("That part is not done.")
                emit(Text("That part is not done."))
            if not calls:
                return "".join(said)
            for call in calls:
                await self.run(call, emit)
            if held and not unbacked(held, self.done()):
                said.append(held)
                emit(Text(held))
        emit(Text("I ran out of steps on that one."))
        return "".join(said)

    async def step(self, emit, said):
        stream = await self.client.chat.completions.create(
            model=self.model, messages=[self.system] + self.history, tools=self.schemas, stream=True,
            temperature=0.2, extra_body=self.extra(), **self.ai_call_options(self.ai_trace_id))
        content, calls = [], {}
        # A SENTENCE IS SPOKEN ONLY ONCE IT IS SEEN NOT TO CLAIM SOMETHING NO TOOL DID; FROM A CLAIM ON, THE ROUND IS HELD.
        pending, held = "", ""

        def release(text):
            nonlocal held
            claim = unbacked(text, self.done())
            clean, held = text.split(claim, 1)[0] if claim else text, text[text.index(claim):] if claim else ""
            # A "SENTENCE" OF NOTHING BUT "… ? …" IS NEITHER SHOWN NOR SPOKEN.
            if clean and any(c.isalnum() for c in clean):
                said.append(clean)
                emit(Text(clean))

        babbled = False

        async for chunk in stream:
            if self.cancelled:
                await stream.close()
                break
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                content.append(delta.content)
                if babbling("".join(content)):
                    babbled = True
                    log.warning("the model collapsed into punctuation; cut it off: %r", "".join(content)[-80:])
                    await stream.close()
                    break
                if held:
                    held += delta.content
                    continue
                pending += delta.content
                ends = [m.end() for m in re.finditer(r"[.!?]\s+|\n", pending)]
                if ends:
                    whole, pending = pending[:ends[-1]], pending[ends[-1]:]
                    release(whole)
                    if held:
                        held += pending
                        pending = ""
            for part in delta.tool_calls or []:
                slot = calls.setdefault(part.index or 0, {"id": "", "name": "", "arguments": ""})
                if part.id:
                    slot["id"] = part.id
                if part.function and part.function.name:
                    slot["name"] += part.function.name
                if part.function and part.function.arguments:
                    slot["arguments"] += part.function.arguments
        listed = []
        for index, slot in sorted(calls.items()):
            listed.append({"id": slot["id"] or f"call_{index}_{int(time.time() * 1000)}", "type": "function",
                           "function": {"name": slot["name"], "arguments": slot["arguments"] or "{}"}})
        if babbled:
            pending, held = sense(pending), sense(held)
            content = [sense("".join(content))]
        if not held:
            release(pending)
        return "".join(content), listed, held

    def done(self):
        return {name for name, _ in self.done_calls}

    async def run(self, call, emit):
        name = call["function"]["name"]
        args = repair(call["function"]["arguments"])
        registered = tools.REGISTRY.get(name)
        if registered is not None:
            args = unwrapped(args, registered.params)
        if args is None:
            result = "Error: the arguments were not valid JSON. Call the tool again with plain JSON."
        elif registered is None:
            result = f"Error: there is no tool called {name}. Use one of the tools you were given."
        elif (name, json.dumps(args, sort_keys=True)) in self.done_calls:
            result = (f"You already called {name} with these arguments in this turn, and it said: "
                      f"{self.done_calls[(name, json.dumps(args, sort_keys=True))][:300]} Do not call it again; use that, "
                      f"try something different, or answer.")
        elif registered.refuse(args):
            result = registered.refuse(args)
        else:
            emit(Act(name, args, registered.show(args), registered.say))
            started = time.time()
            try:
                result = await tools.call(name, args)
            except Exception:
                self.capture_tool_span(name, args, "", time.time() - started, failed=True)
                raise
            self.capture_tool_span(name, args, str(result.note if isinstance(result, Image) else result), time.time() - started)
            self.done_calls[(name, json.dumps(args, sort_keys=True))] = str(result.note if isinstance(result, Image) else result)
        if isinstance(result, Image):
            result = result.note or "Took a screenshot, but this model cannot see pictures."
        result = str(result)
        emit(Acted(name, result, not result.startswith("Error")))
        if len(result) > RESULT_LIMIT:
            result = result[:RESULT_LIMIT] + "\n…(cut short)"
        self.history.append({"role": "tool", "tool_call_id": call["id"], "content": result})
