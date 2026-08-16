"""HOLD THE KEY AND HE LISTENS, AND NOTHING IS HEARD WHILE IT IS NOT HELD."""

import collections
import queue
import threading
import time

from ears import engines, nonsense
from face import show

POLL_SECONDS = 0.2  # SHORT HOPS KEEP CTRL+C RESPONSIVE.

DEAD = "{name} is handing over silence. Pick another microphone in Settings, Ears."

# WHAT WAS ASKED, THE RECORDING IT WAS ASKED IN, AND WHAT THE HEARING COST.
Heard = collections.namedtuple("Heard", "text audio seconds")


class Holding:
    """THE KEY, HELD, AND WHATEVER WAS SAID INTO IT."""

    def __init__(self, recorder, key=None):
        self.recorder = recorder
        self.key = key

        # ONE QUESTION DEEP: TWO THINGS ASKED WHILE HE WAS THINKING MEANS THE
        # SECOND ONE IS WHAT WAS WANTED, NOT A BACKLOG TO WORK THROUGH.
        self.asked = queue.Queue(maxsize=1)

        self.silent = False
        self.running = True

        if key:
            self.pusher = threading.Thread(target=self.pushing, daemon=True, name="pushing")
            self.pusher.start()

    def next(self):
        """THE NEXT THING ASKED OF HAPPY, OR None SO THE CALLER CAN DRAW BREATH."""
        try:
            return self.asked.get(timeout=POLL_SECONDS)
        except queue.Empty:
            return None

    def stop(self):
        self.running = False

        if self.key:
            self.key.stop()

    # ── THE KEY ──

    def pushing(self):
        """WATCHED ON ITS OWN THREAD, BECAUSE WAITING FOR THE KEY BLOCKS."""
        moaned = None

        while self.running:
            try:
                self.key.refit()  # A DIFFERENT KEY WAS PICKED WHILE THE LAST TAKE RAN.
                self.key.reset()  # THE KEYBOARD FROM WHILE THAT TAKE WAS BEING READ.
                self.key.wait_press()

                if not self.running:
                    return

                show.listening()  # WHAT THE PERSON JUST DID, ANSWERED BEFORE ANY DEVICE OPENS.

                self.pressed()

                moaned = None
            except Exception as error:
                # ONCE PER REASON: A MICROPHONE THAT HAS GONE IS GONE EVERY PRESS.
                if str(error) != moaned:
                    moaned = str(error)
                    show.trouble(f"Key: {moaned}")

                time.sleep(POLL_SECONDS)

    def pressed(self):
        """ONE PRESS: RECORD WHILE IT IS DOWN, AND HAND OVER WHATEVER WAS SAID INTO IT.

        NOTHING IS MATCHED AGAINST HIS NAME HERE. HOLDING THE KEY IS ALREADY SOMEBODY SAYING
        WHO THEY ARE TALKING TO, AND SAYING IT TWICE IS SAYING IT ONCE TOO OFTEN."""
        self.recorder.start()  # THE DEVICE OPENS HERE AND SHUTS AGAIN IN stop().

        self.key.wait_release()

        where = self.recorder.stop()

        if where is None:  # THE KEY WAS BRUSHED, NOT HELD.
            show.idle()
            return

        started = time.perf_counter()
        text = (engines.transcribe(where) or "").strip()
        seconds = time.perf_counter() - started

        if not text or nonsense.nothing(text):
            where.unlink(missing_ok=True)
            self.deafness()
            show.idle()
            return

        self.remember(Heard(text=text, audio=where, seconds=seconds))

    def deafness(self):
        """A DEVICE HANDING OVER NOTHING IS NOT SOMEBODY WHO SAID NOTHING, AND ONLY A TAKE
        THAT CAME BACK EMPTY IS EVER A REASON TO LOOK."""
        gone = self.recorder.deaf()

        if gone and not self.silent:
            show.trouble(DEAD.format(name=self.recorder.hearing()))

        self.silent = gone

    def remember(self, found):
        """THE NEWEST QUESTION WINS THE ONE SLOT THERE IS."""
        while True:
            try:
                self.asked.put_nowait(found)
                return
            except queue.Full:
                try:
                    self.asked.get_nowait()
                except queue.Empty:
                    continue
