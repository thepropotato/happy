"""Happy's body: the happy.png tile, unchanged, with every state shown in the light around it."""

import math
import time
from pathlib import Path

import numpy as np
from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QConicalGradient, QImage, QPainter, QPainterPath, QPen, QRadialGradient

SIZE = 104
TILE = 60
ASSET = Path(__file__).parent / "assets" / "happy.png"
VIOLET = QColor(139, 124, 255)
RED = QColor(255, 92, 110)
NOT_READY = {"waking", "setup"}


def cropped(image):
    """The tile itself, without the transparent margin the icon was drawn with."""
    alpha = image_array(image)[:, :, 3]
    rows, cols = np.where(alpha > 12)
    return image.copy(QRect(cols.min(), rows.min(), cols.max() - cols.min() + 1, rows.max() - rows.min() + 1))


def image_array(image):
    image = image.convertToFormat(QImage.Format_RGBA8888)
    return np.frombuffer(image.constBits(), np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4)[:, :image.width()]


def greyed(image):
    """The same tile in grey, for while Happy is not ready."""
    pixels = image_array(image).copy()
    grey = (pixels[:, :, :3] @ np.array([0.30, 0.59, 0.11])).astype(np.uint8)
    pixels[:, :, 0] = pixels[:, :, 1] = pixels[:, :, 2] = grey
    out = QImage(pixels.data, pixels.shape[1], pixels.shape[0], pixels.shape[1] * 4, QImage.Format_RGBA8888)
    return out.copy()


class Mascot:
    """Holds the animation state and paints one frame at a time."""

    def __init__(self):
        tile = cropped(QImage(str(ASSET)))
        scale = TILE * 3
        self.tile = tile.scaled(scale, scale, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.grey = greyed(self.tile)
        self.state = "waking"
        self.since = time.monotonic()
        self.progress = None
        self.mouth_level = 0.0
        self.ear_level = 0.0
        self.voice = 0.0
        self.ring = 0.0
        self.glow = 0.0
        self.origin = QPointF(0, 0)

    def set_state(self, state):
        if state != self.state:
            self.state = state
            self.since = time.monotonic()

    def lively(self):
        return self.state not in ("idle", "asleep")

    def ready(self):
        return self.state not in NOT_READY

    def paint(self, painter: QPainter, width, height):
        now = time.monotonic()
        age = now - self.since
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        self.voice += (min(1.0, self.mouth_level * 9) - self.voice) * 0.45
        self.ring += (min(1.0, self.ear_level * 14) - self.ring) * 0.3
        cx, cy = width / 2, height / 2
        scale = 1.0
        if self.state == "speaking":
            scale += 0.06 * self.voice
        elif self.state == "done":
            scale += 0.08 * max(0.0, math.sin(min(age, 0.5) / 0.5 * math.pi))
        elif self.state == "listening":
            scale += 0.03
        elif self.state in ("idle", "asleep"):
            scale += 0.012 * math.sin(now * 1.8)
        if self.state == "error":
            cx += 3.5 * math.sin(age * 42) * max(0.0, 1 - age / 0.6)

        self.halo(painter, cx, cy, now)
        size = TILE * scale
        box = QRectF(cx - size / 2, cy - size / 2, size, size)
        if not self.ready():
            painter.setOpacity(0.55)
            painter.drawImage(box, self.grey)
            painter.setOpacity(1.0)
        else:
            painter.setOpacity(0.8 if self.state == "asleep" else 1.0)
            painter.drawImage(box, self.tile)
            painter.setOpacity(1.0)
        self.rings(painter, cx, cy, now)

    def halo(self, painter, cx, cy, now):
        """The soft light behind the tile: how awake and how loud."""
        state = self.state
        target = {"idle": 0.35 + 0.1 * math.sin(now * 1.8), "listening": 0.75 + 0.25 * self.ring,
                  "thinking": 0.55, "working": 0.5, "speaking": 0.45 + 0.5 * self.voice,
                  "done": 0.9, "error": 0.8}.get(state, 0.0)
        self.glow += (target - self.glow) * 0.15
        if self.glow < 0.02:
            return
        colour = RED if state == "error" else VIOLET
        reach = TILE / 2 + 8 + (10 * self.ring if state == "listening" else 6 * self.voice if state == "speaking" else 0)
        light = QRadialGradient(QPointF(cx, cy), reach + 6)
        inner = QColor(colour)
        inner.setAlphaF(min(1.0, 0.55 * self.glow))
        outer = QColor(colour)
        outer.setAlphaF(0.0)
        light.setColorAt(0.55, inner)
        light.setColorAt(1.0, outer)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(light))
        painter.drawEllipse(QPointF(cx, cy), reach + 6, reach + 6)

    def rings(self, painter, cx, cy, now):
        """What runs around the tile, following its rounded shape: loading progress, thinking, or work in hand."""
        gap = 6
        box = QRectF(cx - TILE / 2 - gap, cy - TILE / 2 - gap, TILE + gap * 2, TILE + gap * 2)
        outline = QPainterPath()
        outline.addRoundedRect(box, TILE * 0.22 + gap, TILE * 0.22 + gap)
        length = outline.length()
        painter.setBrush(Qt.NoBrush)

        def part(colour, width, share, offset):
            pen = QPen(colour, width)
            pen.setCapStyle(Qt.RoundCap)
            pen.setDashPattern([max(0.01, share * length / width), max(0.01, (1 - share) * length / width)])
            pen.setDashOffset(-offset * length / width)
            painter.setPen(pen)
            painter.drawPath(outline)

        if not self.ready():
            painter.setPen(QPen(QColor(150, 150, 160, 120), 3.2))
            painter.drawPath(outline)
            if self.progress is None:
                part(VIOLET, 3.2, 0.2, (now * 0.6) % 1)
            else:
                part(VIOLET, 3.2, max(0.02, min(1.0, self.progress)), 0)
        elif self.state == "working":
            part(VIOLET, 3, 0.22, (now * 0.8) % 1)
        elif self.state == "thinking":
            sweep = QConicalGradient(QPointF(cx, cy), -now * 220)
            sweep.setColorAt(0.0, QColor(139, 124, 255, 230))
            sweep.setColorAt(0.35, QColor(139, 124, 255, 0))
            sweep.setColorAt(1.0, QColor(139, 124, 255, 0))
            painter.setPen(QPen(QBrush(sweep), 3))
            painter.drawPath(outline)
        elif self.state == "listening":
            colour = QColor(VIOLET)
            colour.setAlphaF(0.35 + 0.5 * self.ring)
            painter.setPen(QPen(colour, 2 + 2 * self.ring))
            grow = 1.5 * math.sin(now * 6)
            listening = QPainterPath()
            listening.addRoundedRect(box.adjusted(-grow, -grow, grow, grow), TILE * 0.22 + gap + grow, TILE * 0.22 + gap + grow)
            painter.drawPath(listening)
