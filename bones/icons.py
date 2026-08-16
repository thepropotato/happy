"""THE ONE PICTURE HAPPY ALREADY HAS, IN WHATEVER SHAPE THIS SYSTEM WANTS ITS ICONS."""

import shutil
import subprocess
import sys
from pathlib import Path

from bones import packages, systems

SOURCE = packages.HAPPY / "face" / "window" / "assets" / "happy.png"

# EVERY SIZE A .icns HOLDS, EACH ALSO GOING IN AT DOUBLE FOR A RETINA SCREEN.
APPLE = (16, 32, 64, 128, 256, 512)

REDMOND = (16, 24, 32, 48, 64, 128, 256)


def icns(into):
    """THE MAC ICON, THROUGH THE TWO TOOLS EVERY MAC ALREADY HAS."""
    folder = into.parent / "happy.iconset"

    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True, exist_ok=True)

    for size in APPLE:
        shrink(folder / f"icon_{size}x{size}.png", size)
        shrink(folder / f"icon_{size}x{size}@2x.png", size * 2)

    made = systems.run(["iconutil", "-c", "icns", str(folder), "-o", str(into)])

    shutil.rmtree(folder, ignore_errors=True)

    return into if made and into.exists() else None


def shrink(where, size):
    """ONE SQUARE COPY, THROUGH THE RESIZER BUILT INTO MACOS."""
    return systems.run(
        ["sips", "-z", str(size), str(size), str(SOURCE), "--out", str(where)]
    )


def ico(into):
    """THE WINDOWS ICON. ONLY PILLOW WRITES THIS ONE, SO THE ENVIRONMENT DOES IT."""
    said = systems.run([str(packages.python()), "-m", "bones.icons", str(into)])

    return into if said and into.exists() else None


def png(into):
    """LINUX WANTS A PNG, AND A PNG IS WHAT THE PICTURE ALREADY IS."""
    shutil.copyfile(SOURCE, into)

    return into


def made(into):
    """WHICHEVER ONE THIS SYSTEM USES."""
    if systems.on_mac():
        return icns(into.with_suffix(".icns"))

    if systems.on_windows():
        return ico(into.with_suffix(".ico"))

    return png(into.with_suffix(".png"))


# RUN BY ico() WITH THE ENVIRONMENT'S PYTHON, WHICH IS THE ONLY ONE THAT HAS PILLOW.
if __name__ == "__main__":
    from PIL import Image

    target = Path(sys.argv[1])

    with Image.open(SOURCE) as picture:
        picture.convert("RGBA").save(target, sizes=[(each, each) for each in REDMOND])
