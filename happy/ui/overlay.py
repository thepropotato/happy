"""What is on screen: the smile in the corner, and the panel it opens down the right edge, both drawn from ui/web."""

import json
import logging
import os
import sys
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QCursor, QGuiApplication, QIcon
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QVBoxLayout, QWidget

from happy import history, paths
from happy.config import Config

log = logging.getLogger("happy.ui")
WEB = Path(__file__).parent / "web"
ASSETS = Path(__file__).parent / "assets"
SMILE_SIZE = (96, 56)
SMILE_INSET = (27, 21)
CORNER = 30
GAP = 10
MOODS = {"idle": "idle", "asleep": "idle", "listening": "listening", "hearing": "hearing", "thinking": "thinking",
         "working": "thinking", "speaking": "speaking", "error": "idle", "waking": "loading", "setup": "loading",
         "done": "idle", "loading": "loading", "gone": "gone"}
KEY_NAMES = {"right_option": "right Option", "right_command": "right Command", "right_ctrl": "right Control",
             "right_shift": "right Shift", "right_alt": "right Alt", "fn": "Fn"}


def native():
    return sys.platform == "darwin" and QGuiApplication.platformName() == "cocoa"


def no_dock_icon():
    """On macOS: run as an accessory, which must happen before any window exists."""
    if native():
        from AppKit import NSApplication, NSApplicationActivationPolicyAccessory

        try:
            NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        except Exception:
            log.exception("could not hide the Dock icon")


def see_through(widget):
    """On macOS: a window with nothing of its own to draw, so only the page's rounded panel and shadow show."""
    if not native():
        return
    try:
        import objc
        from AppKit import NSColor

        window = objc.objc_object(c_void_p=int(widget.winId())).window()
        window.setOpaque_(False)
        window.setBackgroundColor_(NSColor.clearColor())
        window.setHasShadow_(False)
    except Exception:
        log.exception("could not clear the window")


def float_above_everything(widget):
    """On macOS: show on every Space, over full-screen apps."""
    if not native():
        return
    try:
        import objc

        window = objc.objc_object(c_void_p=int(widget.winId())).window()
        window.setLevel_(25)
        window.setCollectionBehavior_(1 | 16 | 64 | 256)
        window.setHidesOnDeactivate_(False)
        if widget.isVisible() and not window.isOnActiveSpace():
            window.orderOut_(None)
            window.orderFrontRegardless()
    except Exception:
        log.exception("could not float the window")


class Channel(QObject):
    """What a page and Python say to each other: an event down, an order up, one JSON line each."""

    event = Signal(str)

    def __init__(self, on_order):
        super().__init__()
        self.on_order = on_order

    @Slot(str)
    def order(self, line):
        try:
            self.on_order(json.loads(line))
        except Exception:
            log.exception("could not follow an order from the page")


class Web(QWidget):
    """A frameless window holding one page from ui/web."""

    def __init__(self, page, flags, on_order):
        super().__init__(None, flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.connected = False
        self.backlog = []
        self.view = QWebEngineView(self)
        self.view.setAttribute(Qt.WA_TranslucentBackground)
        self.view.setStyleSheet("background: transparent")
        self.view.page().setBackgroundColor(Qt.transparent)
        settings = self.view.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, False)
        self.channel = Channel(lambda order: on_order(self, order))
        self.web_channel = QWebChannel(self.view.page())
        self.web_channel.registerObject("core", self.channel)
        self.view.page().setWebChannel(self.web_channel)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.view.load(QUrl.fromLocalFile(str(WEB / page)))

    def send(self, word):
        if self.connected:
            self.channel.event.emit(json.dumps(word, default=str))
        else:
            self.backlog.append(word)

    def opened(self):
        self.connected = True
        for word in self.backlog:
            self.channel.event.emit(json.dumps(word, default=str))
        self.backlog = []


class Grip(QWidget):
    """An invisible layer over the corner smile that takes the clicks and drags."""

    def __init__(self, parent, face):
        super().__init__(parent)
        self.face = face
        self.pressed_at = None
        self.dragged = False
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.pressed_at = event.globalPosition().toPoint()
            self.start = self.window().pos()
            self.dragged = False

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.pressed_at is not None:
            if self.dragged:
                self.face.remember_place()
            else:
                self.face.toggle_panel()
        self.pressed_at = None

    def contextMenuEvent(self, event):
        self.face.menu().exec(event.globalPos())

    def mouseMoveEvent(self, event):
        self.drag(event)

    def drag(self, event):
        if self.pressed_at is None:
            return
        delta = event.globalPosition().toPoint() - self.pressed_at
        if delta.manhattanLength() > 4:
            self.dragged = True
        if self.dragged:
            self.window().move(self.start + delta)


