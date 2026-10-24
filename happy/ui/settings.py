"""The settings view's other half: what is true right now, and the changes it asks for, done off the screen's thread."""

import asyncio
import base64
import subprocess
import sys
import threading

from happy.config import Config, save_secret
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


class Settings:
    def __init__(self, emit, first=False, tint=lambda colour: None):
        self.emit = emit
        self.tint = tint
        self.first = first
        self.restart = False
        self.notice = ""
        self.speech = {"ready": not models.missing(), "progress": None, "text": "", "failed": False}
        self.brains = []
        self.whatsapp = {"state": "busy", "text": "Getting WhatsApp ready…"}
        self.services = None
        self.qr_polling = False
        self.checking = False

    def start(self):
        """Checks what is cheap now; the services are only started when the settings are first opened."""
        for work in (self.prepare_speech, self.find_brains, self.prepare_whatsapp):
            threading.Thread(target=work, daemon=True).start()
        if self.first:
            self.check_services_later()

    def check_services_later(self):
        if not self.checking:
            self.checking = True
            threading.Thread(target=self.check_services, daemon=True).start()

    def send(self, **extra):
        self.emit({"is": "settings", **self.snapshot(), **extra})

    def snapshot(self):
        cfg = Config()
        return {
            "first": self.first,
            "restart": self.restart,
            "notice": self.notice,
            "speech": self.speech,
            "model": self.model_state(cfg),
            "name": cfg.get("name") or "Happy",
            "colour": cfg.get("colour") or "#658761",
            "wake": bool(cfg.get("wake_word")),
            "key": cfg.get("push_to_talk"),
            "keys": KEYS,
            "whatsapp": self.whatsapp,
            "services": self.services,
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

            Speaker(Config().get("voice") or "alba").warm()
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
                state = whatsapp.status() or {}
                self.whatsapp = ({"state": "linked", "text": f"Linked as {state.get('name') or state.get('phone') or 'your phone'}"}
                                 if state.get("linked") else {"state": "unlinked", "text": "Optional. Link it like WhatsApp Web."})
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
                hub.add(name, spec, source)
            mine = services.removable()

            async def one(name, source):
                server = hub.get(name)
                ok = await server.connect(timeout=12)
                state = "connected" if ok else "needs sign-in" if server.error == "needs sign-in" else "failing"
                return {"name": name, "source": source, "state": state, "removable": name in mine,
                        "detail": f"{len(server.tools)} tools" if ok else (server.error or "did not answer")[:90]}

            jobs = {name: asyncio.create_task(one(name, source)) for name, (_, source) in found.items()}
            await asyncio.wait(jobs.values(), timeout=SERVICE_CHECK - 4)
            rows = []
            for name, job in jobs.items():
                if job.done() and not job.exception():
                    rows.append(job.result())
                else:
                    job.cancel()
                    rows.append({"name": name, "source": found[name][1], "state": "failing", "detail": "did not answer in time",
                                 "removable": name in mine})
            try:
                await asyncio.wait_for(hub.close(), 3)
            except (asyncio.TimeoutError, Exception):
                pass
            return rows

        try:
            self.services = asyncio.run(asyncio.wait_for(check(), SERVICE_CHECK))
        except Exception as error:
            self.services = []
            self.notice = f"Could not check the services: {error}"
        self.checking = False
        self.send()

    def later(self, work):
        threading.Thread(target=work, daemon=True).start()

    def order(self, order):
        """One change asked for by the settings view."""
        kind = order.get("do")
        cfg = Config()
        if kind == "settings":
            if self.services is None:
                self.check_services_later()
            self.send()
        elif kind == "set":
            key, value = order.get("key"), order.get("value")
            if key == "name":
                value = (value or "").strip().title() or "Happy"
            cfg.set(key, value)
            cfg.save()
            if key == "colour":
                self.tint(value)
            self.restart = self.restart or key in ("name", "push_to_talk")
            self.send()
        elif kind == "model":
            self.choose_model(order, cfg)
        elif kind == "speech_retry":
            self.later(self.prepare_speech)
        elif kind == "whatsapp_link":
            self.later(self.poll_qr)
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
        self.restart = not self.first
        self.notice = ""
        self.send()

    def add_service(self, text):
        from happy.integrations import services

        ok, message, _ = services.add(text)
        return ok, message

    def service_change(self, ok, message):
        self.notice = message
        self.services = None
        self.send()
        self.checking = True
        self.check_services()
        self.restart = self.restart or (ok and not self.first)

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
                    state = whatsapp.status() or {}
                    self.whatsapp = {"state": "linked", "text": f"Linked as {state.get('name') or 'your phone'}"}
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
        return [{"key": key, "title": title, "why": why, "granted": granted(key)} for key, title, why in (
            ("microphone", "Microphone", "To hear you."),
            ("accessibility", "Accessibility", "For the talk key, typing and clicking."),
            ("screen", "Screen Recording", "To look at the screen when you ask."))]

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
        if what in PANES:
            subprocess.Popen(["open", PANES[what]])


def granted(key):
    try:
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
