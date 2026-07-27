"""TELLING HAPPY'S OWN EVENTS FROM THE PERSON'S.

THE ONLY WAY TO KNOW WHETHER A CLICK WAS OURS IS TO KNOW WHAT WE INJECTED, SO
THIS SITS BESIDE THE INJECTOR RATHER THAN WITH THE OTHER SENSES. EVERY CALL IN
pointer.py MARKS A SHORT WINDOW AS OURS FIRST; ANYTHING ARRIVING OUTSIDE ONE OF
THOSE WINDOWS WAS A HAND ON THE KEYBOARD OR THE MOUSE.

ONLY TIMES ARE KEPT. WHICH KEY WAS PRESSED IS NEVER RECORDED AND NEVER LEAVES
THE CALLBACK: THIS IS HERE TO NOTICE A PERSON, NOT TO READ ONE.

WHAT IT CANNOT DO: MACOS WILL NOT TELL US WHETHER AN EVENT WAS SYNTHETIC, SO
THE WINDOW IS THE WHOLE MECHANISM. A PERSON WHO TYPES IN THE SAME TENTH OF A
SECOND AS HAPPY IS COUNTED AS HAPPY. THE VERIFICATION AFTER EVERY ACT IS WHAT
CATCHES THAT, AND IS WHY THIS IS A HELP RATHER THAN THE GUARANTEE.
"""

import time

# HOW LONG AFTER WE SAY "THIS IS OURS" AN EVENT IS STILL OURS. LONG ENOUGH TO
# COVER THE INJECTION AND THE SYSTEM DELIVERING IT, SHORT ENOUGH THAT A PERSON
# REACHING IN IS NOT SWALLOWED BY IT.
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
        except Exception:  # NO PERMISSION TO LISTEN. HAPPY STILL ACTS AND VERIFIES.
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
        # THE KEY ITSELF IS DELIBERATELY NOT LOOKED AT. ONLY THAT SOMETHING
        # HAPPENED, AND WHEN.
        self.note()

    def busy(self, since):
        """TRUE WHEN THE PERSON TOUCHED THE COMPUTER AFTER since.

        THE EVENT ALSO HAS TO HAVE LANDED AFTER OUR OWN LAST WINDOW CLOSED.
        pynput DELIVERS ON ITS OWN THREAD AND CAN HAND US OUR OWN TYPING A
        MOMENT LATE, WHICH OTHERWISE READS AS A PERSON ARRIVING AND PUTS A
        WARNING ON A PERFECTLY GOOD ACT.
        """
        return self.human > since and self.human > self.until


watcher = Watch()


def watch():
    """THE ONE WATCHER."""
    return watcher