class Panel(Web):
    """The conversation and the settings, down the right edge of the screen."""

    def __init__(self, face):
        super().__init__("index.html", Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool, face.order)
        self.face = face
        self.pinned = False
        self.watching = None
        QApplication.instance().applicationStateChanged.connect(self.app_state)

    def keeps_open(self):
        return self.pinned or self.face.settings_first

    def showEvent(self, event):
        super().showEvent(event)
        see_through(self)
        self.watch_outside()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.stop_watching()

    def watch_outside(self):
        """Closes the panel on a click anywhere outside it, which on macOS only another app ever sees."""
        if not native() or self.watching is not None:
            return
        from AppKit import NSEvent, NSEventMaskLeftMouseDown, NSEventMaskRightMouseDown

        def clicked(event):
            # A CLICK THAT ACTIVATES HAPPY REACHES THIS MONITOR TOO, SO WHERE IT LANDED DECIDES, NOT WHO GOT IT.
            here = QCursor.pos()
            if self.frameGeometry().contains(here) or self.face.mascot.frameGeometry().contains(here):
                return
            if self.isVisible() and not self.keeps_open():
                QTimer.singleShot(0, self.hide)

        self.watching = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            NSEventMaskLeftMouseDown | NSEventMaskRightMouseDown, clicked)

    def stop_watching(self):
        if self.watching is not None:
            from AppKit import NSEvent

            NSEvent.removeMonitor_(self.watching)
            self.watching = None

    def app_state(self, state):
        if state != Qt.ApplicationActive and self.isVisible() and not self.keeps_open() and not native():
            self.hide()

    def place(self):
        screen = (QGuiApplication.screenAt(self.face.mascot.geometry().center()) or QGuiApplication.primaryScreen()).availableGeometry()
        width = max(400, round(screen.width() * 0.25))
        self.setFixedSize(width, screen.height() - GAP * 2)
        self.move(screen.right() - width - GAP + 1, screen.top() + GAP)



