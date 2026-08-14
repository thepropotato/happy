"""WHERE HAPPY'S OWN WINDOWS SIT, SO NOTHING EVER CLICKS HIM."""

from eyes.attention import GW_HWNDNEXT, on_mac, on_windows, ours
from eyes.parts import Row


def boxes():
    """WHERE HAPPY'S OWN WINDOWS SIT, IN POINTS."""
    try:
        if on_mac():
            return mac_boxes(ours())

        if on_windows():
            return windows_boxes(ours())
    except Exception:
        return []

    return []


def mac_boxes(ours):
    import Quartz

    listed = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID,
    )

    found = []

    for each in listed or ():
        # NO LAYER FILTER: THE PANEL FLOATS ABOVE LAYER ZERO AND IS THE WHOLE POINT.
        if each.get("kCGWindowOwnerPID") not in ours or not each.get("kCGWindowAlpha"):
            continue

        box = each.get("kCGWindowBounds") or {}

        found.append(
            (box.get("X") or 0, box.get("Y") or 0, box.get("Width") or 0, box.get("Height") or 0)
        )

    return found


def windows_boxes(ours):
    import ctypes
    import ctypes.wintypes

    user32 = ctypes.windll.user32
    found = []
    handle = user32.GetTopWindow(None)

    while handle:
        pid = ctypes.c_ulong()

        user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))

        if pid.value in ours and user32.IsWindowVisible(handle):
            edge = ctypes.wintypes.RECT()

            if user32.GetWindowRect(handle, ctypes.byref(edge)):
                found.append(
                    (edge.left, edge.top, edge.right - edge.left, edge.bottom - edge.top)
                )

        handle = user32.GetWindow(handle, GW_HWNDNEXT)

    return found


def covers(found, density, word):
    """TRUE WHEN A READ WORD SITS ON HAPPY'S OWN PANEL."""
    x, y = word.centre

    for left, top, width, height in found:
        if (
            left * density <= x < (left + width) * density
            and top * density <= y < (top + height) * density
        ):
            return True

    return False


def elsewhere(seen, density):
    """THE SAME READING WITH ANYTHING WRITTEN ON HAPPY TAKEN OUT OF IT."""
    found = boxes()

    if not found:
        return seen

    words = [word for word in seen.words if not covers(found, density, word)]

    if len(words) == len(seen.words):
        return seen

    kept = set(map(id, words))
    lines = []

    for line in seen.lines:
        left = tuple(word for word in line.words if id(word) in kept)

        if left:
            lines.append(Row(left))

    return seen._replace(words=words, lines=lines)
