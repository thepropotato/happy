"""One running Happy: listens, decides, acts and answers, and never leaves the person in silence."""

import asyncio
import difflib
import logging
import re
import threading
import time

from happy import history, learned, reminders, routines, timing, tools
from happy.agent import Act, Acted, Problem, Text, choose, quick
from happy.integrations import discovered, whatsapp
from happy.integrations.mcp import hub
from happy.speech.spoken_text import Sentences

log = logging.getLogger("happy")

FOLLOW_SECONDS = 4.0
# A SPOKEN REQUEST THIS SOON AFTER THE LAST ONE THAT SOUNDS LIKE A FIX OF IT REPLACES IT.
CORRECTION_SECONDS = 8.0
# THE CLOCK IS READ, NOT SLEPT ON: A TIMER SET FOR THREE HOURS DOES NOT SURVIVE THE LID GOING DOWN.
TICK = 20
CHAT_EVERY = 3
PHONE = ("\n\n(Sent from their phone in your WhatsApp chat: they are away from the computer and read your answer there. "
         "Give the answer itself in plain text, and open things on screen only when they ask to. "
         "'Here' and 'me' mean this chat: to send them a file, call whatsapp_send with to 'me' and the file's full path.)")
CORRECTION_CUE = re.compile(r"^(?:no|nope|nah|sorry|wait|actually|i mean|i meant|not that|not him|not her|correction|rather|instead|oops)\b", re.I)
FACTUAL = {"set_brightness", "set_volume", "set_keyboard_light", "media", "set_speech_speed"}
STILL_EVERY = 8.0
# "WAIT" OVER HAPPY HOLDS HIM THIS LONG BEFORE HE GIVES UP ON THE REST.
HOLD_SECONDS = 15.0
# WHAT A PERSON TALKED OVER CAN BE PICKED UP AGAIN FOR THIS LONG.
LEFTOVER_SECONDS = 120.0
LEFTOVER_LIMIT = 800
PICK_UP = re.compile(r"(?:ok(?:ay)?,? |yeah,? |so,? )?(?:go on|continue|carry on|keep going|go ahead|what were you saying|"
                     r"where were you|you were saying|finish (?:that|what you were saying))[.!?]*", re.I)


def brain(cfg):
    """What decides which model runs, so a change to any of it swaps the model."""
    from happy.config import secrets

    return cfg.get("brain.kind"), cfg.get("brain.model"), cfg.get("brain.base_url"), secrets().get("api_key")


