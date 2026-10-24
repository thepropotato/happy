"""A brain for any OpenAI-shaped endpoint: Ollama, LM Studio, OpenAI, OpenRouter, Groq, Gemini and the rest."""

import json
import logging
import re
import time

from openai import APIError, AsyncOpenAI

from happy import tools
from happy.agent import Act, Acted, Backend, Problem, Text
from happy.agent.prompt import stamped, system_prompt
from happy.tools import Image

log = logging.getLogger("happy.agent")

STEPS = 10
FORGET_AFTER = 15 * 60
KEEP_TURNS = 12
RESULT_LIMIT = 4000


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


class OpenAICompatible(Backend):
    def __init__(self, cfg, base_url, model, api_key="none", local=True):
        self.cfg = cfg
        self.name = model
        self.model = model
        self.local = local
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key or "none", timeout=300)
        self.ollama = ":11434" in base_url
        self.history = []
        self.last = 0.0
        self.cancelled = False

    async def start(self):
        self.tool_list = tools.available(local=True)
        self.schemas = [{"type": "function", "function": {"name": t.name, "description": t.description,
                                                          "parameters": t.schema}} for t in self.tool_list]
        self.system = {"role": "system", "content": system_prompt(self.cfg, local=self.local)}
        from happy import history

        for turn in history.since(FORGET_AFTER)[-6:]:
            self.history += [{"role": "user", "content": turn["request"]}, {"role": "assistant", "content": turn["reply"]}]
        self.last = time.time() if self.history else 0.0

    async def reset(self):
        self.history = []

    async def interrupt(self):
        self.cancelled = True

    def extra(self):
        return {"reasoning_effort": "low"} if "gpt-oss" in self.model else {}

    async def turn(self, text, emit):
        self.cancelled = False
        if time.time() - self.last > FORGET_AFTER:
            self.history = []
        self.last = time.time()
        self.history.append({"role": "user", "content": stamped(text)})
        if len(self.history) > KEEP_TURNS * 6:
            starts = [i for i, m in enumerate(self.history) if m["role"] == "user"]
            self.history = self.history[starts[-KEEP_TURNS]:]
        said = []
        nudged = False
        for _ in range(STEPS):
            if self.cancelled:
                return "".join(said)
            try:
                content, calls = await self.step(emit, said)
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
            if not calls:
                return "".join(said)
            for call in calls:
                await self.run(call, emit)
        emit(Text("I ran out of steps on that one."))
        return "".join(said)

    async def step(self, emit, said):
        stream = await self.client.chat.completions.create(
            model=self.model, messages=[self.system] + self.history, tools=self.schemas, stream=True,
            temperature=0.2, extra_body=self.extra())
        content, calls = [], {}
        async for chunk in stream:
            if self.cancelled:
                await stream.close()
                break
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                content.append(delta.content)
                said.append(delta.content)
                emit(Text(delta.content))
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
        return "".join(content), listed

    async def run(self, call, emit):
        name = call["function"]["name"]
        args = repair(call["function"]["arguments"])
        registered = tools.REGISTRY.get(name)
        if args is None:
            result = "Error: the arguments were not valid JSON. Call the tool again with plain JSON."
        elif registered is None:
            result = f"Error: there is no tool called {name}. Use one of the tools you were given."
        else:
            emit(Act(name, args, registered.show(args), registered.say))
            result = await tools.call(name, args)
        if isinstance(result, Image):
            result = result.note or "Took a screenshot, but this model cannot see pictures."
        result = str(result)
        emit(Acted(name, result, not result.startswith("Error")))
        if len(result) > RESULT_LIMIT:
            result = result[:RESULT_LIMIT] + "\n…(cut short)"
        self.history.append({"role": "tool", "tool_call_id": call["id"], "content": result})
