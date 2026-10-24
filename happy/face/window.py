"""The on-screen face: a draggable mascot in the corner and a bubble that shows what is going on."""

import html
import logging
import re
import subprocess
import sys
import threading
import time

from PySide6.QtCore import QObject, QPoint, QPointF, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QGuiApplication, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QLabel, QMenu, QVBoxLayout, QWidget

from happy import paths
from happy.face.mascot import SIZE, Mascot

log = logging.getLogger("happy.face")
URL = re.compile(r"(https?://[^\s<>()]+[^\s<>().,;:!?'\"])")
LINGER = 9000


def dark():
    try:
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:
        return False


def no_dock_icon():
    """On macOS: run as an accessory, which must happen before any window exists."""
    if sys.platform == "darwin":
        from AppKit import NSApp, NSApplication, NSApplicationActivationPolicyAccessory

        (NSApp or NSApplication.sharedApplication()).setActivationPolicy_(NSApplicationActivationPolicyAccessory)


def float_above_everything(widget):
    """On macOS: show on every Space, over full-screen apps, without stealing focus."""
    if sys.platform != "darwin":
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
        self.setFixedSize(SIZE, SIZE)
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
        painter = QPainter(self)
        self.mascot.paint(painter, self.width(), self.height())

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
        self.face.menu(event.globalPos())


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
        self.label.setMaximumWidth(330)
        self.label.setMinimumWidth(120)
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
        if dark():
            return QColor(38, 38, 43, 245), "#F2F2F5", "#9A9AA3", "#FFB46B"
        return QColor(255, 255, 255, 248), "#1C1C1E", "#8A8A90", "#C2620A"

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        background = self.colours()[0]
        box = QRectF(self.rect()).adjusted(4, 4, -4, -6)
        for spread, alpha in ((4, 16), (2, 22)):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, alpha))
            painter.drawRoundedRect(box.adjusted(-spread / 2, 0, spread / 2, spread), 16, 16)
        path = QPainterPath()
        path.addRoundedRect(box, 15, 15)
        painter.setBrush(background)
        painter.setPen(QPen(QColor(0, 0, 0, 30 if not dark() else 90), 1))
        painter.drawPath(path)

    def compose(self):
        _, ink, quiet, accent = self.colours()
        parts = []
        if self.heard:
            parts.append(f'<div style="color:{quiet};font-size:12px;margin-bottom:4px">“{html.escape(self.heard)}”</div>')
        if self.step:
            if self.step_ok is None:
                dots = "." * (1 + int(time.monotonic() * 2.2) % 3)
                parts.append(f'<div style="color:{accent};font-size:12px;margin-bottom:4px">● {html.escape(self.step)}{dots}</div>')
            else:
                mark = "✓" if self.step_ok else "✕"
                parts.append(f'<div style="color:{quiet};font-size:12px;margin-bottom:4px">{mark} {html.escape(self.step)}</div>')
        if self.answer:
            text = html.escape(self.answer.strip())
            text = URL.sub(lambda m: f'<a href="{m.group(1)}" style="color:{accent}">{shorten(m.group(1))}</a>', text)
            text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text).replace("\n", "<br>")
            parts.append(f'<div style="color:{ink};font-size:14px;line-height:135%">{text}</div>')
        if self.note and not (self.heard or self.answer):
            parts.append(f'<div style="color:{quiet};font-size:12px">{html.escape(self.note)}</div>')
        return "".join(parts)

    def render(self):
        if not self.active:
            return
        content = self.compose()
        if not content:
            self.hide()
            return
        if content != self.label.text():
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

    def peek(self):
        if self.compose():
            self.active = True
            self.hide_timer.stop()
            self.setWindowOpacity(1.0)
            self.render()
            self.hide_timer.start(4000)

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
        self.posted.connect(self.handle, Qt.QueuedConnection)
        self.body.tapped.connect(self.tap)
        self.body.moved.connect(self.place_bubble)
        self.place_body()

    def place_body(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x, y = self.cfg.get("face.x"), self.cfg.get("face.y")
        if x is None or y is None or not screen.adjusted(-40, -40, 40, 40).contains(QPoint(int(x), int(y))):
            x, y = screen.right() - SIZE - 18, screen.bottom() - SIZE - 18
        self.body.move(int(x), int(y))

    def remember_place(self):
        self.cfg.set("face.x", self.body.x())
        self.cfg.set("face.y", self.body.y())
        self.cfg.save()

    def place_bubble(self):
        body = self.body.geometry()
        screen = (QGuiApplication.screenAt(body.center()) or QGuiApplication.primaryScreen()).availableGeometry()
        size = self.bubble.sizeHint().expandedTo(self.bubble.size())
        left = body.left() - size.width() + 6 if body.center().x() > screen.center().x() else body.right() - 6
        top = body.bottom() - size.height() + 4
        left = max(screen.left() + 4, min(left, screen.right() - size.width() - 4))
        top = max(screen.top() + 4, min(top, screen.bottom() - size.height() - 4))
        self.bubble.move(left, top)

    def show(self):
        self.body.winId()
        float_above_everything(self.body)
        self.body.show()
        float_above_everything(self.body)

    def tap(self):
        if self.happy:
            self.happy.key_down()
            self.happy.key_up()

    def menu(self, where):
        menu = QMenu()
        wake = QAction(f"Wake up to “{self.cfg.get('name')}”", menu, checkable=True)
        wake.setChecked(bool(self.cfg.get("wake_word")))
        wake.toggled.connect(self.toggle_wake)
        menu.addAction(wake)
        menu.addSeparator()
        menu.addAction("Settings…", lambda: open_file(paths.CONFIG))
        menu.addAction("Log", lambda: open_file(paths.LOG))
        menu.addSeparator()
        menu.addAction("Quit Happy", self.app.quit)
        menu.exec(where)

    def toggle_wake(self, on):
        self.cfg.set("wake_word", on)
        self.cfg.save()
        if self.happy and self.happy.ears:
            self.happy.ears.wake_enabled = on
            if on and self.happy.ears.wake is None:
                from happy.ears.wake import WakeWord

                self.happy.ears.wake = WakeWord(self.cfg.get("name"), threshold=0.05, boost=3.0)
            elif not on:
                self.happy.ears.wake = None
        self.post("state", "idle" if on else "asleep")

    def post(self, kind, value=None):
        self.posted.emit(kind, value)

    def handle(self, kind, value):
        bubble = self.bubble
        if kind != "state":
            bubble.active = True
        if kind == "state":
            if value == "idle" and not (self.cfg.get("wake_word")):
                value = "asleep"
            self.body.mascot.set_state(value)
            return
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
            bubble.note = value
            bubble.render()
            bubble.linger(6000)
            return
        elif kind == "done":
            if bubble.step and bubble.step_ok is None:
                bubble.step_ok = True
            self.body.mascot.set_state("done")
            QTimer.singleShot(1500, lambda: self.body.mascot.state == "done" and self.body.mascot.set_state(
                "idle" if self.cfg.get("wake_word") else "asleep"))
            bubble.render()
            bubble.linger()
            return
        bubble.render()

    def state(self, name):
        self.post("state", name)

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
        import os

        os.startfile(str(path))
    else:
        subprocess.Popen(["xdg-open", str(path)])


def launch(cfg):
    """Runs Happy with its face; returns when the person quits."""
    from happy.core import Happy
    from happy.face.keys import PushToTalk

    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Happy")
    face = Face(app, cfg)
    face.show()
    happy = Happy(cfg, face)
    face.happy = happy
    keys = PushToTalk(cfg.get("push_to_talk"), happy.key_down, happy.key_up, face.note, happy.key_cancel)
    keys.start()
    threading.Thread(target=happy.run, name="happy", daemon=True).start()
    import signal

    signal.signal(signal.SIGTERM, lambda *_: app.quit())
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    beat = QTimer()
    beat.timeout.connect(lambda: None)
    beat.start(300)
    code = app.exec()
    happy.stop()
    keys.stop()
    return code
