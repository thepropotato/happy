"""The settings view's other half: what is true right now, and the changes it asks for, done off the screen's thread."""

import asyncio
import base64
import json
import subprocess
import sys
import threading
import time
from functools import cache
from pathlib import Path

from happy import paths
from happy import persona
from happy.agent.prompt import owner
from happy.config import Config, SPEECH_SPEEDS, save_secret, speech_speed
from happy.speech import models

KEYS = [("right_option", "Right Option"), ("right_command", "Right Command"), ("right_ctrl", "Right Control"),
        ("right_shift", "Right Shift"), ("fn", "Fn")] if sys.platform == "darwin" else \
       [("right_ctrl", "Right Ctrl"), ("right_alt", "Right Alt"), ("right_shift", "Right Shift")]
PANES = {
    "microphone": "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
    "accessibility": "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
    "screen": "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
}
SERVICE_CHECK = 20
SERVICES_FRESH = 300
SERVICES_SEEN = paths.HOME / "services.json"


class Settings:
    def __init__(self, emit, first=False, tint=lambda colour: None, changed=lambda what: None):
        self.emit = emit
        self.tint = tint
        self.changed = changed
        self.first = first
        self.notice = ""
        self.speech = {"ready": not models.missing(), "progress": None, "text": "", "failed": False}
        self.brains = []
        self.whatsapp = {"state": "busy", "text": "Getting WhatsApp ready…"}
        self.services = remembered_services()
        self.qr_polling = False
        self.checking = False
        self.checked_at = 0.0

    def start(self):
        """Checks what is cheap now; the services are only started when the settings are first opened."""
        for work in (self.prepare_speech, self.find_brains, self.prepare_whatsapp):
            threading.Thread(target=work, daemon=True).start()


    def check_services_later(self):
        if not self.checking:
            self.checking = True
            self.send()
            threading.Thread(target=self.check_services, daemon=True).start()

    def refresh_services(self):
        """Checks the services again when what is shown is old, keeping it on screen meanwhile."""
        if self.services is None or time.monotonic() - self.checked_at > SERVICES_FRESH:
            self.check_services_later()

    def send(self, **extra):
        self.emit({"is": "settings", **self.snapshot(), **extra})

    def snapshot(self):
        cfg = Config()
        return {
            "first": self.first,
            "notice": self.notice,
            "speech": self.speech,
            "model": self.model_state(cfg),
            "name": cfg.get("name") or "Happy",
            "call_me": cfg.get("call_me") or "",
            "persona": persona.read(),
            "owner": owner(),
            "colour": cfg.get("colour") or "#658761",
            "wake": bool(cfg.get("wake_word")),
            "login": cfg.get("start_at_login") is not False,
            "key": cfg.get("push_to_talk"),
            "voice": cfg.get("voice") or "alba",
            "speech_speed": cfg.get("speech_speed"),
            "speech_speeds": SPEECH_SPEEDS,
            "voices": voices(),
            "microphone": cfg.get("input.device") or "",
            "speaker": cfg.get("output.device") or "",
            "microphones": sound_devices("input"),
            "speakers": sound_devices("output"),
            "keys": KEYS,
            "whatsapp": self.whatsapp,
            "services": self.services,
            "services_checking": self.checking,
            "permissions": self.permissions(),
        }

    def model_state(self, cfg):
        options = [{"id": str(i), "label": label} for i, (_, label, _) in enumerate(self.brains)]
        chosen = ""
        kind, model, url = cfg.get("brain.kind"), cfg.get("brain.model"), cfg.get("brain.base_url")
        for i, (found, _, settings) in enumerate(self.brains):
            if kind == "claude" and found == "claude" or kind == "openai" and settings.get("model") == model and settings.get("base_url") == url:
                chosen = str(i)
        if not chosen and kind == "openai" and url:
            chosen = "key"
        if not chosen and options:
            chosen = options[0]["id"]
        return {"options": options, "chosen": chosen, "custom": {"base_url": url or "", "model": model or ""}}

    def prepare_speech(self):
        sizes = {"stt": 482_000_000, "vad": 2_300_000}
        done = {name: 0 for name in models.missing()}

        def progress(name, got, whole):
            done[name] = got
            total = sum(sizes[n] for n in done) or 1
            self.speech = {"ready": False, "failed": False, "progress": 0.9 * sum(done.values()) / total,
                           "text": f"Downloading the speech models ({sum(done.values()) // 1_000_000} MB)"}
            self.send()

        try:
            models.ensure(progress=progress)
            self.speech = {"ready": False, "failed": False, "progress": 0.95, "text": "Getting the voice ready"}
            self.send()
            from happy.speech.speaker import Speaker

            cfg = Config()
            Speaker(cfg.get("voice") or "alba", speed=cfg.get("speech_speed")).warm()
            self.speech = {"ready": True, "failed": False, "progress": None, "text": ""}
        except Exception as error:
            self.speech = {"ready": False, "failed": True, "progress": None,
                           "text": f"Could not get the speech models: {error}. Nothing is lost; trying again picks up from here."}
        self.send()

    def find_brains(self):
        from happy.agent import choose

        try:
            self.brains = choose.options()
        except Exception:
            self.brains = []
        self.send()

    def prepare_whatsapp(self):
        from happy.integrations import whatsapp

        try:
            whatsapp.adopt(Config())
            whatsapp.install(lambda text: None)
            if not whatsapp.start_bridge():
                self.whatsapp = {"state": "failed", "text": "WhatsApp would not start; the log is in ~/.happy/whatsapp-bridge.log."}
            else:
                self.whatsapp = linked(whatsapp.status() or {})
        except Exception as error:
            self.whatsapp = {"state": "failed", "text": f"WhatsApp could not be set up: {error}"}
        self.send()

    def check_services(self):
        """Every MCP server, each given a few seconds to answer, the whole check never more than SERVICE_CHECK."""
        from happy.integrations import discovered, services
        from happy.integrations.mcp import Hub

        async def check():
            hub = Hub()
            found = discovered.everything()
            for name, (spec, source) in found.items():
                if not spec.get("codex_only"):
                    hub.add(name, spec, source)
            mine = services.removable()

            async def one(name, source):
                server = hub.get(name)
                ok = await server.connect(timeout=12)
                state = "connected" if ok else "needs sign-in" if server.error == "needs sign-in" else "failing"
                return {"name": name, "source": source, "state": state, "removable": name in mine,
                        "detail": f"{len(server.tools)} tools" if ok else (server.error or "did not answer")[:90]}

            jobs = {name: asyncio.create_task(one(name, source)) for name, (spec, source) in found.items()
                    if not spec.get("codex_only")}
            listing = asyncio.create_task(asyncio.to_thread(services.connectors))
            await asyncio.wait([*jobs.values(), listing], timeout=SERVICE_CHECK - 4)
            rows = []
            # A CONNECTOR ON THE CLAUDE ACCOUNT REACHES HAPPY THROUGH CLAUDE CODE, WHICHEVER MODEL IS THINKING.
            for name, connected in (listing.result() if listing.done() and not listing.exception() else {}).items():
                rows.append({"name": name, "source": "claude.ai", "removable": False,
                             "state": "connected" if connected else "sign in on claude.ai",
                             "detail": "through Claude" if connected else ""})
            for name, job in jobs.items():
                if job.done() and not job.exception():
                    rows.append(job.result())
                else:
                    job.cancel()
                    rows.append({"name": name, "source": found[name][1], "state": "failing", "detail": "did not answer in time",
                                 "removable": name in mine})
            for name, (spec, source) in found.items():
                if spec.get("codex_only"):
                    rows.append({"name": name, "source": source, "state": "only works inside Codex",
                                 "detail": "", "removable": name in mine})
            try:
                await asyncio.wait_for(hub.close(), 3)
            except (asyncio.TimeoutError, Exception):
                pass
            return rows

        try:
            self.services = asyncio.run(asyncio.wait_for(check(), SERVICE_CHECK))
            remember_services(self.services)
        except Exception as error:
            self.services = self.services or []
            self.notice = f"Could not check the services: {error}"
        self.checking = False
        self.checked_at = time.monotonic()
        self.send()

    def later(self, work):
        threading.Thread(target=work, daemon=True).start()

    def order(self, order):
        """One change asked for by the settings view."""
        kind = order.get("do")
        cfg = Config()
        if kind == "settings":
            # THE SERVICES TAKE SECONDS TO CHECK, SO THEY START THE MOMENT THE SETTINGS OPEN, NOT WHEN THEIR CARD DOES.
            self.later(self.refresh_whatsapp)
            self.send()
            self.refresh_services()
        elif kind == "services":
            self.refresh_services()
        elif kind == "set":
            key, value = order.get("key"), order.get("value")
            if key == "name":
                value = (value or "").strip().title() or "Happy"
            if key == "call_me":
                value = (value or "").strip()
            if key == "speech_speed":
                try:
                    value = speech_speed(value)
                except (TypeError, ValueError):
                    self.notice = "Speech speed must be a finite number."
                    self.send()
                    return
            cfg.set(key, value)
            cfg.save()
            if key == "colour":
                self.tint(value)
            if key == "start_at_login":
                import sys

                from happy import paths
                from happy.system import native

                native.start_at_login(bool(value), [sys.executable, "-m", "happy", "run", "--quiet"], paths.REPO)
            self.changed(key)
            self.send()
        elif kind == "persona":
            text = order.get("text", "")
            if len(text.strip()) > persona.TYPED:
                self.notice = "Learning the way of talking from what you pasted…"
                self.send()

                def learn():
                    persona.adopt(text)
                    self.notice = ""
                    self.send()

                self.later(learn)
            else:
                persona.write(text)
                self.send()
        elif kind == "model":
            self.choose_model(order, cfg)
        elif kind == "speech_retry":
            self.later(self.prepare_speech)
        elif kind == "whatsapp_link":
            self.later(self.poll_qr)
        elif kind == "whatsapp_unlink":
            self.later(self.unlink_whatsapp)
        elif kind == "service_add":
            self.later(lambda: self.service_change(*self.add_service(order.get("text", ""))))
        elif kind == "service_remove":
            from happy.integrations import services

            self.later(lambda: self.service_change(*services.remove(order.get("name", ""))))
        elif kind == "service_signin":
            self.later(lambda: self.sign_in(order.get("name", "")))
        elif kind == "allow":
            self.allow(order.get("what", ""))

    def choose_model(self, order, cfg):
        if order.get("id") == "key":
            url = (order.get("base_url") or "").strip().rstrip("/").removesuffix("/chat/completions")
            if not url or not (order.get("model") or "").strip():
                self.notice = "A service needs its API URL and a model name."
                return self.send()
            cfg.set("brain.kind", "openai")
            cfg.set("brain.base_url", url)
            cfg.set("brain.model", order["model"].strip())
            if (order.get("api_key") or "").strip():
                save_secret("api_key", order["api_key"].strip())
        else:
            found, _, settings = self.brains[int(order.get("id", 0))]
            if found == "claude":
                cfg.set("brain.kind", "claude")
                cfg.set("brain.model", cfg.get("brain.model") if cfg.get("brain.kind") == "claude" and cfg.get("brain.model") else "sonnet")
            else:
                cfg.set("brain.kind", "openai")
                cfg.set("brain.base_url", settings["base_url"])
                cfg.set("brain.model", settings["model"])
                if settings.get("key"):
                    save_secret("api_key", settings["key"])
        cfg.save()
        self.changed("brain")
        self.notice = ""
        self.send()

    def add_service(self, text):
        from happy.integrations import services

        ok, message, _ = services.add(text)
        return ok, message

    def service_change(self, ok, message):
        self.notice = message
        self.checking = True
        self.send()
        self.check_services()
        if ok:
            self.changed("services")

    def sign_in(self, name):
        from happy.integrations import discovered, services
        from happy.integrations.mcp import Hub

        if Config().get("brain.kind") == "claude":
            self.notice = services.sign_in_with_claude(name)
            return self.send()
        self.notice = f"Signing in to {name} in your browser…"
        self.send()

        async def go():
            hub = Hub()
            spec, source = discovered.everything()[name]
            hub.add(name, spec, source)
            ok = await hub.get(name).sign_in()
            await hub.close()
            return ok

        try:
            ok = asyncio.run(go())
        except Exception:
            ok = False
        self.service_change(ok, f"Signed in to {name}." if ok else f"Could not sign in to {name}.")

    def refresh_whatsapp(self):
        from happy.integrations import whatsapp

        if self.whatsapp.get("state") not in ("linked", "unlinked"):
            return
        state = whatsapp.status()
        if state is not None and linked(state) != self.whatsapp:
            self.whatsapp = linked(state)
            self.send()

    def unlink_whatsapp(self):
        from happy.integrations import whatsapp

        self.whatsapp = {"state": "busy", "text": "Unlinking…"}
        self.send()
        if whatsapp.unlink():
            self.whatsapp = {"state": "unlinked", "text": "Unlinked. Link it again like WhatsApp Web."}
        else:
            self.whatsapp = linked(whatsapp.status() or {})
            self.notice = "WhatsApp would not unlink; the log is in ~/.happy/whatsapp-bridge.log."
        self.send()

    def poll_qr(self):
        """Shows WhatsApp's code in the panel until the phone has scanned it."""
        import time

        from happy.integrations import whatsapp

        if self.qr_polling:
            return
        self.qr_polling = True
        try:
            for _ in range(150):
                code = whatsapp.qr_code()
                if code == "linked":
                    self.whatsapp = linked(whatsapp.status() or {})
                    self.emit({"is": "qr", "linked": True})
                    self.send()
                    return
                if code:
                    self.emit({"is": "qr", "image": "data:image/png;base64," + base64.b64encode(code).decode()})
                time.sleep(2)
        finally:
            self.qr_polling = False

    def permissions(self):
        if sys.platform != "darwin":
            return []
        listed = [{"key": key, "title": title, "why": why, "granted": granted(key)} for key, title, why in (
            ("microphone", "Microphone", "To hear you."),
            ("accessibility", "Accessibility", "For the talk key, typing and clicking."),
            ("screen", "Screen Recording", "To look at the screen when you ask."))]
        from happy.system import web_controls

        if web_controls.binary() and Path("/Applications/Google Chrome.app").exists():
            # ONLY CHROME CAN TURN THIS ON: THE BUTTON OPENS ITS SWITCH, AND ITS OWN PROMPT FOLLOWS ON FIRST USE.
            listed.append({"key": "chrome", "title": "Chrome pages", "optional": True, "granted": web_controls.allowed(),
                           "why": "Optional. To work inside pages in your Chrome: switch on remote debugging there, then allow Chrome's prompt."})
        return listed

    def allow(self, what):
        if what == "microphone":
            from AVFoundation import AVCaptureDevice, AVMediaTypeAudio

            if AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeAudio) == 0:
                AVCaptureDevice.requestAccessForMediaType_completionHandler_(AVMediaTypeAudio, lambda ok: self.send())
                return
        elif what == "accessibility":
            from ApplicationServices import AXIsProcessTrustedWithOptions

            AXIsProcessTrustedWithOptions({"AXTrustedCheckOptionPrompt": True})
        elif what == "screen":
            from Quartz import CGRequestScreenCaptureAccess

            CGRequestScreenCaptureAccess()
        elif what == "chrome":
            from happy.system import Failed, web_controls

            try:
                web_controls.open_inspect()
            except Failed as error:
                self.notice = f"Chrome would not open its remote debugging page: {error}"
            self.send()
        if what in PANES:
            subprocess.Popen(["open", PANES[what]])


