"""Happy's face: the smile with round ends, reshaped for every state, so the shape alone says what is going on."""

import math
import random
import time

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QImage, QPainter, QPainterPath, QPen, QPixmap

WIDTH, HEIGHT = 104, 64
SPAN = 60
NOT_READY = {"waking", "setup"}

# The shape for each state: how deep the curve, how open the mouth, how tilted, how wavy, how bright, how big the ends.
SHAPES = {
    "waking":    dict(sag=0.14, open=0.0, tilt=0.0, wave=0.0, alpha=0.9, ball=0.85),
    "setup":     dict(sag=0.14, open=0.0, tilt=0.0, wave=0.0, alpha=0.9, ball=0.85),
    "idle":      dict(sag=0.26, open=0.0, tilt=0.0, wave=0.0, alpha=1.0, ball=1.0),
    "asleep":    dict(sag=0.0, open=0.0, tilt=0.0, wave=0.0, alpha=0.5, ball=0.8),
    "listening": dict(sag=0.32, open=0.45, tilt=0.0, wave=0.0, alpha=1.0, ball=1.15),
    "thinking":  dict(sag=0.05, open=0.0, tilt=-0.12, wave=0.0, alpha=1.0, ball=1.0),
    "working":   dict(sag=0.18, open=0.0, tilt=0.0, wave=0.09, alpha=1.0, ball=1.0),
    "speaking":  dict(sag=0.26, open=0.12, tilt=0.0, wave=0.0, alpha=1.0, ball=1.0),
    "done":      dict(sag=0.42, open=0.0, tilt=0.0, wave=0.0, alpha=1.0, ball=1.1),
    "error":     dict(sag=-0.2, open=0.0, tilt=0.0, wave=0.0, alpha=1.0, ball=1.0),
}


def dark_mode():
    try:
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:
        return False


def inks():
    """The smile's colour and the faint outline that keeps it visible on any background."""
    if dark_mode():
        return QColor(245, 245, 247), QColor(0, 0, 0, 110)
    return QColor(28, 28, 30), QColor(255, 255, 255, 150)


def curve(left, right, sag, tilt, wave=0.0, phase=0.0, steps=48):
    """The smile line from one end to the other, as points."""
    points = []
    for i in range(steps + 1):
        t = i / steps
        x = left.x() + (right.x() - left.x()) * t
        y = left.y() + (right.y() - left.y()) * t + 4 * sag * SPAN * t * (1 - t)
        if wave:
            y += wave * SPAN * math.sin(t * math.pi * 3 - phase) * math.sin(t * math.pi)
        points.append(QPointF(x, y))
    return points


def path_of(points):
    path = QPainterPath(points[0])
    for point in points[1:]:
        path.lineTo(point)
    return path


