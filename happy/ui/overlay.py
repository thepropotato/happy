"""What is on screen: the smile in the corner, a bubble beside it, and a menu-bar icon."""

import html
import logging
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFontMetrics, QGuiApplication, QIcon, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QLabel, QMenu, QSystemTrayIcon, QVBoxLayout, QWidget

from happy import paths
from happy.config import Config
from happy.ui import smile
from happy.ui.smile import HEIGHT, WIDTH, Mascot

log = logging.getLogger("happy.ui")
URL = re.compile(r"(https?://[^\s<>()]+[^\s<>().,;:!?'\"])")
LINGER = 9000
ASSETS = Path(__file__).parent / "assets"


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


def float_above_everything(widget):
    """On macOS: show on every Space, over full-screen apps, without stealing focus."""
    if not native():
        return
    try:
        import objc

        view = objc.objc_object(c_void_p=int(widget.winId()))
        window = view.window()
        window.setLevel_(25)
        window.setCollectionBehavior_(1 | 16 | 64 | 256)
        window.setHidesOnDeactivate_(False)
        window.setCanHide_(False)
        if widget.isVisible() and not window.isOnActiveSpace():
            window.orderOut_(None)
            window.orderFrontRegardless()
    except Exception:
        log.exception("could not float the window")


class Body(QWidget):
    tapped = Signal()
    moved = Signal()

    def __init__(self, face):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus)
        self.face = face
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_MacAlwaysShowToolWindow)
        self.setFixedSize(WIDTH, HEIGHT)
        self.mascot = Mascot()
        self.pressed_at = None
        self.dragged = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(16)
        self.frame = 0

    def tick(self):
        self.frame += 1
        if self.mascot.lively() or self.frame % 3 == 0:
            self.mascot.origin = QPointF(self.mapToGlobal(self.rect().center()))
            self.update()

    def paintEvent(self, event):
        self.mascot.paint(QPainter(self), self.width(), self.height())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.pressed_at = event.globalPosition().toPoint()
            self.start = self.pos()
            self.dragged = False

    def mouseMoveEvent(self, event):
        if self.pressed_at is None:
            return
        delta = event.globalPosition().toPoint() - self.pressed_at
        if delta.manhattanLength() > 4:
            self.dragged = True
        if self.dragged:
            self.move(self.start + delta)
            self.moved.emit()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.pressed_at is not None:
            if self.dragged:
                self.face.remember_place()
            else:
                self.tapped.emit()
        self.pressed_at = None

    def enterEvent(self, event):
        self.face.bubble.peek()

    def contextMenuEvent(self, event):
        self.face.menu().exec(event.globalPos())


class Bubble(QWidget):
    def __init__(self, face):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus)
        self.face = face
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_MacAlwaysShowToolWindow)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 14)
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.RichText)
        self.label.setOpenExternalLinks(True)
        self.label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        layout.addWidget(self.label)
        self.heard = ""
        self.step = ""
        self.step_ok = None
        self.answer = ""
        self.note = ""
        self.active = False
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.fade)
        self.dots = QTimer(self)
        self.dots.timeout.connect(lambda: self.isVisible() and self.step and self.step_ok is None and self.render())
        self.dots.start(450)

    def colours(self):
        """Background, text, secondary text and link colours, following the system's light or dark look."""
        if smile.dark_mode():
            return QColor(44, 44, 46, 250), "#F5F5F7", "#98989D", "#4DA3FF"
        return QColor(255, 255, 255, 252), "#1D1D1F", "#6E6E73", "#0A66D8"

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        box = QRectF(self.rect()).adjusted(4, 4, -4, -6)
        for spread, alpha in ((4, 18), (2, 24)):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, alpha))
            painter.drawRoundedRect(box.adjusted(-spread / 2, 0, spread / 2, spread), 14, 14)
        path = QPainterPath()
        path.addRoundedRect(box, 13, 13)
        painter.setBrush(self.colours()[0])
        painter.setPen(QPen(QColor(0, 0, 0, 40 if not smile.dark_mode() else 120), 0.8))
        painter.drawPath(path)

    def compose(self):
        _, ink, quiet, link = self.colours()
        parts = []
        if self.heard:
            parts.append(f'<div style="color:{quiet};font-size:12px;margin-bottom:4px">“{html.escape(self.heard)}”</div>')
        if self.step:
            if self.step_ok is None:
                dots = "." * (1 + int(time.monotonic() * 2.2) % 3)
                parts.append(f'<div style="color:{quiet};font-size:12px;margin-bottom:4px">{html.escape(self.step)}{dots}</div>')
            else:
                mark = "✓" if self.step_ok else "✕"
                parts.append(f'<div style="color:{quiet};font-size:12px;margin-bottom:4px">{mark} {html.escape(self.step)}</div>')
        if self.answer:
            text = html.escape(self.answer.strip())
            text = URL.sub(lambda m: f'<a href="{m.group(1)}" style="color:{link}">{shorten(m.group(1))}</a>', text)
            text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text).replace("\n", "<br>")
            parts.append(f'<div style="color:{ink};font-size:14px;line-height:135%">{text}</div>')
        if self.note and not (self.heard or self.answer):
            parts.append(f'<div style="color:{ink};font-size:13px">{html.escape(self.note)}</div>')
        return "".join(parts)

    def render(self):
        if not self.active:
            return
        content = self.compose()
        if not content:
            self.hide()
            return
        if content != self.label.text():
            plain = max((self.answer, self.note, self.heard, self.step), key=len)
            wide = int(QFontMetrics(self.label.font()).horizontalAdvance(plain) * 1.1) + 16
            self.label.setFixedWidth(max(160, min(330, wide)))
            self.label.setText(content)
            self.adjustSize()
            self.face.place_bubble()
        if not self.isVisible():
            self.setWindowOpacity(1.0)
            self.winId()
            float_above_everything(self)
            self.show()
            float_above_everything(self)
            self.face.place_bubble()

    def peek(self, ms=4000):
        if self.compose():
            self.active = True
            self.hide_timer.stop()
            self.render()
            self.hide_timer.start(ms)

    def linger(self, ms=LINGER):
        self.hide_timer.start(ms)

    def fade(self):
        if self.underMouse():
            self.hide_timer.start(2000)
            return
        self.active = False
        self.hide()


