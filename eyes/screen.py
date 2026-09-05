"""THE SCREEN ITSELF, GRABBED NOW."""

from eyes.shapes import Shot, VisionError

BLIND = (
    "I cannot see the screen. Screen recording has to be allowed for whatever "
    "runs Happy: on macOS in System Settings, Privacy and Security, Screen and "
    "System Audio Recording, then start Happy again. On Windows it is Settings, "
    "Privacy and security, Camera and screen."
)


BLACK = (
    "The screen is black to a picture right now, which is what a streaming player does with its "
    "video. Nothing can be read off it; current_activity and already_open say what the window is "
    "showing without looking."
)


def density(pixels):
    """HOW MANY PIXELS OF PICTURE THERE ARE TO ONE STEP OF THE POINTER."""
    try:
        from screeninfo import get_monitors

        monitors = get_monitors()
    except Exception:
        return 1.0

    for monitor in monitors:
        if monitor.is_primary and monitor.width:
            return pixels / monitor.width

    return pixels / monitors[0].width if monitors and monitors[0].width else 1.0


def grab():
    """THE WHOLE SCREEN, NOW."""
    from PIL import ImageGrab

    try:
        picture = ImageGrab.grab()
    except Exception as error:
        raise VisionError(f"{BLIND} ({error})")

    if picture is None:
        raise VisionError(BLIND)

    # MACOS DOES NOT REFUSE OUT LOUD: THE GRAB SUCCEEDS AND EVERY PIXEL IS BLACK. BUT SO IS A
    # STREAMING PLAYER FILLING THE SCREEN, SO THE SYSTEM IS ASKED WHICH ONE THIS IS.
    if picture.convert("L").getextrema() == (0, 0):
        raise VisionError(BLACK if allowed() else BLIND)

    return Shot(picture, density(picture.width))


def allowed():
    """WHETHER THE SCREEN MAY BE RECORDED, ASKED OF THE SYSTEM RATHER THAN GUESSED OFF THE PIXELS."""
    try:
        import Quartz

        return bool(Quartz.CGPreflightScreenCaptureAccess())
    except Exception:
        return True  # NOT A MAC, OR NO WAY TO ASK: A BLACK FRAME IS THEN JUST A BLACK FRAME.
