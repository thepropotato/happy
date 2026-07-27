"""HOLD A KEY TO TALK.

THE LISTENER IS GLOBAL, SO THE TERMINAL NEED NOT BE THE FOCUSED WINDOW. ON MACOS
THAT NEEDS ACCESSIBILITY PERMISSION FOR WHATEVER RUNS PYTHON.
"""

import queue

from pynput import keyboard

from memory import catalogue, settings

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


class PushToTalk:
    def __init__(self, on_press=None):
        # CALLED THE INSTANT THE KEY GOES DOWN, FROM THE LISTENER'S OWN THREAD.
        # THE MAIN LOOP IS USUALLY BUSY WHEN A PERSON DECIDES TO INTERRUPT.
        self.notify = on_press

        # EDGES GO THROUGH A QUEUE, SO A TAP TOO FAST TO POLL IS NEVER MISSED.
        self.events = queue.Queue()

        self.held = False
        self.listener = None
        self.chosen = None

        self.attend()

    def attend(self):
        """WATCH WHICHEVER KEY THE SETTINGS NAME."""
        self.chosen = settings.get(SETTING)
        self.key = KEYS.get(self.chosen, FALLBACK)
        self.key_name = catalogue.naming(SETTING, self.chosen).upper()
        self.held = False

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
        if key == self.key and not self.held:  # AUTOREPEAT IS NOT A NEW PRESS.
            self.held = True
            self.events.put(PRESS)

            if self.notify:
                self.notify()

    def released(self, key):
        if key == self.key and self.held:
            self.held = False
            self.events.put(RELEASE)