def linked(state):
    """What the WhatsApp row says, from the bridge's status."""
    if not state.get("linked"):
        return {"state": "unlinked", "text": "Optional. Link it like WhatsApp Web."}
    who = state.get("name") or state.get("phone") or "your phone"
    return {"state": "linked", "text": f"Linked as {who}" if state.get("connected") else f"Linked as {who}, connecting…"}


def remembered_services():
    """The last check's rows, shown at once while a new check runs; None before there has ever been one."""
    try:
        return json.loads(SERVICES_SEEN.read_text())
    except (OSError, ValueError):
        return None


def remember_services(rows):
    try:
        SERVICES_SEEN.write_text(json.dumps(rows))
    except OSError:
        pass


def sound_devices(kind):
    """The microphones or speakers connected right now, by name."""
    try:
        if sys.platform == "darwin":
            from happy.system import macos

            return macos.sound_devices("inpt" if kind == "input" else "outp")
        import sounddevice as sd

        names = [d["name"] for d in sd.query_devices() if d[f"max_{kind}_channels"] > 0]
        return list(dict.fromkeys(names))
    except Exception:
        return []


@cache
def voices():
    try:
        from pocket_tts.utils.utils import _ORIGINS_OF_PREDEFINED_VOICES

        return sorted(_ORIGINS_OF_PREDEFINED_VOICES)
    except Exception:
        return ["alba"]


def granted(key):
    try:
        if key == "chrome":
            from happy.system import web_controls

            return web_controls.allowed()
        if key == "microphone":
            from AVFoundation import AVCaptureDevice, AVMediaTypeAudio

            return AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeAudio) == 3
        if key == "accessibility":
            from ApplicationServices import AXIsProcessTrusted

            return bool(AXIsProcessTrusted())
        from Quartz import CGPreflightScreenCaptureAccess

        return bool(CGPreflightScreenCaptureAccess())
    except Exception:
        return False
