"""HOLD A KEY TO TALK, FROM ANY WINDOW."""

import queue
import sys
import threading

from pynput import keyboard

from memory import catalogue, settings

MACOS = "darwin"

# MACOS HANDS AN UNTRUSTED LISTENER ONLY THIS PROCESS'S OWN KEYS, WHICH LOOKS
# EXACTLY LIKE PUSH TO TALK WORKING UNTIL YOU CLICK ON ANOTHER WINDOW.
DEAF = (
    "macOS is only giving Happy the key while his own window is in front. "
    "Allow Accessibility for Happy in System Settings, Privacy and Security, "
    "then start him again."
)

# EVERY ONE IS A MODIFIER, SO HOLDING IT DOWN NEVER TYPES ANYTHING.
KEYS = {
    "alt_r": keyboard.Key.alt_r,
    "alt_l": keyboard.Key.alt_l,
    "cmd_r": keyboard.Key.cmd_r,
    "cmd_l": keyboard.Key.cmd_l,
    "ctrl_r": keyboard.Key.ctrl_r,
    "ctrl_l": keyboard.Key.ctrl_l,
    "shift_r": keyboard.Key.shift_r,
    "caps_lock": keyboard.Key.caps_lock,
    "f13": keyboard.Key.f13,
}

SETTING = "ears.key"

FALLBACK = keyboard.Key.alt_r

PRESS = "press"
RELEASE = "release"

POLL_SECONDS = 0.2  # SHORT HOPS KEEP CTRL+C RESPONSIVE.


def deaf():
    """TRUE WHEN THE OS WILL ONLY HAND US THE KEY WHILE WE ARE THE FRONT WINDOW."""
    if sys.platform != MACOS:
        return False

    try:
        from ApplicationServices import AXIsProcessTrusted
    except ImportError:
        return False

    return not AXIsProcessTrusted()


class PushToTalk:
    def __init__(self, on_press=None):
        # FROM THE LISTENER'S OWN THREAD, THE INSTANT THE KEY GOES DOWN.
        self.notify = on_press

        # EDGES GO THROUGH A QUEUE, SO A TAP TOO FAST TO POLL IS NEVER MISSED.
        self.events = queue.Queue()

        self.down = False
        self.listener = None
        self.chosen = None
        self.deaf = False

        self.attend()

    def attend(self):
        """WATCH WHICHEVER KEY THE SETTINGS NAME."""
        self.chosen = settings.get(SETTING)
        self.key = KEYS.get(self.chosen, FALLBACK)
        self.key_said = catalogue.naming(SETTING, self.chosen)
        self.key_name = self.key_said.upper()
        self.down = False

        # A LISTENER BUILT WITHOUT THE PERMISSION STAYS DEAF EVEN AFTER IT IS GRANTED,
        # SO THE ANSWER ONLY CHANGES WHEN THERE IS A NEW ONE.
        self.deaf = deaf()

        self.listener = keyboard.Listener(on_press=self.pressed, on_release=self.released)
        self.listener.start()
        self.listener.wait()  # RAISES HERE IF THE OS REFUSED US THE KEYBOARD.

    def refit(self):
        """MOVE TO ANOTHER KEY. A LISTENER CANNOT BE RETUNED, ONLY REPLACED."""
        if settings.get(SETTING) == self.chosen:
            return False

        self.stop()
        self.attend()

        return True

    def holding(self):
        """TRUE WHILE THE KEY IS DOWN, SO NOTHING ELSE REACHES FOR THE MICROPHONE."""
        return self.down

    def wait_press(self):
        self.wait_for(PRESS)

    def wait_release(self):
        self.wait_for(RELEASE)

    def wait_for(self, edge):
        while True:
            try:
                if self.events.get(timeout=POLL_SECONDS) == edge:
                    return
            except queue.Empty:
                continue

    def reset(self):
        """DROP KEY ACTIVITY FROM WHILE WE WERE BUSY TRANSCRIBING."""
        while True:
            try:
                self.events.get_nowait()
            except queue.Empty:
                return

    def stop(self):
        self.listener.stop()

    def pressed(self, key):
        if key == self.key and not self.down:  # AUTOREPEAT IS NOT A NEW PRESS.
            self.down = True
            self.events.put(PRESS)

            # ON ITS OWN THREAD: MACOS TURNS OFF A KEYBOARD HOOK THAT DAWDLES.
            if self.notify:
                threading.Thread(target=self.notify, daemon=True).start()

    def released(self, key):
        if key == self.key and self.down:
            self.down = False
            self.events.put(RELEASE)
