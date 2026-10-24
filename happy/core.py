"""Ties ears, brain, voice and face together, and makes sure the person is never left in silence."""

import asyncio
import logging
import random
import re
import threading
import time

from happy import tools
from happy.brain import Act, Acted, Problem, Text, commands, pick
from happy.connectors import hub, inherit, whatsapp
from happy.voice.speakable import Sentences

log = logging.getLogger("happy")

FIRST_FILLER = 3.0
STILL_EVERY = 8.0
FILLERS = ["One sec.", "Give me a moment.", "Let me see.", "Just a moment."]


class Happy:
    def __init__(self, cfg, face, voice=True, ears=True):
        self.cfg = cfg
        self.face = face
        self.name = cfg.get("name") or "Happy"
        self.loop = None
        self.task = None
        self.brain = None
        self.ready = threading.Event()
        self.quit = None
        self.speaker = None
        self.ears = None
        self.want_voice = voice
        self.want_ears = ears
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
        self.brain = pick.choose(self.cfg, self.extra_servers)
        if self.brain is not None:
            self.loading(f"Waking the brain ({self.brain.name})", 0.92)
            try:
                await self.brain.start()
            except Exception as error:
                log.exception("brain did not start")
                self.face.note(f"{self.brain.name} did not start: {error}")
        self.ready.set()
        self.face.state("idle")
        key = (self.cfg.get("push_to_talk") or "").replace("_", " ")
        if self.brain is None:
            self.face.note("Ready for everyday commands. Pick a brain in Setup for everything else.")
        else:
            self.face.note(f"Ready. Say “{self.name}” or hold {key}.")
        await self.quit.wait()
        if self.brain:
            await self.brain.close()
        await hub.close()

    def loading(self, text, fraction):
        self.waiting = text
        self.face.progress(text, fraction)

    def wake_up(self):
        """Loads the slow parts, saying which one it is waiting on: WhatsApp, then voice and ears together."""
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
        for name, (server, source) in inherit.everything().items():
            hub.add(name, server, source)
            if source != "Claude Code":
                self.extra_servers[name] = server
        parts = {}
        if self.want_voice:
            from happy.voice.speaker import Speaker

            self.speaker = Speaker(self.cfg.get("voice") or "alba", on_level=self.face.mouth, on_speaking=self.speaking)
            parts["the voice"] = self.speaker.start
        if self.want_ears:
            from happy.ears.listen import Ears

            self.ears = Ears(self.name, wake=self.cfg.get("wake_word"), device=self.cfg.get("input.device") or "",
                             on_heard=self.heard, on_state=self.ear_state, on_level=self.face.ear)
            parts["the ears"] = self.ears.start
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
        if self.ears:
            self.ears.stop()

    def heard(self, text, how):
        """Called from the ears thread with what was said."""
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
        if self.ears:
            self.ears.key_down()

    def key_up(self):
        if self.ears:
            self.ears.key_up()

    def key_cancel(self):
        """The key was part of a shortcut, not a request to talk."""
        if self.ears:
            self.ears.cancel()
        if not self.busy():
            self.face.state("idle")

    def ear_state(self, state):
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
        if self.ears:
            self.ears.mute_wake(talking)
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
            if self.brain:
                asyncio.ensure_future(self.brain.interrupt())

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
        found = commands.match(text)
        if found and found[0] == "stop":
            if self.speaker:
                self.speaker.stop()
            self.face.reply("")
            self.face.state("idle")
            self.face.done()
            return
        self.face.state("thinking")
        started = time.monotonic()
        try:
            if found:
                name, args = found
                self.face.step(tools.REGISTRY[name].show(args))
                result = await commands.run(name, args)
                self.face.step_done(not result.startswith("Error"))
                self.face.reply(result)
                self.say(self.plain(result))
                log.info("fast path %s %s -> %s (%.0f ms)", name, args, result, (time.monotonic() - started) * 1000)
            elif self.brain is None:
                self.say("I can't think without a brain. Run happy setup.")
            else:
                await self.think(text, started)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            log.exception("turn failed")
            self.face.reply(f"Something went wrong: {error}")
            self.say(f"Something went wrong. {self.plain(str(error))}")
        finally:
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
                log.info("tool %s %s", event.tool, event.args)
            elif isinstance(event, Acted):
                self.last_result = event
                self.face.step_done(event.ok)
                log.info("tool %s %s: %s", event.tool, "ok" if event.ok else "failed", event.result[:300].replace("\n", " | "))
            elif isinstance(event, Problem):
                self.face.reply(event.message)
                self.answered = True
                self.say(event.message)

        guard = asyncio.create_task(self.keep_talking(started))
        try:
            final = await self.brain.turn(text, emit)
        finally:
            guard.cancel()
        for sentence in sentences.rest():
            self.answered = True
            self.say(sentence)
        if not self.answered:
            self.say(self.fallback())
        log.info("answer: %s (%.1fs)", (final or "").strip()[:300], time.monotonic() - started)
        if (final or "").strip().endswith("?") and self.ears:
            await asyncio.to_thread(self.speaker.wait if self.speaker else (lambda: None))
            self.ears.listen_now()

    def fallback(self):
        """Something to say when the brain finished without a word."""
        result = self.last_result
        if result is None:
            return "Done."
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
