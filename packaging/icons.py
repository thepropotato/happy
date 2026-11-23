"""Draws packaging/icon.svg into the Mac .icns and the Windows .ico the installers carry, and mac/dmg-background.svg into
the picture behind the DMG's window; run it after changing either."""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

HERE = Path(__file__).resolve().parent


def drawn(renderer, size, height=None):
    image = QImage(QSize(size, height or size), QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    paint = QPainter(image)
    paint.setRenderHint(QPainter.Antialiasing)
    renderer.render(paint)
    paint.end()
    return image


def main():
    QGuiApplication(sys.argv)
    renderer = QSvgRenderer(str(HERE / "icon.svg"))
    drawn(renderer, 1024).save(str(HERE / "icon.png"))
    drawn(renderer, 256).save(str(HERE / "windows" / "happy.ico"))

    with tempfile.TemporaryDirectory() as scratch:
        iconset = Path(scratch) / "Happy.iconset"
        iconset.mkdir()
        for size in (16, 32, 128, 256, 512):
            drawn(renderer, size).save(str(iconset / f"icon_{size}x{size}.png"))
            drawn(renderer, size * 2).save(str(iconset / f"icon_{size}x{size}@2x.png"))
        if shutil.which("iconutil"):
            subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(HERE / "mac" / "Happy.icns")], check=True)

        # ONE TIFF HOLDING BOTH SIZES, SO FINDER SHOWS THE SHARP ONE ON A RETINA SCREEN.
        background = QSvgRenderer(str(HERE / "mac" / "dmg-background.svg"))
        flat, sharp = Path(scratch) / "background.png", Path(scratch) / "background@2x.png"
        drawn(background, 640, 400).save(str(flat))
        drawn(background, 1280, 800).save(str(sharp))
        if shutil.which("tiffutil"):
            subprocess.run(["tiffutil", "-cathidpicheck", str(flat), str(sharp), "-out", str(HERE / "mac" / "dmg-background.tiff")],
                           check=True, capture_output=True)


if __name__ == "__main__":
    main()
