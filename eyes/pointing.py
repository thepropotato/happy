"""WHERE THE KEYBOARD AND THE POINTER ARE.

THE OTHER TWO CHEAP SENSES. attention.py IS WHAT IS IN FRONT, WHICH IS A WINDOW;
THESE TWO ARE WHERE INSIDE IT A PERSON IS ACTUALLY WORKING, WHICH IS WHAT TYPING
AND CLICKING BOTH LAND ON.
"""

from eyes.attention import front, on_mac, on_windows


def caret():
    """WHAT HAS THE KEYBOARD, IN WORDS, OR "". TYPING GOES WHEREVER THIS IS."""
    if on_mac():
        from eyes.asking import mac_attribute
        from eyes.naming import wording

        _, pid = front()

        if pid is None:
            return ""

        from ApplicationServices import AXUIElementCreateApplication

        app = AXUIElementCreateApplication(pid)
        focused = mac_attribute(app, "AXFocusedUIElement")

        if focused is None:
            return ""

        return (
            wording(mac_attribute(focused, "AXTitle"))
            or wording(mac_attribute(focused, "AXDescription"))
            or wording(mac_attribute(focused, "AXRole"))
        )

    if on_windows():
        try:
            from comtypes.client import CreateObject, GetModule

            GetModule("UIAutomationCore.dll")

            from comtypes.gen.UIAutomationClient import CUIAutomation, IUIAutomation

            automation = CreateObject(CUIAutomation, interface=IUIAutomation)
            focused = automation.GetFocusedElement()

            return str(focused.CurrentName or "") if focused else ""
        except Exception:
            return ""

    return ""


def pointer():
    """WHERE THE POINTER IS, IN THE COORDINATES IT MOVES IN."""
    try:
        from pynput.mouse import Controller

        x, y = Controller().position

        return int(x), int(y)
    except Exception:
        return 0, 0
