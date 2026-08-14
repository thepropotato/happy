"""TELLING HAPPY'S OWN EVENTS FROM THE PERSON'S."""

import time

# HOW LONG AFTER WE SAY "THIS IS OURS" AN EVENT IS STILL OURS.
OURS_SECONDS = 0.5


class Watch:
    """WHO HAS BEEN TOUCHING THE COMPUTER, AND WHEN."""

    def __init__(self):
        self.human = 0.0
        self.until = 0.0
        self.listeners = []

    def start(self):
        """BEGIN LISTENING. SAFE TO CALL AS OFTEN AS YOU LIKE."""
        if self.listeners:
            return True

        try:
            from pynput import keyboard, mouse
        except Exception:
            return False

        try:
            watchers = [
                mouse.Listener(on_move=self.moved, on_click=self.clicked, on_scroll=self.scrolled),
                keyboard.Listener(on_press=self.pressed),
            ]

            for each in watchers:
                each.daemon = True
                each.start()
        except Exception:
            return False

        self.listeners = watchers

        return True

    def stop(self):
        for each in self.listeners:
            try:
                each.stop()
            except Exception:
                pass

        self.listeners = []

    def ours(self, seconds=OURS_SECONDS):
        """THE NEXT LITTLE WHILE IS HAPPY ACTING, NOT A PERSON."""
        self.until = max(self.until, time.time() + seconds)

    def note(self):
        now = time.time()

        if now > self.until:
            self.human = now

    def moved(self, x, y):
        self.note()

    def clicked(self, x, y, button, down):
        self.note()

    def scrolled(self, x, y, across, along):
        self.note()

    def pressed(self, pressed_key):
        # THE KEY ITSELF IS DELIBERATELY NOT LOOKED AT. ONLY THAT SOMETHING HAPPENED.
        self.note()

    def busy(self, since):
        """TRUE WHEN THE PERSON TOUCHED THE COMPUTER AFTER since."""
        return self.human > since and self.human > self.until


watcher = Watch()


def watch():
    """THE ONE WATCHER."""
    return watcher
