"""
HOLD A KEY TO TALK.

THE LISTENER IS GLOBAL, SO THE TERMINAL DOES NOT HAVE TO BE THE FOCUSED WINDOW.
ON MACOS THAT NEEDS ACCESSIBILITY PERMISSION FOR WHATEVER RUNS PYTHON.
"""

import queue

from pynput import keyboard

KEY = keyboard.Key.alt_r  # RIGHT OPTION. A MODIFIER, SO IT NEVER TYPES ANYTHING.
KEY_NAME = "RIGHT OPTION"

PRESS = "press"
RELEASE = "release"

POLL_SECONDS = 0.2  # WAITING IN SHORT HOPS KEEPS CTRL+C RESPONSIVE.


class PushToTalk:
    def __init__(self, key=KEY, key_name=KEY_NAME, on_press=None):
        self.key = key
        self.key_name = key_name
        self.held = False

        # CALLED THE INSTANT THE KEY GOES DOWN, FROM THE LISTENER'S OWN THREAD.
        # THE MAIN LOOP IS USUALLY BUSY WHEN A PERSON DECIDES TO INTERRUPT, SO
        # ANYTHING THAT HAS TO HAPPEN AT ONCE HANGS OFF HERE AND NOT OFF THE QUEUE.
        self.notify = on_press

        # EDGES GO THROUGH A QUEUE, SO A TAP TOO FAST TO POLL IS NEVER MISSED.
        self.events = queue.Queue()

        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()
        self.listener.wait()  # RAISES HERE IF THE OS REFUSED US THE KEYBOARD.

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

    def reset(self):  # DROP KEY ACTIVITY FROM WHILE WE WERE BUSY TRANSCRIBING.
        while True:
            try:
                self.events.get_nowait()
            except queue.Empty:
                return

    def stop(self):
        self.listener.stop()

    def on_press(self, key):
        if key == self.key and not self.held:  # AUTOREPEAT IS NOT A NEW PRESS.
            self.held = True
            self.events.put(PRESS)

            if self.notify:
                self.notify()

    def on_release(self, key):
        if key == self.key and self.held:
            self.held = False
            self.events.put(RELEASE)
