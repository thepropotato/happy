"""THE ROOM AS SOUND: WHEN SOMEBODY STARTS TALKING, AND WHEN THEY STOP."""

import queue
import time

from ears.microphone import BLOCK_SIZE, SAMPLE_RATE, loudness
from memory import settings

LEVEL = "ears.level"
GAP = "ears.gap"

BLOCK_SECONDS = BLOCK_SIZE / SAMPLE_RATE

POLL_SECONDS = 0.2  # SHORT HOPS KEEP CTRL+C RESPONSIVE.

# A TELEVISION LEFT ON IS NOT AN UTTERANCE, AND NOBODY ASKS ANYTHING THIS LONG.
MOST_SECONDS = 20

# THE ROOM IS STILL RINGING WITH HIM FOR A MOMENT AFTER THE LAST CLIP STOPS.
AFTER_SPEAKING_SECONDS = 0.4


class Room:
    """EVERY BLOCK THE DEVICE HANDS OVER, TURNED INTO ONE TAKE AT A TIME."""

    def __init__(self, recorder, busy=None):
        self.recorder = recorder

        # TRUE WHILE HAPPY HIMSELF IS THE LOUDEST THING IN THE ROOM.
        self.busy = busy or (lambda: False)

        # THE SOUND AS IT ARRIVES. THE DEVICE'S OWN THREAD ONLY EVER PUTS.
        self.blocks = queue.Queue()

        self.deaf_until = 0.0  # NOTHING IS LISTENED TO BEFORE THIS MOMENT.
        self.running = True

        recorder.overhear(self.blocks.put)

    def close(self):
        self.running = False
        self.recorder.overhear(None)

    def begun(self):
        """WAIT UNTIL SOMEBODY IS TALKING."""
        for _ in range(int(POLL_SECONDS / BLOCK_SECONDS) or 1):
            if not self.running:
                return False

            block = self.block()

            if block is None:
                return False

            if self.ignoring():
                continue

            if loudness(block) >= floor():
                return True

        return False

    def taken(self):
        """CAPTURE UNTIL THE TALKING STOPS.

        THIS ENDS ON SILENCE ALONE, WHICH CANNOT TELL A PAUSE FOR BREATH FROM A
        FINISHED SENTENCE. SO IT IS KEPT SHORT AND WHAT THE TAKE TURNED OUT TO
        SAY DECIDES WHETHER TO GO ROUND AGAIN — SEE ears.ending."""
        self.recorder.start()

        began = time.monotonic()
        silence = 0.0
        gap = hush()

        while self.running:
            block = self.block()

            # NO SOUND ARRIVING AT ALL IS THE QUIETEST THE ROOM GETS.
            if block is None or loudness(block) < floor():
                silence += BLOCK_SECONDS

                if silence >= gap:
                    break
            else:
                silence = 0.0

            if time.monotonic() - began >= MOST_SECONDS:
                break

        return self.recorder.stop()

    def block(self):
        try:
            return self.blocks.get(timeout=BLOCK_SECONDS * 2)
        except queue.Empty:
            return None

    def drain(self):
        """THE ROOM FROM WHILE HAPPY WAS BUSY. NONE OF IT WAS EVER LISTENED TO."""
        while True:
            try:
                self.blocks.get_nowait()
            except queue.Empty:
                return

    def ignoring(self):
        """TRUE WHILE THE ONLY THING WORTH HEARING WOULD BE HAPPY HIMSELF."""
        if self.busy():
            self.deaf_until = time.monotonic() + AFTER_SPEAKING_SECONDS

            return True

        return time.monotonic() < self.deaf_until


def floor():
    return settings.get(LEVEL)


def hush():
    return settings.get(GAP)