class Happy:
    def __init__(self, cfg, face, voice=True, listening=True):
        self.cfg = cfg
        self.face = face
        self.name = cfg.get("name") or "Happy"
        self.loop = None
        self.task = None
        self.last_spoken = ("", 0.0)
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
        self.saying = ""
        self.last_result = None
        self.quiet = False
        self.chat = None
        self.prompted = ""
        self.narrated = set()
        self.brain = None
        self.extra_servers = {}
        self.record = None
        self.said_for = None
        self.streamed = ""
        self.leftover = ([], 0.0)
        self.hold_timer = None

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
        self.brain = brain(self.cfg)
        from happy.tools import status

        status.model_name = self.backend.name if self.backend else ""
        if self.backend is not None:
            self.loading(f"Starting {self.backend.name}", 0.92)
            try:
                await self.backend.start()
            except Exception as error:
                log.exception("model did not start")
                self.face.trouble(f"{self.backend.name} did not start: {error}")
            from happy.agent.prompt import system_prompt

            self.prompted = system_prompt(self.cfg)
        self.ready.set()
        self.face.state("idle")
        threading.Thread(target=self.keep_time, name="reminders", daemon=True).start()
        self.login_item()
        if "whatsapp" in self.extra_servers and self.cfg.get("whatsapp.own_chat", True) is not False:
            threading.Thread(target=self.keep_chat, name="own chat", daemon=True).start()
        key = (self.cfg.get("push_to_talk") or "").replace("_", " ")
        if self.backend is None:
            self.face.ready("Ready for everyday commands. Pick a model in Settings for everything else.")
        else:
            self.face.ready(f"Ready. Say “{self.name}” or hold {key}.")
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
        from happy.tools import controls

        controls.on_speed = self.speed_changed
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
            if server.get("codex_only"):
                continue
            hub.add(name, server, source)
            if source != "Claude Code":
                self.extra_servers[name] = server
        parts = {}
        if self.want_voice:
            from happy.speech.speaker import Speaker

            self.speaker = Speaker(self.cfg.get("voice") or "alba", on_level=self.face.mouth, on_speaking=self.speaking,
                                   refresh_devices=self.reload_sound, device=self.cfg.get("output.device") or "",
                                   speed=self.cfg.get("speech_speed", 1.0))
            parts["the voice"] = self.speaker.start
        if self.want_listening:
            from happy.speech.listener import Listener

            self.listener = Listener(self.name, wake=self.cfg.get("wake_word"), device=self.cfg.get("input.device") or "",
                             on_heard=self.heard, on_state=self.heard_state, on_level=self.face.ear,
                             echo_cancel=self.cfg.get("input.echo_cancel", True) is not False,
                             on_barge=self.barged, on_cut_in=self.heard_over, echo=self.is_echo,
                             refresh_devices=self.reload_sound)
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

    def reload_sound(self):
        """Reloads the sound devices for a changed output, and reopens the microphone, which shares the same list."""
        import sounddevice as sd

        if self.listener:
            self.listener.close_mic()
        sd._terminate()
        sd._initialize()
        if self.listener:
            self.listener.reopen()

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
        if self.loop:
            self.loop.call_soon_threadsafe(self.cut_off)
        elif self.speaker:
            self.speaker.stop()
        if self.listener:
            self.listener.key_down()

    def key_up(self):
        if self.listener:
            self.listener.key_up()

    def retune(self):
        """Takes up changed settings while running, from any thread: nothing in the settings waits on a restart."""
        from happy.config import Config

        self.cfg = Config()
        self.name = self.cfg.get("name") or "Happy"
        if self.backend:
            self.backend.cfg = self.cfg
        if self.listener:
            self.listener.name = self.name
            self.listener.wake_enabled = bool(self.cfg.get("wake_word"))
            device = self.cfg.get("input.device") or ""
            if device != self.listener.device:
                self.listener.device = device
                # A MIC PLUGGED IN SINCE START IS NOT IN THE SOUND LIBRARY'S LIST UNTIL IT IS READ AGAIN.
                threading.Thread(target=self.reload_sound, name="microphone", daemon=True).start()
        if self.speaker:
            self.speaker.device = self.cfg.get("output.device") or ""
            self.speaker.speed = self.cfg.get("speech_speed", 1.0)
        voice = self.cfg.get("voice") or "alba"
        if self.speaker and self.ready.is_set() and voice != self.speaker.voice:
            threading.Thread(target=self.speaker.use_voice, args=(voice,), name="voice change", daemon=True).start()
        if self.loop and self.ready.is_set() and brain(self.cfg) != self.brain:
            asyncio.run_coroutine_threadsafe(self.rebrain(), self.loop)

    def speed_changed(self, value):
        """Puts a saved speed to work without interrupting the reply."""
        self.cfg.set("speech_speed", value)
        if self.speaker:
            self.speaker.speed = value
        self.face.speed(value)

    def speed_command(self, text):
        found = quick.speed(quick.clean(text))
        if not found:
            return False
        from happy.tools.controls import set_speech_speed

        try:
            result = set_speech_speed(**found[1])
        except (OSError, ValueError) as error:
            log.exception("could not change speaking speed")
            self.face.trouble(f"Could not change speaking speed: {error}")
            self.carry_on()
            return True
        self.face.note(result)
        self.say(result)
        self.carry_on()
        return True

    async def rebrain(self):
        """Swaps in the model the settings now name, once the turn under way has finished."""
        if self.busy():
            try:
                await asyncio.shield(self.task)
            except BaseException:
                pass
        self.brain = brain(self.cfg)
        old, self.backend = self.backend, choose.backend(self.cfg, self.extra_servers)
        if self.backend is not None:
            try:
                await self.backend.start()
            except Exception as error:
                log.exception("model did not start")
                self.face.trouble(f"{self.backend.name} did not start: {error}")
        from happy.tools import status

        status.model_name = self.backend.name if self.backend else ""
        log.info("now thinking with %s", status.model_name or "nothing")
        if old:
            await old.close()

    def services_changed(self):
        """Connects a service added in the settings and drops a removed one, then hands the model the new tool list."""
        if self.loop:
            asyncio.run_coroutine_threadsafe(self.reconnect(), self.loop)

    async def reconnect(self):
        from happy.tools import REGISTRY, other_mcps

        found = discovered.everything()
        for name in [n for n, server in hub.servers.items() if server.source != "happy" and n not in found]:
            await hub.servers.pop(name).close()
            self.extra_servers.pop(name, None)
            for gone in [t for t in REGISTRY if t.startswith(other_mcps.tool_name(name, ""))]:
                del REGISTRY[gone]
        for name, (server, source) in found.items():
            if name not in hub.servers:
                hub.add(name, server, source)
                if source != "Claude Code":
                    self.extra_servers[name] = server
        if self.cfg.get("brain.kind") != "claude":
            await asyncio.gather(*(server.connect(timeout=8) for server in hub.inherited()), return_exceptions=True)
            other_mcps.register_direct()
        if self.busy():
            try:
                await asyncio.shield(self.task)
            except BaseException:
                pass
        if self.backend:
            await self.backend.refresh()

    def login_item(self):
        """Keeps Happy starting at login when the setting says so, which is what lets a reminder survive a restart."""
        import sys

        from happy import paths
        from happy.system import native

        try:
            native.start_at_login(self.cfg.get("start_at_login") is not False,
                                  [sys.executable, "-m", "happy", "run", "--quiet"], paths.REPO)
        except Exception:
            log.exception("could not set Happy to start at login")

    def keep_chat(self):
        """Watches Happy's own WhatsApp group for requests the person writes from their phone."""
        from happy.integrations.own_chat import Chat

        self.chat = Chat(self.cfg)
        while True:
            try:
                for text in self.chat.requests():
                    log.info("from the phone: %s", text)
                    self.loop.call_soon_threadsafe(self.from_phone, text)
            except Exception as error:
                log.debug("own chat: %s", error)
            time.sleep(CHAT_EVERY)

    def from_phone(self, text):
        # A REQUEST FROM THE PHONE WAITS ITS TURN RATHER THAN CUTTING OFF SOMEONE TALKING AT THE COMPUTER.
        if self.busy():
            self.loop.call_later(2, self.from_phone, text)
            return
        self.begin(text + PHONE, "whatsapp", shown=text)

    def keep_time(self):
        """Fires reminders as they come due; the ones missed while Happy was off are said together, once."""
        while True:
            try:
                fired = reminders.due()
            except Exception:
                log.exception("reminders could not be read")
                fired = []
            if fired and self.loop:
                self.loop.call_soon_threadsafe(self.remind, fired)
            time.sleep(TICK)

    def remind(self, fired):
        missed = [r for r in fired if r["missed"]]
        now = [r for r in fired if not r["missed"]]
        lines = [f"Reminder: {r['what']}." for r in now if not r["routine"]]
        if missed:
            said = "; ".join(f"{r['what']} at {timing.spoken(r['at'])}" for r in missed)
            lines.append(f"While I was off, you had {'a reminder' if len(missed) == 1 else f'{len(missed)} reminders'}: {said}.")
        if lines:
            text = " ".join(lines)
            log.info("reminder: %s", text)
            self.face.announce(text)
            if self.speaker:
                # SPOKEN EVEN WHILE A PHONE REQUEST IS QUIETLY RUNNING: THE REMINDER IS FOR WHOEVER IS IN THE ROOM.
                self.speaker.blip()
                self.speaker.say(text)
            history.finish(history.begin("", "reminder", "reminder"), text, [], 0.0)
        for row in now:
            if row["routine"]:
                self.run_routine(row["routine"])

    def run_routine(self, name):
        """Runs a routine a reminder set off, waiting for whatever Happy is in the middle of to finish first."""
        routine = routines.named(name)
        if not routine:
            return
        if self.busy():
            self.loop.call_later(5, self.run_routine, name)
            return
        self.begin(routines.request(routine), "routine", shown=f"Running your {routine['name']} routine")

    def barged(self):
        """The person started talking over Happy: he pauses, and what they said decides what happens next."""
        if self.speaker:
            self.speaker.pause()
        self.face.state("listening")

    def heard_over(self, text, by_name):
        """Called from the listening thread with what was said over Happy."""
        if self.loop:
            self.loop.call_soon_threadsafe(self.cut_in, text, by_name)

    def cut_in(self, text, by_name=False):
        from happy.speech.listener import meaning

        wants, command = meaning(text, self.name, by_name)
        log.info("said over Happy (%s): %r", wants, text)
        if self.speed_command(command):
            return
        if wants == "carry on":
            self.carry_on()
        elif wants == "wait":
            if self.speaker:
                self.speaker.pause()
            if self.listener:
                self.listener.holding = True
            if self.hold_timer:
                self.hold_timer.cancel()
            self.hold_timer = self.loop.call_later(HOLD_SECONDS, self.gave_up)
            self.face.state("listening")
        elif wants == "stop":
            self.cut_off()
            if not self.busy():
                self.face.state("idle")
        else:
            self.cut_off()
            self.begin(command, "barge")

    def carry_on(self):
        self.release()
        if self.speaker and self.speaker.paused():
            self.speaker.resume()
        talking = self.speaker and self.speaker.speaking
        self.face.state("speaking" if talking else "working" if self.busy() and self.activity else "thinking" if self.busy() else "idle")

    def gave_up(self):
        log.info("nothing more after %.0fs of holding; stopping", HOLD_SECONDS)
        self.cut_off()
        if not self.busy():
            self.face.state("idle")

    def release(self):
        if self.hold_timer:
            self.hold_timer.cancel()
            self.hold_timer = None
        if self.listener:
            self.listener.holding = False

    def cut_off(self, cancel=True):
        """Stops Happy mid-answer, keeping what was not heard so it can be picked up again, and drops the turn."""
        self.release()
        unheard = self.speaker.stop() if self.speaker else []
        if unheard:
            self.leftover = (unheard, time.monotonic())
            log.info("cut off before: %s", " ".join(unheard)[:300])
            self.face.unsaid(unheard[0])
            if self.said_for:
                self.loop.run_in_executor(None, history.unsaid, self.said_for, unheard[0])
        if cancel:
            self.interrupt()

    def picked_up(self, text):
        """The sentences talked over, when this asks to hear them after all."""
        rest, at = self.leftover
        if not rest or time.monotonic() - at > LEFTOVER_SECONDS or not PICK_UP.fullmatch(text.strip()):
            return []
        self.leftover = ([], 0.0)
        return rest

    def leftover_note(self):
        """For the model: the part of its last answer that was talked over, once."""
        rest, at = self.leftover
        self.leftover = ([], 0.0)
        if not rest or time.monotonic() - at > LEFTOVER_SECONDS:
            return ""
        unheard = " ".join(rest)
        if len(unheard) > LEFTOVER_LIMIT:
            unheard = unheard[:LEFTOVER_LIMIT].rsplit(" ", 1)[0] + "…"
        return (f'\n\n(They talked over your last answer and missed this part: "{unheard}" '
                "If this request is about that answer or a word in it, answer it, then finish the missed part in your own words. "
                "If it is about anything else, answer only it and do not mention the missed part.)")

    def is_echo(self, text):
        """Whether what was heard is Happy's own last words coming back through the microphone."""
        if not self.speaker:
            return False
        heard = set(re.findall(r"[a-z']+", text.lower()))
        said = set(re.findall(r"[a-z']+", " ".join(self.speaker.recent).lower()))
        return bool(heard) and len(heard & said) / len(heard) >= 0.6

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
            self.face.state("hearing")
        elif state in ("idle", "missed"):
            if not self.busy():
                self.face.state("idle")
        elif state == "following":
            self.face.state("listening")
        elif state == "silent-mic":
            self.face.trouble("The microphone is sending pure silence. Check the input device in Sound settings.")

    def speaking(self, talking):
        if self.listener:
            self.listener.mute_wake(talking)
        if self.busy() and not self.answered:
            # A WORD ON WHAT IT IS DOING IS PART OF THE WORK, SO THE FACE STAYS "ON IT" THROUGH IT.
            return
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

    def begin(self, text, how, shown=None):
        if self.speaker and self.speaker.speaking and self.speed_command(text):
            return
        shown, text, how = shown or text, *self.corrected(text, how)
        self.interrupt()
        previous = self.task
        self.task = asyncio.create_task(self.turn(text, how, previous, shown))

    def corrected(self, text, how):
        """A spoken fix of what was just said becomes one request carrying both, so the model acts on the fix."""
        if how in ("typed", "routine"):
            return text, how
        earlier, at = self.last_spoken
        self.last_spoken = (text, time.monotonic())
        if not earlier or time.monotonic() - at > CORRECTION_SECONDS or not self.correcting(earlier, text):
            return text, how
        self.last_spoken = (f"{earlier} {text}", time.monotonic())
        log.info("correction of %r: %r", earlier, text)
        # WHAT WAS CORRECTED WAS NOT WHAT THEY WANTED, SO ITS STEPS ARE NOT KEPT FOR NEXT TIME.
        if learned.forget(earlier):
            log.info("forgot the learned steps for %r", earlier)
        return (f'{text}\n\n(This corrects what they said just before: "{earlier}". '
                f"Act only on the corrected request; the earlier one is replaced.)"), "correction"

    @staticmethod
    def correcting(earlier, text):
        if CORRECTION_CUE.match(text.strip()):
            return True
        # A REPEATED COMMAND LIKE "VOLUME UP" IS MEANT TWICE; ONLY A REPEAT THAT WENT TO THE MODEL IS A RETRY.
        if quick.match(text):
            return False
        said, again = re.findall(r"[\w']+", earlier.lower()), re.findall(r"[\w']+", text.lower())
        return len(again) >= 3 and difflib.SequenceMatcher(None, said, again).ratio() >= 0.6

    def say(self, text):
        if self.quiet:
            return
        if not text or not self.speaker:
            if text:
                log.info("would say: %s", text)
            return
        if self.speaker.say(text):
            self.spoken_at = time.monotonic()
            self.said_for = self.record

    async def turn(self, text, how, previous, shown=None):
        shown = shown or text
        if previous and not previous.done():
            try:
                await asyncio.wait_for(asyncio.shield(previous), 2)
            except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                pass
        log.info("request (%s): %s", how, shown)
        self.record = None
        # WHOEVER ASKED FROM THE PHONE IS NOT IN THE ROOM, SO THE ANSWER IS WRITTEN BACK, NOT SPOKEN.
        self.quiet = how == "whatsapp"
        self.face.user(shown)
        # WHAT THEY ACTUALLY WROTE, WITHOUT THE NOTE A PHONE REQUEST CARRIES FOR THE MODEL.
        bare = shown if how == "whatsapp" else text
        rest = [] if how in ("whatsapp", "routine") else self.picked_up(bare)
        if rest:
            # ASKED TO GO ON, HE SAYS WHAT WAS TALKED OVER WORD FOR WORD; NOTHING ABOUT IT NEEDS THINKING.
            self.reply = " ".join(rest)
            self.record = await asyncio.to_thread(history.begin, shown, how, "picked up")
            self.face.reply(self.reply)
            for sentence in rest:
                self.say(sentence)
            await asyncio.to_thread(history.finish, self.record, self.reply, [], 0.0)
            await self.settle()
            return
        routine = routines.asked_for(bare) if how != "routine" else None
        if routine:
            # A ROUTINE NAMED PLAINLY GOES STRAIGHT TO ITS STEPS, BEFORE ANY MODEL GETS TO GUESS AT IT.
            text = routines.request(routine) + (PHONE if how == "whatsapp" else "")
            how = "whatsapp" if how == "whatsapp" else "routine"
        found = None if routine or how == "routine" else quick.match(bare)
        if found and found[0] == "stop" and how == "whatsapp":
            found = ("reply", {"text": "Okay."})
        if found and found[0] == "stop":
            self.cut_off(cancel=False)
            from happy.tools import controls

            if controls.cancel_power():
                self.face.reply("Cancelled; the computer stays on.")
                self.say("Cancelled, the computer stays on.")
                await self.settle()
                return
            self.face.reply("")
            self.face.state("idle")
            self.face.done()
            return
        if found and found[0] == "reply":
            self.record = await asyncio.to_thread(history.begin, shown, how, "quick")
            self.face.reply(found[1]["text"])
            self.say(found[1]["text"])
            await asyncio.to_thread(history.finish, self.record, found[1]["text"], [], 0.0)
            if how == "whatsapp" and self.chat:
                await asyncio.to_thread(self.chat.send, found[1]["text"])
            self.quiet = False
            await self.settle(listen=how != "whatsapp")
            return
        plan = None if found or routine or how in ("routine", "correction") else await asyncio.to_thread(learned.match, bare)
        self.face.state("thinking")
        started = time.monotonic()
        self.steps, self.reply, self.streamed, failed = [], "", "", False
        record = await asyncio.to_thread(history.begin, shown, how, "quick" if found else "learned" if plan else
                                         self.backend.name if self.backend else "")
        self.record = record
        try:
            if found:
                name, args = found
                label = tools.REGISTRY[name].show(args)
                self.face.began("quick", name, label, args)
                result = await quick.run(name, args)
                self.steps.append({"tool": name, "label": label, "args": args, "result": result[:500], "ok": not result.startswith("Error")})
                self.face.ended("quick", name, label, args, result[:2000], not result.startswith("Error"))
                self.face.reply(result)
                self.reply = result
                self.say(self.plain(result))
                log.info("fast path %s %s -> %s (%.0f ms)", name, args, result, (time.monotonic() - started) * 1000)
                if self.backend:
                    self.backend.heard(shown, result)
            elif self.backend is None:
                self.reply = "I don't have a model to think with yet. Pick one in Setup."
                self.say(self.reply)
            else:
                note = "" if how == "whatsapp" else self.leftover_note()
                if plan and not await self.replay(plan, bare, started):
                    stopped = self.steps[-1]
                    # THE MODEL CARRIES ON FROM WHERE THE SAVED STEPS STOPPED, RATHER THAN REPEATING WHAT ALREADY RAN.
                    note += (f"\n\n(Saved steps for this request ran first and stopped at {stopped['label']}: "
                             f"{stopped['result'][:300]} Carry on from there.)")
                    plan = None
                if not plan:
                    await self.think(text + note, started)
                    if how not in ("routine", "correction") and await asyncio.to_thread(learned.learn, bare, self.steps):
                        log.info("learned the steps for %r", bare)
        except asyncio.CancelledError:
            failed = True
            # WHAT WAS ALREADY ON SCREEN IS THE REPLY, SO A TALKED-OVER ANSWER KEEPS ITS WORDS.
            self.reply = self.reply or self.streamed.strip() or "(interrupted)"
            raise
        except Exception as error:
            failed = True
            log.exception("turn failed")
            self.reply = f"Something went wrong: {error}"
            self.face.reply(self.reply)
            self.say(f"Something went wrong. {self.plain(str(error))}")
        finally:
            await asyncio.to_thread(history.finish, record, self.reply, self.steps, time.monotonic() - started, failed)
            if how == "whatsapp" and self.chat:
                await asyncio.to_thread(self.chat.send, self.reply or "I didn't come up with an answer for that.")
            self.quiet = False
            await self.settle(listen=how != "whatsapp")

    async def replay(self, plan, request, started):
        """Runs the steps these words learned, each as its own row; False, and forgotten, the moment one does not work."""
        results = []
        for n, step in enumerate(plan):
            name, args = step["tool"], step["args"]
            registered = tools.REGISTRY.get(name)
            if registered is None:
                await asyncio.to_thread(learned.forget, request)
                return False
            label, call = registered.show(args), f"learned{n}"
            self.face.began(call, name, label, args)
            self.face.state("working")
            result = str(await tools.call(name, args))
            ok = not learned.failed(result)
            self.steps.append({"tool": name, "label": label, "args": args, "result": result[:500], "ok": ok})
            self.face.ended(call, name, label, args, result[:2000], ok)
            if not ok:
                await asyncio.to_thread(learned.forget, request)
                log.info("learned steps for %r stopped at %s: %s", request, name, result[:200])
                return False
            results.append(result)
        await asyncio.to_thread(learned.used, request)
        self.reply = " ".join(results)
        self.face.reply(self.reply)
        self.say(self.plain(self.reply))
        if self.backend:
            self.backend.heard(request, self.reply)
        log.info("replayed learned steps for %r (%.0f ms)", request, (time.monotonic() - started) * 1000)
        return True

    async def think(self, text, started):
        sentences = Sentences()
        self.answered = False
        self.activity = ""
        self.saying = ""
        self.narrated = set()
        self.last_result = None
        self.spoken_at = 0.0
        self.face.reply("")
        facts, held = [], []

        def emit(event):
            if isinstance(event, Text):
                # ONCE A LEVEL OR MEDIA TOOL HAS RUN, WHAT HAPPY SAYS ABOUT IT IS THE TOOL'S OWN RESULT.
                if facts:
                    held.append(event.delta)
                    return
                self.face.reply_add(event.delta)
                self.streamed += event.delta
                for sentence in sentences.add(event.delta):
                    self.answered = True
                    self.say(sentence)
            elif isinstance(event, Act):
                for sentence in sentences.rest():
                    self.answered = True
                    self.say(sentence)
                self.activity = event.label
                self.saying = event.say
                quick.remember(event.tool)
                call = f"c{len(self.steps)}"
                self.face.began(call, event.tool, event.label, event.args)
                self.face.state("working")
                if event.say and not self.answered and time.monotonic() - self.spoken_at > 4:
                    self.narrate(event.say)
                self.steps.append({"tool": event.tool, "label": event.label, "args": event.args, "call": call})
                log.info("tool %s %s", event.tool, event.args)
            elif isinstance(event, Acted):
                self.last_result = event
                for step in reversed(self.steps):
                    if step["tool"] == event.tool and "ok" not in step:
                        step.update(result=event.result[:500], ok=event.ok)
                        self.face.ended(step.pop("call", ""), event.tool, step["label"], step["args"], event.result[:2000], event.ok)
                        break
                if event.tool in FACTUAL and event.ok:
                    facts.append(quick.SPOKEN.get(event.tool, lambda r: r)(event.result))
                log.info("tool %s %s: %s", event.tool, "ok" if event.ok else "failed", event.result[:300].replace("\n", " | "))
            elif isinstance(event, Problem):
                self.face.reply(event.message)
                self.answered = True
                self.say(event.message)

        from happy.agent.prompt import system_prompt

        # ANYTHING THE PROMPT IS BUILT FROM, CHANGED IN THE SETTINGS, BY VOICE OR BY remember, APPLIES FROM THE NEXT TURN.
        prompt = system_prompt(self.cfg)
        if self.prompted and prompt != self.prompted:
            await self.backend.refresh()
        self.prompted = prompt
        guard = asyncio.create_task(self.keep_talking(started))
        tools.shown.set(emit)
        try:
            final = await self.backend.turn(text, emit)
        finally:
            guard.cancel()
        for sentence in sentences.rest():
            self.answered = True
            self.say(sentence)
        self.reply = (final or "").strip()
        if facts and all(step["tool"] in FACTUAL for step in self.steps):
            self.reply = " ".join(facts)
            if held:
                log.info("said the tool's result instead of: %s", "".join(held).strip()[:200])
            self.face.reply(self.reply)
            self.answered = True
            self.say(self.reply)
        elif held:
            rest = "".join(held)
            self.face.reply_add(rest)
            self.answered = True
            self.say(rest)
        if not self.answered:
            self.reply = self.fallback()
            self.face.reply(self.reply)
            self.say(self.reply)
        log.info("answer: %s (%.1fs)", self.reply[:300], time.monotonic() - started)

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
        """Fills a long silence only with what the running tool is actually doing, never a stock phrase."""
        while True:
            await asyncio.sleep(0.4)
            if self.speaker and not self.speaker.idle():
                continue
            if time.monotonic() - max(self.spoken_at, started) <= STILL_EVERY:
                continue
            doing = self.saying.rstrip(".").strip() or self.activity.split(":")[0].strip()
            if doing.split(" ")[0].lower().endswith("ing"):
                # "STILL" ONLY AFTER THE PLAIN LINE WAS HEARD, WHICH IS SKIPPED WHEN THE MODEL OR "ONE SEC" SPOKE FIRST.
                first = f"{doing[0].upper()}{doing[1:]}."
                said = first.lower() in self.narrated or self.saying.lower() in self.narrated
                self.narrate(f"Still {doing[0].lower()}{doing[1:]}." if said else first)

    def narrate(self, line):
        """Says what Happy is doing once per turn; the same words again are noise, not news."""
        if line.lower() in self.narrated:
            return
        self.narrated.add(line.lower())
        self.say(line)

    async def settle(self, listen=True):
        if self.speaker:
            await asyncio.to_thread(self.speaker.wait)
        if self.task is asyncio.current_task() or not self.busy():
            self.face.state("idle")
            self.face.done()
        if listen and self.task is asyncio.current_task() and self.listener and self.cfg.get("follow_up", True) is not False:
            # A REPLY IS OFTEN ANSWERED, SO FOR A MOMENT AFTER IT NOBODY HAS TO SAY THE NAME AGAIN.
            await asyncio.sleep(0.3)
            self.listener.listen_now(wait=FOLLOW_SECONDS, announce=False)

    @staticmethod
    def plain(text):
        return re.sub(r"\s+", " ", text or "").strip()[:400]
