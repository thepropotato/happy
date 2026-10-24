"""One running Happy: listens, decides, acts and answers, and never leaves the person in silence."""

import asyncio
import logging
import random
import re
import threading
import time

from happy import history, tools
from happy.agent import Act, Acted, Problem, Text, choose, quick
from happy.integrations import discovered, whatsapp
from happy.integrations.mcp import hub
from happy.speech.spoken_text import Sentences

log = logging.getLogger("happy")

FIRST_FILLER = 3.0
STILL_EVERY = 8.0
FILLERS = ["One sec.", "Give me a moment.", "Let me see.", "Just a moment."]


class Happy:
    def __init__(self, cfg, face, voice=True, listening=True):
        self.cfg = cfg
        self.face = face
        self.name = cfg.get("name") or "Happy"
        self.loop = None
        self.task = None
        self.backend = None
        self.ready = threading.Event()
        self.quit = None
        self.speaker = None
        self.listener = None
        self.want_voice = voice
        self.want_listening = listening
        self.waiting = "Getting ready"
        self.spoken_at = 0.0
        self.answered = False
        self.activity = ""
        self.last_result = None

    def run(self):
        asyncio.run(self.main())

    async def main(self):
        self.loop = asyncio.get_running_loop()
        self.quit = asyncio.Event()
        self.waiting = "Getting ready"
        self.face.progress(self.waiting, 0.02)
        await asyncio.to_thread(self.wake_up)
        await self.connect_services()
        self.backend = choose.backend(self.cfg, self.extra_servers)
        from happy.tools import status

        status.model_name = self.backend.name if self.backend else ""
        if self.backend is not None:
            self.loading(f"Starting {self.backend.name}", 0.92)
            try:
                await self.backend.start()
            except Exception as error:
                log.exception("model did not start")
                self.face.note(f"{self.backend.name} did not start: {error}")
        self.ready.set()
        self.face.state("idle")
        key = (self.cfg.get("push_to_talk") or "").replace("_", " ")
        if self.backend is None:
            self.face.note("Ready for everyday commands. Pick a model in Setup for everything else.")
        else:
            self.face.note(f"Ready. Say “{self.name}” or hold {key}.")
        await self.quit.wait()
        if self.backend:
            await self.backend.close()
        await hub.close()

    async def connect_services(self):
        """Starts the person's MCP servers together, so local models get their tools from the first request."""
        servers = hub.inherited()
        if not servers or self.cfg.get("brain.kind") == "claude":
            return
        self.loading(f"Connecting {len(servers)} service{'s' if len(servers) != 1 else ''}", 0.88)
        await asyncio.gather(*(server.connect(timeout=8) for server in servers), return_exceptions=True)
        from happy.tools import other_mcps

        added = other_mcps.register_direct()
        log.info("services: %s", ", ".join(f"{s.name} {'ok' if s.client else s.error}" for s in servers))
        log.info("%d service tools handed to the model directly", added)

    def loading(self, text, fraction):
        self.waiting = text
        self.face.progress(text, fraction)

    def wake_up(self):
        """Loads the slow parts, saying which one it is waiting on: WhatsApp, then the voice and microphone together."""
        tools.load()
        self.extra_servers = {}
        self.loading("Starting WhatsApp", 0.05)
        try:
            whatsapp.adopt(self.cfg)
            whatsapp.install(lambda text: self.loading("Installing WhatsApp (once)", 0.08))
        except Exception:
            log.exception("WhatsApp could not be installed")
        spec = whatsapp.spec()
        if spec:
            if whatsapp.start_bridge():
                hub.add("whatsapp", spec, "happy")
                self.extra_servers["whatsapp"] = spec
            else:
                log.warning("the WhatsApp bridge did not start; see ~/.happy/whatsapp-bridge.log")
        for name, (server, source) in discovered.everything().items():
            hub.add(name, server, source)
            if source != "Claude Code":
                self.extra_servers[name] = server
        parts = {}
        if self.want_voice:
            from happy.speech.speaker import Speaker

            self.speaker = Speaker(self.cfg.get("voice") or "alba", on_level=self.face.mouth, on_speaking=self.speaking)
            parts["the voice"] = self.speaker.start
        if self.want_listening:
            from happy.speech.listener import Listener

            self.listener = Listener(self.name, wake=self.cfg.get("wake_word"), device=self.cfg.get("input.device") or "",
                             on_heard=self.heard, on_state=self.heard_state, on_level=self.face.ear)
            parts["the microphone"] = self.listener.start
        pending = set(parts)
        lock = threading.Lock()

        def load(name, start):
            try:
                start()
            except Exception:
                log.exception("%s did not load", name)
            with lock:
                pending.discard(name)
                if pending:
                    self.loading(f"Loading {' and '.join(sorted(pending))}", 0.3 + 0.55 * (1 - len(pending) / len(parts)))

        if parts:
            self.loading(f"Loading {' and '.join(sorted(parts))}", 0.3)
        workers = [threading.Thread(target=load, args=item) for item in parts.items()]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()

    def stop(self):
        if self.loop and self.quit:
            self.loop.call_soon_threadsafe(self.quit.set)
        if self.listener:
            self.listener.stop()

    def heard(self, text, how):
        """Called from the listening thread with what was said."""
        if self.loop:
            self.loop.call_soon_threadsafe(self.begin, text, how)

    def typed(self, text):
        if self.loop:
            self.loop.call_soon_threadsafe(self.begin, text, "typed")

    def key_down(self):
        """Push-to-talk pressed: stop talking and listen, from whatever thread the key arrived on."""
        if not self.ready.is_set():
            self.face.progress(f"Not ready yet: {self.waiting.lower()}")
            return
        if self.speaker:
            self.speaker.stop()
        if self.loop:
            self.loop.call_soon_threadsafe(self.interrupt)
        if self.listener:
            self.listener.key_down()

    def key_up(self):
        if self.listener:
            self.listener.key_up()

    def key_cancel(self):
        """The key was part of a shortcut, not a request to talk."""
        if self.listener:
            self.listener.cancel()
        if not self.busy():
            self.face.state("idle")

    def heard_state(self, state):
        if state == "listening":
            if self.speaker:
                self.speaker.blip()
            self.face.state("listening")
        elif state == "transcribing":
            self.face.state("thinking")
        elif state in ("idle", "missed"):
            if not self.busy():
                self.face.state("idle")
        elif state == "silent-mic":
            self.face.note("The microphone is sending pure silence. Check the input device in Sound settings.")

    def speaking(self, talking):
        if self.listener:
            self.listener.mute_wake(talking)
        if talking:
            self.face.state("speaking")
        elif self.busy():
            self.face.state("working" if self.activity else "thinking")
        else:
            self.face.state("idle")

    def busy(self):
        return self.task is not None and not self.task.done()

    def interrupt(self):
        if self.busy():
            self.task.cancel()
            if self.backend:
                asyncio.ensure_future(self.backend.interrupt())

    def begin(self, text, how):
        self.interrupt()
        previous = self.task
        self.task = asyncio.create_task(self.turn(text, how, previous))

    def say(self, text):
        if not text or not self.speaker:
            if text:
                log.info("would say: %s", text)
            return
        if self.speaker.say(text):
            self.spoken_at = time.monotonic()

    async def turn(self, text, how, previous):
        if previous and not previous.done():
            try:
                await asyncio.wait_for(asyncio.shield(previous), 2)
            except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                pass
        log.info("request (%s): %s", how, text)
        self.face.user(text)
        found = quick.match(text)
        if found and found[0] == "stop":
            if self.speaker:
                self.speaker.stop()
            self.face.reply("")
            self.face.state("idle")
            self.face.done()
            return
        self.face.state("thinking")
        started = time.monotonic()
        self.steps, self.reply, failed = [], "", False
        record = await asyncio.to_thread(history.begin, text, how, "quick" if found else self.backend.name if self.backend else "")
        try:
            if found:
                name, args = found
                label = tools.REGISTRY[name].show(args)
                self.face.step(label)
                result = await quick.run(name, args)
                self.steps.append({"tool": name, "label": label, "args": args, "result": result[:500], "ok": not result.startswith("Error")})
                self.face.step_done(not result.startswith("Error"))
                self.face.reply(result)
                self.reply = result
                self.say(self.plain(result))
                log.info("fast path %s %s -> %s (%.0f ms)", name, args, result, (time.monotonic() - started) * 1000)
            elif self.backend is None:
                self.reply = "I don't have a model to think with yet. Pick one in Setup."
                self.say(self.reply)
            else:
                await self.think(text, started)
        except asyncio.CancelledError:
            failed = True
            self.reply = self.reply or "(interrupted)"
            raise
        except Exception as error:
            failed = True
            log.exception("turn failed")
            self.reply = f"Something went wrong: {error}"
            self.face.reply(self.reply)
            self.say(f"Something went wrong. {self.plain(str(error))}")
        finally:
            await asyncio.to_thread(history.finish, record, self.reply, self.steps, time.monotonic() - started, failed)
            await self.settle()

    async def think(self, text, started):
        sentences = Sentences()
        self.answered = False
        self.activity = ""
        self.last_result = None
        self.spoken_at = 0.0
        self.face.reply("")

        def emit(event):
            if isinstance(event, Text):
                self.face.reply_add(event.delta)
                for sentence in sentences.add(event.delta):
                    self.answered = True
                    self.say(sentence)
            elif isinstance(event, Act):
                for sentence in sentences.rest():
                    self.answered = True
                    self.say(sentence)
                self.activity = event.label
                self.face.step(event.label)
                self.face.state("working")
                if event.say and not self.answered and time.monotonic() - self.spoken_at > 4:
                    self.say(event.say)
                self.steps.append({"tool": event.tool, "label": event.label, "args": event.args})
                log.info("tool %s %s", event.tool, event.args)
            elif isinstance(event, Acted):
                self.last_result = event
                for step in reversed(self.steps):
                    if step["tool"] == event.tool and "ok" not in step:
                        step.update(result=event.result[:500], ok=event.ok)
                        break
                self.face.step_done(event.ok)
                log.info("tool %s %s: %s", event.tool, "ok" if event.ok else "failed", event.result[:300].replace("\n", " | "))
            elif isinstance(event, Problem):
                self.face.reply(event.message)
                self.answered = True
                self.say(event.message)

        guard = asyncio.create_task(self.keep_talking(started))
        try:
            final = await self.backend.turn(text, emit)
        finally:
            guard.cancel()
        for sentence in sentences.rest():
            self.answered = True
            self.say(sentence)
        self.reply = (final or "").strip()
        if not self.answered:
            self.reply = self.fallback()
            self.face.reply(self.reply)
            self.say(self.reply)
        log.info("answer: %s (%.1fs)", (final or "").strip()[:300], time.monotonic() - started)
        if (final or "").strip().endswith("?") and self.listener:
            await asyncio.to_thread(self.speaker.wait if self.speaker else (lambda: None))
            self.listener.listen_now()

    def fallback(self):
        """Something to say when the model finished without a word."""
        result = self.last_result
        if result is None:
            return "I didn't come up with an answer for that. Could you ask it another way?"
        first = re.split(r"(?<=[.!?])\s|\n", result.result.strip(), maxsplit=1)[0]
        if not result.ok:
            return "That didn't work. " + self.plain(first.removeprefix("Error: "))
        return first if 0 < len(first) <= 140 else "Done."

    async def keep_talking(self, started):
        """Fills silence while a turn runs: a quick filler early, then a word on what it is doing."""
        filled = False
        while True:
            await asyncio.sleep(0.4)
            if self.speaker and not self.speaker.idle():
                continue
            now = time.monotonic()
            quiet = now - max(self.spoken_at, started)
            if not filled and not self.answered and self.spoken_at == 0 and quiet > FIRST_FILLER:
                filled = True
                self.say(random.choice(FILLERS))
            elif quiet > STILL_EVERY:
                doing = self.activity.split(":")[0].strip().lower() if self.activity else ""
                self.say(f"Still {doing.removeprefix('still ')}." if doing.endswith("ing") else "Still working on it.")

    async def settle(self):
        if self.speaker:
            await asyncio.to_thread(self.speaker.wait)
        if self.task is asyncio.current_task() or not self.busy():
            self.face.state("idle")
            self.face.done()

    @staticmethod
    def plain(text):
        return re.sub(r"\s+", " ", text or "").strip()[:400]
