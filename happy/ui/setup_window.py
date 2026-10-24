"""The setup window: everything Happy can work out is already filled in, and what is left is a click."""

import os
import subprocess
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QProgressBar, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from happy.speech import models
from happy.config import Config, save_secret, secrets
from happy.ui import smile, theme

SETTINGS_PANES = {
    "microphone": "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
    "accessibility": "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
    "screen": "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
}


class Events(QObject):
    """Carries word from background threads back to the window."""

    speech = Signal(float, str)
    brains = Signal(list)
    whatsapp = Signal(str, str)
    services = Signal(list)
    service_done = Signal(bool, str)


def card(title, hint=""):
    """A section: a heading with a status on the right, and a line saying what it is for."""
    frame = QFrame()
    frame.setObjectName("card")
    box = QVBoxLayout(frame)
    box.setContentsMargins(16, 14, 16, 14)
    box.setSpacing(8)
    top = QHBoxLayout()
    heading = QLabel(title)
    heading.setObjectName("heading")
    top.addWidget(heading)
    top.addStretch()
    status = QLabel("")
    top.addWidget(status)
    box.addLayout(top)
    if hint:
        note = QLabel(hint)
        note.setObjectName("small")
        note.setWordWrap(True)
        box.addWidget(note)
    return frame, box, status


def mark(label, good, text):
    label.setObjectName("good" if good else "bad")
    label.setText(("✓ " if good else "") + text)
    label.style().unpolish(label)
    label.style().polish(label)


