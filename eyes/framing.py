"""THE PART OF THE PICTURE THAT IS THE WINDOW IN FRONT, WITH HAPPY'S OWN WINDOWS PAINTED OVER.

HIS PANEL IS ON SCREEN WHENEVER ANYBODY IS TALKING TO HIM, SO A READ OF THE WHOLE SCREEN CAME
BACK AS HIS OWN TRANSCRIPT, AND THE FILM BEHIND IT WAS NEVER READ."""

from eyes import masking
from eyes.attention import LEAST, on_mac, on_windows, ours
from eyes.shapes import Shot

# WHAT HAPPY'S WINDOWS ARE PAINTED WITH BEFORE THE PICTURE IS READ. BLACK HAS NO WORDS IN IT.
INK = (0, 0, 0)


def framed(shot):
    """THE SHOT CUT DOWN TO THE FRONT WINDOW AND WITH HAPPY PAINTED OUT, OR THE WHOLE SHOT
    WITH HIM PAINTED OUT WHEN NO WINDOW CAN BE FOUND."""
    picture = shot.image.copy()
    scale = shot.density if shot.density else 1.0

    covered(picture, scale)

    box = front_box()

    if box is None:
        return Shot(picture, shot.density)

    left, top, width, height = (round(each * scale) for each in box)
    left, top = max(0, left), max(0, top)
    right, bottom = min(picture.width, left + width), min(picture.height, top + height)

    if right - left < 2 or bottom - top < 2:
        return Shot(picture, shot.density)

    return Shot(picture.crop((left, top, right, bottom)), shot.density)


def covered(picture, scale):
    """HAPPY'S OWN WINDOWS, PAINTED OVER IN PLACE."""
    from PIL import ImageDraw

    drawing = ImageDraw.Draw(picture)

    for left, top, width, height in masking.boxes():
        drawing.rectangle(
            (round(left * scale), round(top * scale), round((left + width) * scale), round((top + height) * scale)),
            fill=INK,
        )


def front_box():
    """WHERE THE FRONT WINDOW THAT IS NOT HAPPY SITS, IN POINTS, OR None."""
    try:
        if on_mac():
            return mac_front(ours())

        if on_windows():
            return windows_front(ours())
    except Exception:
        return None

    return None


def mac_front(ours):
    import Quartz

    from eyes.attention import front

    listed = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID,
    )
    _, wanted = front()
    candidates = []

    for each in listed or ():
        box = each.get("kCGWindowBounds") or {}
        pid = each.get("kCGWindowOwnerPID")
        width, height = box.get("Width") or 0, box.get("Height") or 0

        if each.get("kCGWindowLayer") or not each.get("kCGWindowAlpha") or pid in ours:
            continue

        if min(width, height) < LEAST:
            continue

        candidates.append((pid, width * height, (box.get("X") or 0, box.get("Y") or 0, width, height)))

    # A BROWSER KEEPS A STRIP OR TWO AS WINDOWS OF THEIR OWN, SO THE FRONT APPLICATION'S
    # BIGGEST WINDOW IS THE ONE BEING LOOKED AT, NOT WHICHEVER OF ITS WINDOWS THE LIST PUT FIRST.
    own = [each for each in candidates if each[0] == wanted] if wanted else []
    chosen = max(own or candidates, key=lambda each: each[1], default=None)

    return chosen[2] if chosen else None


def windows_front(ours):
    import ctypes
    import ctypes.wintypes

    user32 = ctypes.windll.user32
    handle = user32.GetTopWindow(None)

    while handle:
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        edge = ctypes.wintypes.RECT()

        if pid.value not in ours and user32.IsWindowVisible(handle) and user32.GetWindowRect(handle, ctypes.byref(edge)):
            width, height = edge.right - edge.left, edge.bottom - edge.top

            if min(width, height) >= LEAST:
                return edge.left, edge.top, width, height

        handle = user32.GetWindow(handle, masking.GW_HWNDNEXT)

    return None
