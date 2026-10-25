"""Happy's resting smile drawn as a square picture in his colour, for places that want an icon, like his WhatsApp group."""

import math


def blend(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def parts(hex_colour):
    value = int(hex_colour.lstrip("#"), 16)
    return (value >> 16) & 255, (value >> 8) & 255, value & 255


def curve(left, right, sag):
    """The same cubic the panel draws the lips along, so the picture is the smile on screen."""
    reach = (right[0] - left[0]) * 0.3
    one = (left[0] + reach, left[1] + sag / 0.75)
    two = (right[0] - reach, right[1] + sag / 0.75)

    def at(t):
        u = 1 - t
        a, b, c, d = u ** 3, 3 * u * u * t, 3 * u * t * t, t ** 3
        return (a * left[0] + b * one[0] + c * two[0] + d * right[0],
                a * left[1] + b * one[1] + c * two[1] + d * right[1])

    return at


def band(along, half, steps=48):
    """The outline of a lip: half(t) either side of the curve, measured across it."""
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QPolygonF

    outer, inner = [], []
    for i in range(steps + 1):
        t = i / steps
        x, y = along(t)
        ax, ay = along(max(0, t - 0.005))
        bx, by = along(min(1, t + 0.005))
        length = math.hypot(bx - ax, by - ay) or 1
        nx, ny = -(by - ay) / length, (bx - ax) / length
        h = half(t)
        outer.append(QPointF(x - nx * h, y - ny * h))
        inner.append(QPointF(x + nx * h, y + ny * h))
    return QPolygonF(outer + inner[::-1])


def smile_jpeg(hex_colour="#658761", size=640):
    """The idle smile, light lips on a field of his colour, as JPEG bytes."""
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, Qt
    from PySide6.QtGui import QBrush, QColor, QGuiApplication, QImage, QLinearGradient, QPainter, QRadialGradient

    QGuiApplication.instance() or QGuiApplication([])
    base = parts(hex_colour)
    lip_top, lip_bottom = blend(base, (255, 255, 255), 0.9), blend(base, (255, 255, 255), 0.62)
    image = QImage(size, size, QImage.Format.Format_RGB32)
    field = QLinearGradient(0, 0, 0, size)
    field.setColorAt(0, QColor(*blend(base, (255, 255, 255), 0.12)))
    field.setColorAt(1, QColor(*blend(base, (0, 0, 0), 0.18)))
    paint = QPainter(image)
    paint.setRenderHint(QPainter.RenderHint.Antialiasing)
    paint.fillRect(0, 0, size, size, QBrush(field))

    # THE IDLE SHAPE FROM shapes.js, DRAWN A LITTLE LARGER SO IT FILLS A ROUND CROP.
    w = size * 1.45
    wide, sag, lip = 0.48 * w, 0.13 * w, 0.036 * w
    paint.translate(size / 2, size / 2 - sag / 2)
    left, right = (-wide / 2, 0.0), (wide / 2, 0.0)
    along = curve(left, right, sag)
    lips = QLinearGradient(0, -lip, 0, sag + lip)
    lips.setColorAt(0, QColor(*lip_top))
    lips.setColorAt(1, QColor(*lip_bottom))
    paint.setPen(Qt.PenStyle.NoPen)
    paint.setBrush(QBrush(lips))
    paint.drawPolygon(band(along, lambda t: lip * (0.5 + 0.5 * 1.25 * math.sin(t * math.pi))))
    radius = lip * 1.1
    for x, y in (left, right):
        ball = QRadialGradient(QPointF(x - radius * 0.35, y - radius * 0.4), radius * 1.1)
        ball.setColorAt(0, QColor(255, 255, 255))
        ball.setColorAt(0.6, QColor(*lip_top))
        ball.setColorAt(1, QColor(*lip_bottom))
        paint.setBrush(QBrush(ball))
        paint.drawEllipse(QPointF(x, y), radius, radius)
    paint.end()
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "JPEG", 92)
    return bytes(data)
