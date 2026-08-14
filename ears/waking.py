"""SAY HIS NAME AND HE LISTENS."""

import collections
import difflib
import queue
import re
import threading
import time

from ears import engines
from ears.microphone import BLOCK_SIZE, SAMPLE_RATE, loudness
from face import show
from memory import settings

PHRASE = "ears.wake"
LEVEL = "ears.level"
GAP = "ears.gap"
AFTER = "ears.after"

FALLBACK = "hey happy"

BLOCK_SECONDS = BLOCK_SIZE / SAMPLE_RATE

POLL_SECONDS = 0.2  # SHORT HOPS KEEP CTRL+C RESPONSIVE.

# A TELEVISION LEFT ON IS NOT AN UTTERANCE, AND NOBODY ASKS ANYTHING THIS LONG.
MOST_SECONDS = 20

# THE ROOM IS STILL RINGING WITH HIM FOR A MOMENT AFTER THE LAST CLIP STOPS.
AFTER_SPEAKING_SECONDS = 0.4

# HOW CLOSE A MISHEARD WORD STILL COUNTS AS THAT WORD, AND HOW CLOSE THE LAST ONE HAS TO BE.
EACH_CLOSE = 0.55
NAME_CLOSE = 0.8

# EVERY LANGUAGE'S WORDS, SO A PHRASE SOMEBODY SET IN THEIR OWN SCRIPT STILL SPLITS INTO
# ONES.
WORDS = re.compile(r"\w+", re.UNICODE)

# WHAT WAS ASKED, THE RECORDING IT WAS ASKED IN, AND WHAT THE HEARING COST.
Heard = collections.namedtuple("Heard", "text audio seconds")


class Waking:
    """THE ROOM, LISTENED TO, WITH THE PART MEANT FOR HAPPY HANDED ON."""

    def __init__(self, recorder, busy=None):
        self.recorder = recorder

        # TRUE WHILE HAPPY HIMSELF IS THE LOUDEST THING IN THE ROOM.
        self.busy = busy or (lambda: False)

        # THE SOUND AS IT ARRIVES. THE DEVICE'S OWN THREAD ONLY EVER PUTS.
        self.blocks = queue.Queue()

        # ONE QUESTION DEEP: TWO THINGS ASKED WHILE HE WAS THINKING MEANS THE
        # SECOND ONE IS WHAT WAS WANTED, NOT A BACKLOG TO WORK THROUGH.
        self.asked = queue.Queue(maxsize=1)

        self.deaf_until = 0.0  # NOTHING IS LISTENED TO BEFORE THIS MOMENT.
        self.open_until = 0.0  # HIS NAME LANDED BARE; UNTIL THIS, ANY TAKE IS THE QUESTION.
        self.running = True

        recorder.overhear(self.blocks.put)

        self.listener = threading.Thread(target=self.watching, daemon=True, name="waking")
        self.listener.start()

    def phrase(self):
        return (settings.get(PHRASE) or FALLBACK).strip() or FALLBACK

    def next(self):
        """THE NEXT THING ASKED OF HAPPY, OR None SO THE CALLER CAN DRAW BREATH."""
        try:
            return self.asked.get(timeout=POLL_SECONDS)
        except queue.Empty:
            return None

    def stop(self):
        self.running = False
        self.recorder.overhear(None)

    # ── THE LOOP ──

    def watching(self):
        moaned = None

        while self.running:
            try:
                self.round()
                moaned = None
            except Exception as error:
                # ONCE PER REASON: A MICROPHONE THAT HAS GONE IS GONE EVERY LAP.
                if str(error) != moaned:
                    moaned = str(error)
                    show.trouble(f"Ears: {moaned}")

                time.sleep(POLL_SECONDS)

    def round(self):
        """ONE UTTERANCE: WAIT FOR IT, KEEP IT, READ IT, DECIDE WHOSE IT WAS."""
        self.drain()
        self.lapsed()

        if not self.begun():
            return

        # WHEN SOMEBODY STARTED TALKING, WHICH IS NOT WHEN WE FIND OUT WHAT THEY SAID.
        began = time.monotonic()

        where = self.taken()

        if where is None:  # A DOOR, A COUGH, ANYTHING BRIEFER THAN A WORD.
            return

        self.considered(where, began)

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
        """CAPTURE UNTIL THE TALKING STOPS."""
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

    def considered(self, where, began):
        """READ THE TAKE AND EITHER HAND IT ON OR FORGET IT EVER HAPPENED."""
        started = time.perf_counter()
        text = engines.transcribe(where)
        seconds = time.perf_counter() - started

        wanted = self.meant(text, began)

        if wanted is None:  # SOMEBODY ELSE'S SENTENCE. HE WAS NEVER IN IT.
            where.unlink(missing_ok=True)
            return

        if not wanted:  # HIS NAME AND NOTHING ELSE. THE QUESTION IS STILL COMING.
            self.open_until = time.monotonic() + patience()
            where.unlink(missing_ok=True)
            show.listening()
            return

        self.open_until = 0.0
        self.remember(Heard(text=wanted, audio=where, seconds=seconds))

    def lapsed(self):
        """THE WAIT FOR THE REST OF A SENTENCE RAN OUT."""
        if not self.open_until or time.monotonic() < self.open_until:
            return

        self.open_until = 0.0

        show.idle()

    def meant(self, text, began):
        """WHAT WAS ASKED OF HAPPY IN THIS TAKE."""
        if not (text or "").strip():
            return None

        found = addressed(text, self.phrase())

        # ALREADY WOKEN.
        if found is None and began < self.open_until:
            return text.strip()

        return found

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

    # ── THE SOUND ITSELF ──

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


def addressed(text, phrase):
    """WHAT FOLLOWS HIS NAME IN THIS LINE, OR None WHEN HIS NAME IS NOT IN IT."""
    found = list(WORDS.finditer(text or ""))
    wanted = split(phrase)

    if not found or not wanted or len(found) < len(wanted):
        return None

    for at in range(len(found) - len(wanted) + 1):
        run = [each.group().lower() for each in found[at : at + len(wanted)]]

        if says(run, wanted):
            # ONLY OFF THE FRONT: THE QUESTION MARK AT THE END IS PART OF THE QUESTION.
            return text[found[at + len(wanted) - 1].end() :].lstrip(" ,.!?:;-").strip()

    return None


def says(run, wanted):
    """WHETHER THIS RUN OF WORDS IS SOMEBODY SAYING THAT NAME."""
    if run == wanted:
        return True

    last = len(wanted) - 1

    for at, (said, word) in enumerate(zip(run, wanted)):
        if near(said, word) < (NAME_CLOSE if at == last else EACH_CLOSE):
            return False

    return True


def near(said, name):
    return difflib.SequenceMatcher(None, said, name).ratio()


def split(text):
    return WORDS.findall((text or "").lower())


def floor():
    return settings.get(LEVEL)


def hush():
    return settings.get(GAP)


def patience():
    return settings.get(AFTER)
