"""THE SCREEN ITSELF, GRABBED NOW."""

from eyes.parts import Shot, VisionError

# CAPTURE NEEDS PERMISSION ON BOTH SYSTEMS AND IS REFUSED SILENTLY ON ONE OF
# THEM, SO THE FIX IS SPELLED OUT RATHER THAN THE FAILURE REPORTED.
BLIND = (
    "I cannot see the screen. Screen recording has to be allowed for whatever "
    "runs Happy: on macOS in System Settings, Privacy and Security, Screen and "
    "System Audio Recording, then start Happy again. On Windows it is Settings, "
    "Privacy and security, Camera and screen."
)


def density(pixels):
    """HOW MANY PIXELS OF PICTURE THERE ARE TO ONE STEP OF THE POINTER.

    TWO ON EVERY RETINA MAC AND ON A SCALED WINDOWS DISPLAY. GETTING THIS WRONG
    IS NOT A NEAR MISS: A CLICK MEANT FOR THE MIDDLE OF THE SCREEN LANDS PAST
    THE BOTTOM RIGHT CORNER.
    """
    try:
        from screeninfo import get_monitors

        monitors = get_monitors()
    except Exception:  # NO DISPLAY, OR A PLATFORM IT DOES NOT KNOW.
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

    # PERMISSION IS NOT REFUSED OUT LOUD ON MACOS. THE GRAB SUCCEEDS AND EVERY
    # PIXEL IN IT IS BLACK, WHICH WOULD OTHERWISE READ AS AN EMPTY SCREEN.
    if picture.convert("L").getextrema() == (0, 0):
        raise VisionError(BLIND)

    return Shot(picture, density(picture.width))