class Setup(QWidget):
    started = Signal()

    def __init__(self, standalone=False):
        super().__init__()
        self.cfg = Config()
        self.standalone = standalone
        self.events = Events()
        self.speech_ready = not models.missing()
        self.setObjectName("happy")
        self.setWindowTitle("Set up Happy")
        self.setWindowIcon(smile.icon(128))
        self.setStyleSheet(theme.STYLE)
        self.resize(560, 780)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        body.setObjectName("happy")
        self.column = QVBoxLayout(body)
        self.column.setContentsMargins(24, 22, 24, 22)
        self.column.setSpacing(12)
        scroll.setWidget(body)
        outer.addWidget(scroll)
        self.header()
        self.speech_card()
        self.brain_card()
        self.name_card()
        self.whatsapp_card()
        self.services_card()
        if sys.platform == "darwin":
            self.permissions_card()
        self.column.addStretch()
        footer = QHBoxLayout()
        footer.setContentsMargins(24, 12, 24, 18)
        self.warning = QLabel("")
        self.warning.setObjectName("small")
        self.warning.setWordWrap(True)
        footer.addWidget(self.warning, 1)
        self.start_button = QPushButton("Start Happy")
        self.start_button.setObjectName("primary")
        self.start_button.clicked.connect(self.start)
        footer.addWidget(self.start_button)
        outer.addLayout(footer)
        self.events.speech.connect(self.on_speech)
        self.events.brains.connect(self.on_brains)
        self.events.whatsapp.connect(self.on_whatsapp)
        self.events.services.connect(self.on_services)
        self.events.service_done.connect(self.on_service_done)
        self.refresh_start()
        threading.Thread(target=self.prepare_speech, daemon=True).start()
        threading.Thread(target=lambda: self.events.brains.emit(self.find_brains()), daemon=True).start()
        threading.Thread(target=self.prepare_whatsapp, daemon=True).start()

    def header(self):
        row = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(smile.icon(64).pixmap(64, 64))
        row.addWidget(icon)
        words = QVBoxLayout()
        title = QLabel("Happy")
        title.setObjectName("title")
        subtitle = QLabel("A voice agent that lives on this computer. Everything below is filled in where it could be.")
        subtitle.setObjectName("quiet")
        subtitle.setWordWrap(True)
        words.addWidget(title)
        words.addWidget(subtitle)
        row.addLayout(words, 1)
        self.column.addLayout(row)

    def speech_card(self):
        frame, box, self.speech_status = card("Voice and ears", "Speech is heard and spoken on this computer. Nothing you say leaves it until it is a request.")
        self.speech_bar = QProgressBar()
        self.speech_bar.setTextVisible(False)
        self.speech_bar.setRange(0, 1000)
        self.speech_note = QLabel("")
        self.speech_note.setObjectName("small")
        box.addWidget(self.speech_bar)
        box.addWidget(self.speech_note)
        self.column.addWidget(frame)

    def prepare_speech(self):
        sizes = {"stt": 482_000_000, "vad": 2_300_000}
        done = {name: 0 for name in models.missing()}

        def progress(name, got, whole):
            done[name] = got
            total = sum(sizes[n] for n in done) or 1
            self.events.speech.emit(0.85 * sum(done.values()) / total, f"Downloading the speech models ({sum(done.values()) // 1_000_000} MB)")

        try:
            models.ensure(progress=progress)
            self.events.speech.emit(0.9, "Getting the voice ready (the first time downloads it)")
            from happy.speech.speaker import Speaker

            Speaker(self.cfg.get("voice") or "alba").warm()
            self.events.speech.emit(1.0, "")
        except Exception as error:
            self.events.speech.emit(-1.0, f"Could not get the speech models: {error}")

    def on_speech(self, fraction, text):
        if fraction < 0:
            mark(self.speech_status, False, "Failed")
            self.speech_note.setText(text)
            return
        self.speech_bar.setValue(int(fraction * 1000))
        self.speech_note.setText(text)
        if fraction >= 1.0:
            self.speech_ready = True
            self.speech_bar.hide()
            self.speech_note.hide()
            mark(self.speech_status, True, "Ready")
        self.refresh_start()

    def brain_card(self):
        frame, box, self.brain_status = card("Model", "What thinks for Happy. Claude is used when you are logged in to Claude Code; otherwise whatever runs on this computer.")
        self.brain_choice = QComboBox()
        self.brain_choice.addItem("Looking for what this computer has…", None)
        self.brain_choice.currentIndexChanged.connect(self.on_brain_choice)
        box.addWidget(self.brain_choice)
        self.key_fields = QWidget()
        fields = QVBoxLayout(self.key_fields)
        fields.setContentsMargins(0, 4, 0, 0)
        self.key_url = QLineEdit(self.cfg.get("brain.base_url") or "")
        self.key_url.setPlaceholderText("API URL from the provider's docs, like https://api.openai.com/v1")
        self.key_model = QLineEdit(self.cfg.get("brain.model") or "")
        self.key_model.setPlaceholderText("Model name")
        self.key_secret = QLineEdit()
        self.key_secret.setEchoMode(QLineEdit.Password)
        self.key_secret.setPlaceholderText("API key")
        for field in (self.key_url, self.key_model, self.key_secret):
            fields.addWidget(field)
        self.key_fields.hide()
        box.addWidget(self.key_fields)
        self.column.addWidget(frame)

    def find_brains(self):
        from happy.agent import choose

        try:
            return choose.options()
        except Exception:
            return []

    def on_brains(self, found):
        self.brain_choice.blockSignals(True)
        self.brain_choice.clear()
        for kind, label, settings in found:
            self.brain_choice.addItem(label, (kind, settings))
        self.brain_choice.addItem("Another service, with an API key…", ("key", {}))
        chosen = 0
        kind, model = self.cfg.get("brain.kind"), self.cfg.get("brain.model")
        for index in range(self.brain_choice.count()):
            data = self.brain_choice.itemData(index)
            if kind == "claude" and data[0] == "claude" or kind == "openai" and data[1].get("model") == model and data[1].get("base_url") == self.cfg.get("brain.base_url"):
                chosen = index
        self.brain_choice.setCurrentIndex(chosen)
        self.brain_choice.blockSignals(False)
        self.on_brain_choice(chosen)
        if not found:
            mark(self.brain_status, False, "None found")

    def on_brain_choice(self, index):
        data = self.brain_choice.itemData(index)
        if not data:
            return
        self.key_fields.setVisible(data[0] == "key")
        mark(self.brain_status, True, "Chosen") if data[0] != "key" else self.brain_status.setText("")
        self.refresh_start()

    def name_card(self):
        key = (self.cfg.get("push_to_talk") or "right_option").replace("_", " ")
        frame, box, _ = card("Name", f"Saying the name wakes it: “Hey {self.cfg.get('name') or 'Happy'}, …”. Holding the {key} key works too.")
        self.name_field = QLineEdit(self.cfg.get("name") or "Happy")
        box.addWidget(self.name_field)
        self.column.addWidget(frame)

    def whatsapp_card(self):
        frame, box, self.whatsapp_status = card("WhatsApp", "Read, search and send messages. It links like WhatsApp Web, as a linked device on your phone.")
        self.whatsapp_note = QLabel("Getting WhatsApp ready…")
        self.whatsapp_note.setObjectName("small")
        self.whatsapp_note.setWordWrap(True)
        box.addWidget(self.whatsapp_note)
        self.qr = QLabel()
        self.qr.setAlignment(Qt.AlignCenter)
        self.qr.hide()
        box.addWidget(self.qr)
        self.link_button = QPushButton("Link WhatsApp")
        self.link_button.clicked.connect(self.link_whatsapp)
        self.link_button.hide()
        box.addWidget(self.link_button, 0, Qt.AlignLeft)
        self.qr_timer = QTimer(self)
        self.qr_timer.timeout.connect(self.poll_qr)
        self.column.addWidget(frame)

    def prepare_whatsapp(self):
        from happy.integrations import whatsapp

        try:
            whatsapp.adopt(self.cfg)
            whatsapp.install(lambda text: self.events.whatsapp.emit("busy", "Installing WhatsApp support (once)…"))
            if not whatsapp.start_bridge():
                self.events.whatsapp.emit("failed", "WhatsApp would not start. The log is in ~/.happy/whatsapp-bridge.log.")
                return
            status = whatsapp.status() or {}
            if status.get("linked"):
                self.events.whatsapp.emit("linked", status.get("name") or status.get("phone") or "your phone")
            else:
                self.events.whatsapp.emit("unlinked", "")
        except Exception as error:
            self.events.whatsapp.emit("failed", f"WhatsApp could not be set up: {error}")

    def on_whatsapp(self, state, text):
        if state == "linked":
            self.qr_timer.stop()
            self.qr.hide()
            self.link_button.hide()
            mark(self.whatsapp_status, True, "Linked")
            self.whatsapp_note.setText(f"Linked as {text}.")
        elif state == "unlinked":
            self.whatsapp_status.setText("")
            self.whatsapp_note.setText("Not linked yet. Optional: link it now, or any time later from the menu.")
            self.link_button.show()
        elif state == "busy":
            self.whatsapp_note.setText(text)
        else:
            mark(self.whatsapp_status, False, "Not available")
            self.whatsapp_note.setText(text)

    def link_whatsapp(self):
        self.link_button.hide()
        self.whatsapp_note.setText("On your phone: WhatsApp → Settings → Linked devices → Link a device, then scan this.")
        self.qr.setText("Fetching the code…")
        self.qr.show()
        self.qr_timer.start(2000)
        self.poll_qr()

    def poll_qr(self):
        from happy.integrations import whatsapp

        code = whatsapp.qr_code()
        if code == "linked":
            status = whatsapp.status() or {}
            self.on_whatsapp("linked", status.get("name") or "your phone")
        elif code:
            image = QImage.fromData(code)
            self.qr.setPixmap(QPixmap.fromImage(image).scaled(240, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def services_card(self):
        frame, box, self.services_status = card(
            "Services",
            "Bring your own MCP servers: paste the install command a service gives for Claude Code or Codex, or its MCP "
            "URL. Servers already set up in Claude Code, Claude Desktop, Cursor or VS Code show up here on their own.")
        self.service_list = QVBoxLayout()
        self.service_list.setSpacing(6)
        box.addLayout(self.service_list)
        row = QHBoxLayout()
        self.service_input = QLineEdit()
        self.service_input.setPlaceholderText("claude mcp add --transport http notion https://mcp.notion.com/mcp")
        self.service_input.returnPressed.connect(self.add_service)
        row.addWidget(self.service_input, 1)
        add = QPushButton("Add")
        add.clicked.connect(self.add_service)
        row.addWidget(add)
        box.addLayout(row)
        self.service_note = QLabel("")
        self.service_note.setObjectName("small")
        self.service_note.setWordWrap(True)
        box.addWidget(self.service_note)
        gmail = QPushButton("Add Gmail (Google's official server)…")
        gmail.clicked.connect(lambda: self.gmail_fields.setVisible(not self.gmail_fields.isVisible()))
        box.addWidget(gmail, 0, Qt.AlignLeft)
        self.gmail_fields = QWidget()
        fields = QVBoxLayout(self.gmail_fields)
        fields.setContentsMargins(0, 4, 0, 0)
        from happy.integrations import oauth, services

        how = QLabel(
            f"Google asks every person to bring their own OAuth client: in Google Cloud, enable the Gmail and Gmail MCP "
            f"APIs, then create a Web application client with the redirect <b>{oauth.REDIRECT}</b>. The server is in "
            f"Google's Workspace Developer Preview. It searches, reads, labels and drafts; it does not send. "
            f"<a href='{services.GMAIL_GUIDE}' style='color:{theme.GREEN_SOFT}'>Google's guide</a>")
        how.setObjectName("small")
        how.setWordWrap(True)
        how.setOpenExternalLinks(True)
        fields.addWidget(how)
        self.gmail_id = QLineEdit()
        self.gmail_id.setPlaceholderText("OAuth client ID")
        self.gmail_secret = QLineEdit()
        self.gmail_secret.setEchoMode(QLineEdit.Password)
        self.gmail_secret.setPlaceholderText("OAuth client secret")
        add_gmail = QPushButton("Add Gmail")
        add_gmail.clicked.connect(self.add_gmail)
        fields.addWidget(self.gmail_id)
        fields.addWidget(self.gmail_secret)
        fields.addWidget(add_gmail, 0, Qt.AlignLeft)
        self.gmail_fields.hide()
        box.addWidget(self.gmail_fields)
        self.column.addWidget(frame)
        self.refresh_services()

    def refresh_services(self):
        self.services_status.setText("Checking…")
        threading.Thread(target=lambda: self.events.services.emit(self.check_services()), daemon=True).start()

    def check_services(self):
        """Every MCP server, connected in a hub of its own to see whether it really answers."""
        import asyncio

        from happy.integrations import discovered
        from happy.integrations.mcp import Hub

        async def check():
            hub = Hub()
            found = discovered.everything()
            for name, (spec, source) in found.items():
                hub.add(name, spec, source)

            async def one(name, source):
                server = hub.get(name)
                ok = await server.connect(timeout=15)
                state = "connected" if ok else "needs sign-in" if server.error == "needs sign-in" else "failing"
                return name, source, state, f"{len(server.tools)} tools" if ok else server.error[:90]

            rows = await asyncio.gather(*(one(name, source) for name, (_, source) in found.items()))
            await hub.close()
            return list(rows)

        try:
            return asyncio.run(check())
        except Exception as error:
            return [("", "", "failing", str(error))]

    def on_services(self, rows):
        from happy.integrations import services

        while self.service_list.count():
            item = self.service_list.takeAt(0)
            if item.layout():
                while item.layout().count():
                    child = item.layout().takeAt(0).widget()
                    if child:
                        child.deleteLater()
            elif item.widget():
                item.widget().deleteLater()
        mine = services.removable()
        working = sum(1 for row in rows if row[2] == "connected")
        mark(self.services_status, working == len(rows), f"{working} of {len(rows)} working") if rows else self.services_status.setText("")
        for name, source, state, detail in rows:
            if not name:
                continue
            line = QHBoxLayout()
            label = QLabel(f"{name} <span style='color:{theme.QUIET}'>· {source}</span>")
            line.addWidget(label, 1)
            status = QLabel("")
            mark(status, state == "connected", detail if state == "connected" else state)
            status.setToolTip(detail)
            line.addWidget(status)
            if state == "needs sign-in":
                sign = QPushButton("Sign in")
                sign.clicked.connect(lambda _=False, n=name: self.sign_in(n))
                line.addWidget(sign)
            if name in mine:
                drop = QPushButton("Remove")
                drop.clicked.connect(lambda _=False, n=name: self.remove_service(n))
                line.addWidget(drop)
            self.service_list.addLayout(line)

    def add_service(self):
        from happy.integrations import services

        text = self.service_input.text().strip()
        if not text:
            return
        self.service_note.setText("Adding…")

        def work():
            ok, message, _ = services.add(text)
            self.events.service_done.emit(ok, message)

        threading.Thread(target=work, daemon=True).start()

    def add_gmail(self):
        from happy.integrations import services

        client_id, secret = self.gmail_id.text().strip(), self.gmail_secret.text().strip()
        if not client_id or not secret:
            self.service_note.setText("Gmail needs both the client ID and the client secret.")
            return
        self.service_note.setText("Adding Gmail…")
        threading.Thread(target=lambda: self.events.service_done.emit(*services.add_gmail(client_id, secret)), daemon=True).start()

    def remove_service(self, name):
        from happy.integrations import services

        threading.Thread(target=lambda: self.events.service_done.emit(*services.remove(name)), daemon=True).start()

    def sign_in(self, name):
        """Claude keeps its own sign-ins, so with Claude as the model its MCP screen opens; otherwise Happy signs in."""
        from happy.integrations import services

        data = self.brain_choice.currentData()
        if data and data[0] == "claude":
            self.service_note.setText(services.sign_in_with_claude(name))
            return
        self.service_note.setText(f"Signing in to {name} in your browser…")

        def work():
            import asyncio

            from happy.integrations import discovered
            from happy.integrations.mcp import Hub

            async def go():
                hub = Hub()
                spec, source = discovered.everything()[name]
                hub.add(name, spec, source)
                ok = await hub.get(name).sign_in()
                await hub.close()
                return ok

            ok = asyncio.run(go())
            self.events.service_done.emit(ok, f"Signed in to {name}." if ok else f"Could not sign in to {name}.")

        threading.Thread(target=work, daemon=True).start()

    def on_service_done(self, ok, message):
        self.service_note.setText(message)
        if ok:
            self.service_input.clear()
            self.gmail_fields.hide()
        self.refresh_services()

    def permissions_card(self):
        frame, box, _ = card("Permissions", "macOS asks once. They are granted to the app Happy was started from.")
        self.permission_rows = {}
        for key, title, why in (("microphone", "Microphone", "to hear you"),
                                ("accessibility", "Accessibility", "for the talk key, typing and clicking"),
                                ("screen", "Screen Recording", "to look at the screen when asked")):
            row = QHBoxLayout()
            label = QLabel(f"{title} <span style='color:{theme.QUIET}'>— {why}</span>")
            row.addWidget(label, 1)
            state = QLabel("")
            row.addWidget(state)
            button = QPushButton("Allow")
            button.clicked.connect(lambda _=False, k=key: self.allow(k))
            row.addWidget(button)
            box.addLayout(row)
            self.permission_rows[key] = (state, button)
        self.column.addWidget(frame)
        self.permission_timer = QTimer(self)
        self.permission_timer.timeout.connect(self.check_permissions)
        self.permission_timer.start(1500)
        self.check_permissions()

    def granted(self, key):
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

    def check_permissions(self):
        for key, (state, button) in self.permission_rows.items():
            good = self.granted(key)
            mark(state, good, "Allowed") if good else state.setText("")
            button.setVisible(not good)

    def allow(self, key):
        if key == "microphone":
            from AVFoundation import AVCaptureDevice, AVMediaTypeAudio

            if AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeAudio) == 0:
                AVCaptureDevice.requestAccessForMediaType_completionHandler_(AVMediaTypeAudio, lambda ok: None)
                return
        elif key == "accessibility":
            from ApplicationServices import AXIsProcessTrustedWithOptions

            AXIsProcessTrustedWithOptions({"AXTrustedCheckOptionPrompt": True})
        elif key == "screen":
            from Quartz import CGRequestScreenCaptureAccess

            CGRequestScreenCaptureAccess()
        subprocess.Popen(["open", SETTINGS_PANES[key]])

    def refresh_start(self):
        data = self.brain_choice.currentData() if hasattr(self, "brain_choice") else None
        self.start_button.setEnabled(self.speech_ready)
        if not self.speech_ready:
            self.warning.setText("Happy can start once the speech models are in.")
        elif not data or data[0] == "key" and not self.key_url.text().strip():
            self.warning.setText("Without a brain only everyday commands work: brightness, volume, media, tabs, apps.")
        else:
            self.warning.setText("")

    def save(self):
        cfg = Config()
        data = self.brain_choice.currentData()
        if data:
            kind, settings = data
            if kind == "claude":
                cfg.set("brain.kind", "claude")
                cfg.set("brain.model", cfg.get("brain.model") if cfg.get("brain.kind") == "claude" and cfg.get("brain.model") else "sonnet")
            elif kind == "openai":
                cfg.set("brain.kind", "openai")
                cfg.set("brain.base_url", settings["base_url"])
                cfg.set("brain.model", settings["model"])
                if settings.get("key"):
                    save_secret("api_key", settings["key"])
            elif kind == "key" and self.key_url.text().strip():
                cfg.set("brain.kind", "openai")
                cfg.set("brain.base_url", self.key_url.text().strip().rstrip("/").removesuffix("/chat/completions"))
                cfg.set("brain.model", self.key_model.text().strip())
                if self.key_secret.text().strip():
                    save_secret("api_key", self.key_secret.text().strip())
        cfg.set("name", self.name_field.text().strip().title() or "Happy")
        cfg.set("ready", True)
        cfg.save()

    def start(self):
        self.save()
        self.qr_timer.stop()
        if self.standalone:
            from happy.cli import running_pid
            from happy.integrations import whatsapp

            whatsapp.stop_bridge()

            if running_pid():
                subprocess.run([sys.executable, "-m", "happy", "stop"], capture_output=True)
            subprocess.Popen([sys.executable, "-m", "happy", "start"], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        self.started.emit()
        self.close()


def show_setup():
    """`happy setup`: the window on its own; Start launches Happy in the background."""
    from PySide6.QtWidgets import QApplication

    os.environ.pop("ELECTRON_RUN_AS_NODE", None)
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Happy")
    window = Setup(standalone=True)
    window.started.connect(app.quit)
    window.show()
    window.raise_()
    window.activateWindow()
    return app.exec()