def shorten(url):
    bare = re.sub(r"^https?://(www\.)?", "", url)
    return bare if len(bare) <= 42 else bare[:40] + "…"


class Face(QObject):
    """Thread-safe: every method can be called from any thread; drawing happens on the main one."""

    posted = Signal(str, object)

    def __init__(self, app, cfg):
        super().__init__()
        no_dock_icon()
        self.app = app
        self.cfg = cfg
        self.body = Body(self)
        self.bubble = Bubble(self)
        self.happy = None
        self.setup = None
        self.restart = False
        self.waiting_on = "Getting ready"
        self.posted.connect(self.handle, Qt.QueuedConnection)
        self.body.tapped.connect(self.tap)
        self.body.moved.connect(self.place_bubble)
        self.tray = self.make_tray()
        self.place_body()

    def make_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return None
        if sys.platform == "darwin":
            icon = QIcon(str(ASSETS / "trayTemplate.png"))
            icon.setIsMask(True)
        else:
            icon = smile.icon(32)
        tray = QSystemTrayIcon(icon)
        tray.setToolTip("Happy")
        tray.setContextMenu(self.menu())
        tray.show()
        return tray

    def ready(self):
        return self.body.mascot.ready()

    def place_body(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x, y = self.cfg.get("face.x"), self.cfg.get("face.y")
        if x is None or y is None or not screen.adjusted(-40, -40, 40, 40).contains(QPoint(int(x), int(y))):
            x, y = screen.right() - WIDTH - 10, screen.bottom() - HEIGHT - 10
        self.body.move(int(x), int(y))

    def remember_place(self):
        cfg = Config()
        cfg.set("face.x", self.body.x())
        cfg.set("face.y", self.body.y())
        cfg.save()

    def place_bubble(self):
        body = self.body.geometry()
        screen = (QGuiApplication.screenAt(body.center()) or QGuiApplication.primaryScreen()).availableGeometry()
        size = self.bubble.sizeHint().expandedTo(self.bubble.size())
        left = body.left() - size.width() + 10 if body.center().x() > screen.center().x() else body.right() - 10
        top = body.bottom() - size.height() - 4
        left = max(screen.left() + 4, min(left, screen.right() - size.width() - 4))
        top = max(screen.top() + 4, min(top, screen.bottom() - size.height() - 4))
        self.bubble.move(left, top)

    def show(self):
        self.body.winId()
        float_above_everything(self.body)
        self.body.show()
        float_above_everything(self.body)

    def tap(self):
        if not self.ready():
            self.bubble.note = self.waiting_on
            self.bubble.heard = self.bubble.answer = ""
            self.bubble.active = True
            self.bubble.render()
            self.bubble.linger(5000)
            if self.setup is not None:
                self.setup.raise_()
                self.setup.activateWindow()
            return
        if self.happy:
            self.happy.key_down()
            self.happy.key_up()

    def menu(self):
        menu = QMenu()
        name = self.cfg.get("name") or "Happy"
        status = menu.addAction(f"{name}: ready" if self.ready() else f"{name}: {self.waiting_on.lower()}")
        status.setEnabled(False)
        menu.addSeparator()
        shown = QAction("Show on screen", menu, checkable=True)
        shown.setChecked(self.body.isVisible())
        shown.toggled.connect(lambda on: self.body.setVisible(on) or (on and float_above_everything(self.body)))
        menu.addAction(shown)
        wake = QAction(f"Wake up to “{name}”", menu, checkable=True)
        wake.setChecked(bool(self.cfg.get("wake_word")))
        wake.toggled.connect(self.toggle_wake)
        menu.addAction(wake)
        menu.addSeparator()
        menu.addAction("History…", self.open_history)
        menu.addAction("Setup…", self.open_setup)
        menu.addAction("Log", lambda: open_file(paths.LOG))
        menu.addSeparator()
        menu.addAction(f"Quit {name}", self.app.quit)
        menu.aboutToShow.connect(lambda: None)
        return menu

    def refresh_menu(self):
        if self.tray:
            self.tray.setContextMenu(self.menu())
            name = self.cfg.get("name") or "Happy"
            self.tray.setToolTip(f"{name} — ready" if self.ready() else f"{name} — {self.waiting_on.lower()}")

    def open_setup(self, first=False):
        from happy.ui.setup_window import Setup

        if self.setup is None:
            self.setup = Setup()
            self.setup.started.connect(self.after_setup)
            self.setup.destroyed.connect(lambda: setattr(self, "setup", None))
            self.setup.setAttribute(Qt.WA_DeleteOnClose)
            self.first_setup = first
        self.setup.show()
        self.setup.raise_()
        self.setup.activateWindow()
        if native():
            from AppKit import NSApplication

            NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    def open_history(self):
        from happy.ui.history_window import History

        if getattr(self, "history", None) is None:
            self.history = History()
            self.history.setAttribute(Qt.WA_DeleteOnClose)
            self.history.destroyed.connect(lambda: setattr(self, "history", None))
        self.history.reload()
        self.history.show()
        self.history.raise_()
        self.history.activateWindow()
        if native():
            from AppKit import NSApplication

            NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    def after_setup(self):
        if getattr(self, "first_setup", False) and self.happy is None:
            self.cfg = Config()
            self.start_happy()
        else:
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

    def toggle_wake(self, on):
        cfg = Config()
        cfg.set("wake_word", on)
        cfg.save()
        self.cfg = cfg
        if self.happy and self.happy.listener:
            self.happy.listener.wake_enabled = on
        if self.ready():
            self.post("state", "idle" if on else "asleep")

    def post(self, kind, value=None):
        self.posted.emit(kind, value)

    def handle(self, kind, value):
        bubble = self.bubble
        mascot = self.body.mascot
        if kind == "state":
            if value == "idle" and not self.cfg.get("wake_word"):
                value = "asleep"
            mascot.set_state(value)
            self.refresh_menu()
            return
        if kind == "progress":
            text, fraction = value
            self.waiting_on = text
            mascot.set_state("setup" if fraction is None and text.startswith("Finish") else "waking")
            mascot.progress = fraction
            bubble.heard = bubble.answer = bubble.step = ""
            share = f" · {int(fraction * 100)}%" if fraction is not None else ""
            bubble.note = text if text.startswith(("Finish", "Not ready")) else f"Not ready yet · {text[0].lower() + text[1:]}{share}"
            bubble.active = True
            bubble.render()
            bubble.linger(60000)
            self.refresh_menu()
            return
        bubble.active = True
        if kind == "user":
            bubble.hide_timer.stop()
            bubble.heard, bubble.step, bubble.step_ok, bubble.answer = value, "", None, ""
        elif kind == "reply":
            bubble.answer = value
        elif kind == "reply_add":
            bubble.answer += value
        elif kind == "step":
            bubble.step, bubble.step_ok = value, None
        elif kind == "step_done":
            bubble.step_ok = value
        elif kind == "note":
            bubble.heard = bubble.answer = bubble.step = ""
            bubble.note = value
            bubble.render()
            bubble.linger(7000)
            return
        elif kind == "done":
            if bubble.step and bubble.step_ok is None:
                bubble.step_ok = True
            mascot.set_state("done")
            QTimer.singleShot(1500, lambda: mascot.state == "done" and mascot.set_state(
                "idle" if self.cfg.get("wake_word") else "asleep"))
            bubble.render()
            bubble.linger()
            return
        bubble.render()

    def state(self, name):
        self.post("state", name)

    def progress(self, text, fraction=None):
        self.post("progress", (text, fraction))

    def user(self, text):
        self.post("user", text)

    def reply(self, text):
        self.post("reply", text)

    def reply_add(self, delta):
        self.post("reply_add", delta)

    def step(self, label):
        self.post("step", label)

    def step_done(self, ok):
        self.post("step_done", ok)

    def note(self, text):
        self.post("note", text)

    def done(self):
        self.post("done")

    def mouth(self, level):
        self.body.mascot.mouth_level = level

    def ear(self, level):
        self.body.mascot.ear_level = level


def open_file(path):
    if sys.platform == "darwin":
        subprocess.Popen(["open", "-t", str(path)])
    elif sys.platform == "win32":
        os.startfile(str(path))
    else:
        subprocess.Popen(["xdg-open", str(path)])


def launch(cfg):
    """Runs Happy with its face, opening setup first if it has never been finished."""
    import signal

    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Happy")
    face = Face(app, cfg)
    face.show()
    if cfg.get("ready"):
        face.start_happy()
    else:
        face.progress("Finish setting me up in the window that just opened.")
        face.open_setup(first=True)
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