class Mascot:
    """Holds the animation state and paints one frame at a time."""

    def __init__(self):
        self.state = "waking"
        self.since = time.monotonic()
        self.progress = None
        self.mouth_level = 0.0
        self.ear_level = 0.0
        self.voice = 0.0
        self.ring = 0.0
        self.shape = dict(SHAPES["waking"])
        self.origin = QPointF(0, 0)
        self.next_twitch = time.monotonic() + 5

    def set_state(self, state):
        if state != self.state:
            self.state = state
            self.since = time.monotonic()

    def lively(self):
        return self.state not in ("idle", "asleep")

    def ready(self):
        return self.state not in NOT_READY

    def step(self, now):
        target = dict(SHAPES.get(self.state, SHAPES["idle"]))
        self.voice += (min(1.0, self.mouth_level * 9) - self.voice) * 0.45
        self.ring += (min(1.0, self.ear_level * 14) - self.ring) * 0.35
        if self.state == "speaking":
            target["open"] = 0.04 + 0.5 * self.voice
        elif self.state == "listening":
            target["open"] = 0.3 + 0.35 * self.ring
        elif self.state == "idle":
            target["sag"] += 0.015 * math.sin(now * 1.6)
            if now > self.next_twitch:
                self.next_twitch = now + random.uniform(4, 9)
                self.shape["sag"] += 0.06
        for key, value in target.items():
            self.shape[key] += (value - self.shape[key]) * 0.2

    def paint(self, painter: QPainter, width, height):
        now = time.monotonic()
        age = now - self.since
        self.step(now)
        shape = self.shape
        painter.setRenderHint(QPainter.Antialiasing)
        ink, outline = inks()
        cx, cy = width / 2, height / 2 - 6
        if self.state == "done":
            cy -= 5 * max(0.0, math.sin(min(age, 0.45) / 0.45 * math.pi))
        if self.state == "error":
            cx += 3 * math.sin(age * 40) * max(0.0, 1 - age / 0.6)
        lift = shape["tilt"] * SPAN / 2
        bob = 2.2 * math.sin(now * 3.2) if self.state == "thinking" else 0.0
        left = QPointF(cx - SPAN / 2, cy - lift + bob)
        right = QPointF(cx + SPAN / 2, cy + lift - bob)
        thick = SPAN * 0.12
        radius = SPAN * 0.105 * shape["ball"]
        lower = curve(left, right, shape["sag"], 0, shape["wave"], now * 6)
        painter.setOpacity(shape["alpha"])
        if not self.ready():
            self.paint_loading(painter, lower, left, right, thick, radius, ink, outline, now)
            painter.setOpacity(1.0)
            return
        lines = [path_of(lower)]
        if shape["open"] > 0.03:
            upper = curve(left, right, shape["sag"] - shape["open"] * 0.55, 0)
            mouth = path_of(lower)
            for point in reversed(upper):
                mouth.lineTo(point)
            mouth.closeSubpath()
            gap = QColor(ink)
            gap.setAlpha(70)
            painter.setPen(Qt.NoPen)
            painter.setBrush(gap)
            painter.drawPath(mouth)
            lines.append(path_of(upper))
        for colour, width_ in ((outline, thick + 3), (ink, thick)):
            pen = QPen(colour, width_)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            for path in lines:
                painter.drawPath(path)
            if colour is outline:
                painter.setPen(Qt.NoPen)
                painter.setBrush(outline)
                for end in (left, right):
                    painter.drawEllipse(end, radius + 1.5, radius + 1.5)
        painter.setPen(Qt.NoPen)
        painter.setBrush(ink)
        for end in (left, right):
            painter.drawEllipse(end, radius, radius)
        shine = QColor(255, 255, 255, 90) if not dark_mode() else QColor(0, 0, 0, 60)
        painter.setBrush(shine)
        for end in (left, right):
            painter.drawEllipse(QPointF(end.x() - radius * 0.35, end.y() - radius * 0.35), radius * 0.32, radius * 0.32)
        painter.setOpacity(1.0)

    def paint_loading(self, painter, points, left, right, thick, radius, ink, outline, now):
        """Not ready: a dotted smile with hollow ends, drawn in solid as loading goes on."""
        line = path_of(points)
        length = line.length()
        faint = QColor(ink)
        faint.setAlpha(110)
        dots = QPen(faint, thick * 0.55)
        dots.setCapStyle(Qt.RoundCap)
        dots.setDashPattern([0.01, 2.2])
        painter.setBrush(Qt.NoBrush)
        painter.setPen(dots)
        painter.drawPath(line)
        if self.progress is None:
            share, start = 0.28, (math.sin(now * 2.2) * 0.5 + 0.5) * 0.72
        else:
            share, start = max(0.03, min(1.0, self.progress)), 0.0
        solid = QPen(ink, thick)
        solid.setCapStyle(Qt.RoundCap)
        solid.setDashPattern([max(0.01, share * length / thick), max(0.01, length / thick)])
        solid.setDashOffset(-start * length / thick)
        painter.setPen(solid)
        painter.drawPath(line)
        painter.setPen(QPen(ink, 2))
        for end in (left, right):
            painter.drawEllipse(end, radius, radius)


def icon(size=64):
    """The smile at rest, as an app icon, in the current ink."""
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    mascot = Mascot()
    mascot.set_state("idle")
    mascot.shape = dict(SHAPES["idle"])
    scale = size / WIDTH
    painter.scale(scale, scale)
    painter.translate(0, (WIDTH - HEIGHT) / 2)
    mascot.paint(painter, WIDTH, HEIGHT)
    painter.end()
    return QIcon(QPixmap.fromImage(image))
