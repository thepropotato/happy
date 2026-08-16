"""HIS OWN FACE, THE ONE ON THE ICON, FOR ANYWHERE THAT WANTS A PICTURE OF HIM."""

import io
from pathlib import Path

ICON = Path(__file__).resolve().parent / "window" / "assets" / "happy.png"

# WHAT A PROFILE PICTURE IS WHEREVER IT GOES: SQUARE, JPEG, AND NOT LARGE.
SIDE = 640

QUALITY = 90

# THE CORNERS OF AN APP ICON ARE TRANSPARENT AND JPEG HAS NO ALPHA TO KEEP THEM.
BEHIND = (255, 255, 255)


def jpeg():
    """HIS ICON AS JPEG BYTES, OR None IF IT IS NOT THERE TO BE READ."""
    if not ICON.exists():
        return None

    from PIL import Image

    with Image.open(ICON) as icon:
        flat = Image.new("RGB", icon.size, BEHIND)
        flat.paste(icon, mask=icon.getchannel("A") if "A" in icon.getbands() else None)

        held = io.BytesIO()
        flat.resize((SIDE, SIDE), Image.LANCZOS).save(held, "JPEG", quality=QUALITY)

        return held.getvalue()