class Face(QObject):
    """Thread-safe: every method can be called from any thread; drawing happens on the main one."""

    posted = Signal(object)

    def __init__(self, app, cfg):
        super().__init__()
        no_dock_icon()
        self.app = app
        self.cfg = cfg
        self.happy = None
        self.keys = None
        self.restart = False
        self.settings = None
        self.settings_first = False
        self.calls = {}
        self.level_at = 0.0
        self.mood = "loading"
        self.posted.connect(self.deliver, Qt.QueuedConnection)
        self.mascot = Web("mascot.html", Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus,
                          self.order)
        self.mascot.setAttribute(Qt.WA_ShowWithoutActivating)
        self.mascot.setFixedSize(*SMILE_SIZE)
        self.grip = Grip(self.mascot, self)
        self.grip.setGeometry(0, 0, *SMILE_SIZE)
        self.grip.raise_()
        self.panel = Panel(self)
        self.tray = self.make_tray()
        self.place_mascot()
        self.hovering = False
        self.pointer = QTimer(self)
        self.pointer.timeout.connect(self.watch_pointer)
        self.pointer.start(70)
        if native():
            from happy.system import macos

            macos.cursor_from_background()

    def watch_pointer(self):
        """Hover, found by looking: macOS sends no enter or leave to an app that is not in front."""
        inside = self.mascot.isVisible() and self.mascot.frameGeometry().contains(QCursor.pos())
        if inside == self.hovering:
            if inside and native():
                from AppKit import NSCursor

                NSCursor.pointingHandCursor().set()
            return
        self.hovering = inside
        self.mascot.send({"is": "hover", "on": inside})
        if native():
            from AppKit import NSCursor

            (NSCursor.pointingHandCursor() if inside else NSCursor.arrowCursor()).set()

    # ── windows ──

    def make_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return None
        icon = QIcon(str(ASSETS / "trayTemplate.png"))
        icon.setIsMask(sys.platform == "darwin")
        tray = QSystemTrayIcon(icon)
        tray.setToolTip("Happy")
        tray.setContextMenu(self.menu())
        tray.activated.connect(lambda reason: reason == QSystemTrayIcon.Trigger and self.toggle_panel())
        tray.show()
        return tray

    def menu(self):
        menu = QMenu()
        menu.addAction("Show Happy", self.show_panel)
        menu.addAction("Settings", lambda: (self.show_panel(), self.send_panel({"is": "open_settings"})))
        menu.addSeparator()
        menu.addAction("Restart Happy", self.do_restart)
        menu.addSeparator()
        menu.addAction("Quit", self.app.quit)
        return menu

    def place_mascot(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x, y = self.cfg.get("face.x"), self.cfg.get("face.y")
        whole = QGuiApplication.primaryScreen().geometry()
        if x is None or y is None or not whole.adjusted(-40, -40, 40, 40).contains(QPoint(int(x), int(y))):
            # THE SAME GAP TO THE SMILE ITSELF FROM THE RIGHT EDGE AND THE BOTTOM; THE CORNER IS CLEAR OF THE DOCK.
            x = whole.x() + whole.width() - CORNER - (SMILE_SIZE[0] - SMILE_INSET[0])
            y = whole.y() + whole.height() - CORNER - (SMILE_SIZE[1] - SMILE_INSET[1])
        self.mascot.move(int(x), int(y))

    def remember_place(self):
        cfg = Config()
        cfg.set("face.x", self.mascot.x())
        cfg.set("face.y", self.mascot.y())
        cfg.save()

    def show(self):
        self.mascot.winId()
        see_through(self.mascot)
        float_above_everything(self.mascot)
        self.mascot.show()
        float_above_everything(self.mascot)

    def show_panel(self):
        self.panel.place()
        self.panel.winId()
        float_above_everything(self.panel)
        self.panel.show()
        self.panel.raise_()
        self.panel.activateWindow()
        if native():
            from AppKit import NSApplication

            # WITHOUT A REAL ACTIVATION THE PANEL GETS NO HOVER, AND ITS FIRST CLICK ONLY ACTIVATES IT.
            app = NSApplication.sharedApplication()
            if hasattr(app, "activate"):
                app.activate()
            else:
                app.activateIgnoringOtherApps_(True)
        self.send_panel({"is": "shown"})

    def toggle_panel(self):
        if self.panel.isVisible():
            self.panel.hide()
        else:
            self.show_panel()

    # ── to the pages ──

    def emit(self, word):
        self.posted.emit(word)

    def deliver(self, word):
        if word.get("to") == "panel":
            self.panel.send({k: v for k, v in word.items() if k != "to"})
            return
        self.panel.send(word)
        if word.get("is") in ("state", "level", "hush", "step", "trouble", "tint"):
            self.mascot.send(word)

    def send_panel(self, word):
        self.emit({**word, "to": "panel"})

    # ── from the pages ──

    def order(self, page, order):
        kind, value = order.get("kind"), order.get("value")
        if kind == "connected":
            page.opened()
            page.send({"is": "tint", "colour": Config().get("colour") or "#658761"})
        elif kind == "ask":
            self.asked(value or {})
        elif kind == "hide":
            self.panel.hide()
        elif kind == "show":
            self.show_panel()
        elif kind == "pin":
            self.panel.pinned = bool(value)
        elif kind == "open" and str(value).startswith(("http://", "https://")):
            webbrowser.open(value)
        elif kind == "allow" and self.settings:
            self.settings.allow(value or "accessibility")
        elif kind == "restart":
            self.do_restart()
        elif kind == "quit":
            self.app.quit()

    def asked(self, order):
        kind = order.get("do")
        if kind == "hello":
            self.hello()
        elif kind == "say" and self.happy:
            self.happy.typed(order.get("text", ""))
        elif kind == "stop" and self.happy:
            self.happy.key_down()
            self.happy.key_cancel()
        elif kind == "begin":
            self.begin()
        elif kind == "restart":
            self.do_restart()
        elif self.settings:
            if kind == "settings" and self.settings.services is None:
                pass
            self.settings.order(order)

    def hello(self):
        cfg = Config()
        from happy.agent.prompt import owner

        self.send_panel({"is": "history", "messages": past()})
        if self.happy and self.happy.ready.is_set():
            self.send_panel(self.ready_word(cfg, owner()))
        if self.settings:
            self.settings.send()

    def ready_word(self, cfg, name):
        return {"is": "ready", "name": name, "called": cfg.get("name") or "Happy", "key": KEY_NAMES.get(cfg.get("push_to_talk"), "the talk key"),
                "amiss": "" if self.trusted() else "Allow Accessibility so the talk key works anywhere."}

    @staticmethod
    def trusted():
        if sys.platform != "darwin":
            return True
        from ApplicationServices import AXIsProcessTrusted

        return bool(AXIsProcessTrusted())

    def begin(self):
        if self.settings and not self.settings.speech.get("ready"):
            return
        cfg = Config()
        cfg.set("ready", True)
        cfg.save()
        self.cfg = cfg
        self.settings_first = False
        if self.settings:
            self.settings.first = False
            self.settings.send(started=True)
        self.start_happy()

    def do_restart(self):
        self.restart = True
        self.app.quit()

    def start_happy(self):
        from happy.app import Happy
        from happy.ui.hotkey import PushToTalk

        self.happy = Happy(self.cfg, self)
        self.keys = PushToTalk(self.cfg.get("push_to_talk"), self.happy.key_down, self.happy.key_up, self.note,
                               self.happy.key_cancel)
        self.keys.start()
        threading.Thread(target=self.happy.run, name="happy", daemon=True).start()

    # ── what the core reports, in the words the pages understand ──

    def state(self, name):
        mood = MOODS.get(name, "idle")
        if name == "idle" and self.happy and self.happy.ready.is_set() and self.mood == "loading":
            from happy.agent.prompt import owner

            self.send_panel(self.ready_word(Config(), owner()))
        self.mood = mood
        self.emit({"is": "state", "state": mood})

    def progress(self, text, fraction=None):
        self.mood = "loading"
        self.emit({"is": "state", "state": "loading"})
        self.send_panel({"is": "hint", "text": text})

    def user(self, text):
        self.emit({"is": "message", "who": "you", "text": text})

    def reply(self, text):
        if text:
            self.emit({"is": "message", "who": "happy", "text": text})

    def reply_add(self, delta):
        self.emit({"is": "piece", "text": delta})

    def began(self, call, tool, label, args):
        self.calls[call] = time.monotonic()
        self.emit({"is": "began", "id": call, "name": tool, "why": label, "args": args})

    def ended(self, call, tool, label, args, result, ok):
        seconds = time.monotonic() - self.calls.pop(call, time.monotonic())
        self.emit({"is": "step", "id": call, "name": tool, "why": label, "args": args, "result": result,
                   "failed": not ok, "seconds": seconds})

    def note(self, text):
        self.emit({"is": "working", "text": text})

    def trouble(self, text):
        self.emit({"is": "trouble", "text": text})

    def ready(self, text):
        """Ready: the greeting names the talk key, so this line is only for the log."""
        log.info(text)

    def done(self):
        self.emit({"is": "done"})

    def mouth(self, level):
        self.level(level)

    def ear(self, level):
        self.level(level)

    def level(self, value):
        now = time.monotonic()
        if now - self.level_at > 0.05:
            self.level_at = now
            self.emit({"is": "level", "level": round(float(value), 4)})


def past(limit=40):
    """The conversation so far, oldest first, as the panel reads it back."""
    rows = []
    for turn in reversed(history.recent(limit=limit)):
        rows.append({
            "message": turn["request"], "reply": turn["reply"], "seconds": turn["seconds"],
            "tools": [{"name": step.get("tool"), "why": step.get("label"), "args": step.get("args"),
                       "result": step.get("result"), "failed": step.get("ok") is False} for step in turn["steps"]],
        })
    return rows


def quiet_qt():
    """Sends Qt's own warnings to the log instead of the terminal."""
    from PySide6.QtCore import qInstallMessageHandler

    qt_log = logging.getLogger("happy.qt")
    qInstallMessageHandler(lambda kind, context, message: qt_log.debug("%s", message))


def launch(cfg, settings_first=False):
    """Runs Happy with its smile and panel; the first time, the panel opens on the settings."""
    import signal

    from happy.ui.settings import Settings

    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-features=TranslateUI")
    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Happy")
    quiet_qt()
    face = Face(app, cfg)
    first = not cfg.get("ready")
    face.settings_first = first
    face.settings = Settings(face.send_panel, first=first, tint=lambda colour: face.emit({"is": "tint", "colour": colour}))
    face.settings.start()
    face.show()
    if first or settings_first:
        face.show_panel()
        if not first:
            face.send_panel({"is": "open_settings"})
    if not first:
        face.start_happy()
    signal.signal(signal.SIGTERM, lambda *_: app.quit())
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    beat = QTimer()
    beat.timeout.connect(lambda: None)
    beat.start(300)
    code = app.exec()
    if face.happy:
        face.happy.stop()
        face.keys.stop()
    from happy.integrations import whatsapp

    whatsapp.stop_bridge()
    if face.restart:
        os.execv(sys.executable, [sys.executable, "-m", "happy", "run"] + (["--quiet"] if "--quiet" in sys.argv else []))
    return code
