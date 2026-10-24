"""Happy's body: a small sunny blob drawn in code, with a look for every state."""

import math
import random
import time

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QCursor, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient

SIZE = 84

PALETTES = {
    "idle": ("#FFDB70", "#FFA445"),
    "listening": ("#FFE48C", "#FF9A3C"),
    "thinking": ("#FFDB70", "#FFA445"),
    "working": ("#FFDB70", "#FFA445"),
    "speaking": ("#FFE07E", "#FFA040"),
    "done": ("#FFE07E", "#FFA040"),
    "error": ("#FFC7A8", "#F58D7A"),
    "waking": ("#EFE4C8", "#D9C08F"),
    "asleep": ("#EFE4C8", "#D9C08F"),
}
INK = QColor("#2E2A33")
ACCENT = QColor("#FF8A3D")


def mix(a, b, t):
    a, b = QColor(a), QColor(b)
    return QColor(int(a.red() + (b.red() - a.red()) * t), int(a.green() + (b.green() - a.green()) * t),
                  int(a.blue() + (b.blue() - a.blue()) * t), int(a.alpha() + (b.alpha() - a.alpha()) * t))


class Mascot:
    """Holds the animation state and paints one frame at a time."""

    def __init__(self):
        self.state = "waking"
        self.since = time.monotonic()
        self.top, self.bottom = QColor(PALETTES["waking"][0]), QColor(PALETTES["waking"][1])
        self.mouth_level = 0.0
        self.ear_level = 0.0
        self.mouth_open = 0.0
        self.ring = 0.0
        self.eye_open = 1.0
        self.next_blink = time.monotonic() + 3
        self.blinking_until = 0.0
        self.gaze = QPointF(0, 0)
        self.origin = QPointF(0, 0)

    def set_state(self, state):
        if state != self.state:
            self.state = state
            self.since = time.monotonic()

    def lively(self):
        return self.state not in ("idle", "asleep")

    def step(self, now):
        top, bottom = PALETTES.get(self.state, PALETTES["idle"])
        self.top = mix(self.top, top, 0.15)
        self.bottom = mix(self.bottom, bottom, 0.15)
        self.mouth_open += (min(1.0, self.mouth_level * 9) - self.mouth_open) * 0.45
        self.ring += (min(1.0, self.ear_level * 14) - self.ring) * 0.3
        if now > self.next_blink:
            self.blinking_until = now + 0.14
            self.next_blink = now + random.uniform(2.5, 6.0)
        target = 0.08 if now < self.blinking_until else 1.0
        self.eye_open += (target - self.eye_open) * 0.5
        cursor = QCursor.pos()
        dx, dy = cursor.x() - self.origin.x(), cursor.y() - self.origin.y()
        distance = math.hypot(dx, dy) or 1
        reach = min(1.0, distance / 400) * 3.2
        want = QPointF(dx / distance * reach, dy / distance * reach)
        if self.state == "thinking":
            want = QPointF(2.6 + math.sin(now * 1.3), -2.8)
        elif self.state in ("working", "listening", "speaking"):
            want = QPointF(want.x() * 0.4, want.y() * 0.4)
        self.gaze = QPointF(self.gaze.x() + (want.x() - self.gaze.x()) * 0.12, self.gaze.y() + (want.y() - self.gaze.y()) * 0.12)

    def paint(self, painter: QPainter, width, height):
        now = time.monotonic()
        self.step(now)
        painter.setRenderHint(QPainter.Antialiasing)
        age = now - self.since
        cx, cy = width / 2, height / 2 + 3
        squash = 1 + 0.025 * math.sin(now * 2.1)
        lift = 0.0
        if self.state == "done":
            lift = -6 * max(0.0, math.sin(min(age, 0.6) / 0.6 * math.pi))
        if self.state == "error":
            cx += 3 * math.sin(age * 40) * max(0.0, 1 - age / 0.5)
        if self.state == "speaking":
            squash += self.mouth_open * 0.03
        if self.state == "thinking":
            painter.translate(cx, cy)
            painter.rotate(3 * math.sin(now * 2.4))
            painter.translate(-cx, -cy)
        body_w, body_h = 58, 52 * squash
        body = QRectF(cx - body_w / 2, cy - body_h / 2 + lift + (52 - body_h) / 2, body_w, body_h)

        shadow = QRadialGradient(QPointF(cx, body.bottom() + 6 - lift * 0.3), 26)
        shadow.setColorAt(0, QColor(0, 0, 0, 55))
        shadow.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(shadow))
        painter.drawEllipse(QRectF(cx - 26, body.bottom() + 1 - lift * 0.3, 52, 10))

        if self.state == "listening":
            glow = 6 + 10 * self.ring + 2 * math.sin(now * 5)
            halo = QRadialGradient(QPointF(cx, body.center().y()), body_w / 2 + glow)
            halo.setColorAt(0.6, QColor(255, 160, 70, 120))
            halo.setColorAt(1, QColor(255, 160, 70, 0))
            painter.setBrush(QBrush(halo))
            painter.drawEllipse(body.center(), body_w / 2 + glow, body_h / 2 + glow)

        path = QPainterPath()
        path.addRoundedRect(body, 25, 24)
        fill = QLinearGradient(body.topLeft(), body.bottomLeft())
        fill.setColorAt(0, self.top)
        fill.setColorAt(1, self.bottom)
        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(mix(self.bottom, "#C9701F", 0.35), 1.2))
        painter.drawPath(path)

        shine = QRadialGradient(QPointF(body.left() + 18, body.top() + 12), 20)
        shine.setColorAt(0, QColor(255, 255, 255, 150))
        shine.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(shine))
        painter.drawEllipse(QRectF(body.left() + 4, body.top() + 2, 30, 22))

        face_y = body.center().y() - 3
        gx, gy = self.gaze.x(), self.gaze.y()
        painter.setBrush(QColor(255, 110, 110, 70))
        for side in (-1, 1):
            painter.drawEllipse(QPointF(cx + side * 17 + gx * 0.4, face_y + 9 + gy * 0.3), 5, 3.2)
        self.eyes(painter, cx + gx, face_y + gy, now, age)
        self.mouth(painter, cx + gx * 0.6, face_y + 11 + gy * 0.5, now)
        self.extras(painter, body, now)

    def eyes(self, painter, cx, cy, now, age):
        painter.setPen(Qt.NoPen)
        painter.setBrush(INK)
        mood = self.state
        for side in (-1, 1):
            x = cx + side * 10.5
            if mood in ("asleep", "waking"):
                pen = QPen(INK, 2.2)
                pen.setCapStyle(Qt.RoundCap)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawArc(QRectF(x - 4.5, cy - 3, 9, 6), 200 * 16, 140 * 16)
                painter.setPen(Qt.NoPen)
                painter.setBrush(INK)
                continue
            if mood == "done" and age < 1.6:
                pen = QPen(INK, 2.4)
                pen.setCapStyle(Qt.RoundCap)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawArc(QRectF(x - 4.5, cy - 2, 9, 8), 20 * 16, 140 * 16)
                painter.setPen(Qt.NoPen)
                painter.setBrush(INK)
                continue
            w, h = 7.0, 10.0
            if mood == "listening":
                w, h = 7.8, 11.5
            elif mood == "working":
                h = 7.0
            elif mood == "error":
                h = 8.0
            h = max(1.4, h * self.eye_open)
            painter.drawRoundedRect(QRectF(x - w / 2, cy - h / 2, w, h), w / 2, min(w, h) / 2)
            if h > 4:
                painter.setBrush(QColor(255, 255, 255, 220))
                painter.drawEllipse(QPointF(x - 1.3, cy - h / 4), 1.3, 1.3)
                painter.setBrush(INK)
            if mood == "error":
                pen = QPen(INK, 1.8)
                pen.setCapStyle(Qt.RoundCap)
                painter.setPen(pen)
                painter.drawLine(QPointF(x - 4, cy - 8 - side * 1.2), QPointF(x + 4, cy - 8 + side * 1.2))
                painter.setPen(Qt.NoPen)

    def mouth(self, painter, cx, cy, now):
        pen = QPen(INK, 2.2)
        pen.setCapStyle(Qt.RoundCap)
        mood = self.state
        if mood == "speaking":
            opening = 1.5 + 8 * self.mouth_open
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#5B2A2E"))
            painter.drawRoundedRect(QRectF(cx - 5, cy - 1.5, 10, opening), 4.5, min(4.5, opening / 2))
            if opening > 5:
                painter.setBrush(QColor("#FF7F8A"))
                painter.drawEllipse(QPointF(cx, cy - 1.5 + opening * 0.75), 3, 1.5)
            return
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        if mood == "listening":
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#5B2A2E"))
            painter.drawEllipse(QPointF(cx, cy + 1), 2.6, 2.6 + self.ring * 1.5)
        elif mood == "thinking":
            painter.drawLine(QPointF(cx - 2, cy + 1.5), QPointF(cx + 4, cy + 0.5))
        elif mood == "error":
            painter.drawArc(QRectF(cx - 5, cy + 1, 10, 7), 30 * 16, 120 * 16)
        elif mood in ("asleep", "waking"):
            painter.drawEllipse(QPointF(cx, cy + 1.5), 1.6, 1.2)
        else:
            width = 12 if mood == "done" else 9
            painter.drawArc(QRectF(cx - width / 2, cy - 4, width, 8), 200 * 16, 140 * 16)

    def extras(self, painter, body, now):
        if self.state == "thinking":
            painter.setPen(Qt.NoPen)
            for i in range(3):
                phase = now * 3 - i * 0.7
                alpha = int(110 + 110 * (0.5 + 0.5 * math.sin(phase)))
                painter.setBrush(QColor(255, 138, 61, alpha))
                painter.drawEllipse(QPointF(body.right() - 6 + i * 7, body.top() - 4 - i * 3), 2.6 - i * 0.3, 2.6 - i * 0.3)
        elif self.state == "working":
            pen = QPen(ACCENT, 3)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            ring = body.adjusted(-6, -6, 6, 6)
            painter.drawArc(ring, int(-now * 360 * 16) % (360 * 16), 80 * 16)
        elif self.state == "asleep":
            painter.setPen(QPen(QColor(46, 42, 51, 150), 1.6))
            drift = (now * 0.6) % 1
            font = painter.font()
            font.setPixelSize(11)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(QPointF(body.right() - 2 + drift * 4, body.top() + 2 - drift * 8), "z")
