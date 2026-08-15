"""SAY HIS NAME AND HE LISTENS, OR HOLD THE KEY AND HE LISTENS WITHOUT IT."""

import queue
import threading
import time

from ears import ending, engines
from ears.calling import addressed, phrases, spoken
from ears.ending import Heard
from ears.listening import POLL_SECONDS, Room
from face import show
from memory import settings

AFTER = "ears.after"
MORE = "ears.more"

DEAD = "{name} is handing over silence. Pick another microphone in Settings, Ears."

# HOW MANY TIMES ONE QUESTION MAY BE PICKED BACK UP. WITHOUT A CAP, SOMEBODY WHO
# ENDS EVERY BREATH ON "AND" IS NEVER ANSWERED AT ALL.
MOST_CARRIES = 3


class Waking:
    """THE ROOM, LISTENED TO, WITH THE PART MEANT FOR HAPPY HANDED ON."""

    def __init__(self, recorder, busy=None, key=None):
        self.recorder = recorder
        self.held = ending.Held()

        # THE KEY AND THE ROOM BOTH REACH FOR THE ONE DEVICE, NEVER AT THE SAME TIME.
        self.key = key
        self.mic = threading.Lock()

        self.room = Room(recorder, busy=busy, ousted=self.holding)

        # ONE QUESTION DEEP: TWO THINGS ASKED WHILE HE WAS THINKING MEANS THE
        # SECOND ONE IS WHAT WAS WANTED, NOT A BACKLOG TO WORK THROUGH.
        self.asked = queue.Queue(maxsize=1)

        self.silent = False
        self.running = True

        self.listener = threading.Thread(target=self.watching, daemon=True, name="waking")
        self.listener.start()

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
        self.room.close()

        if self.key:
            self.key.stop()

    def phrase(self):
        """EVERY NAME HE ANSWERS TO, IN WORDS, FOR A HINT SOMEBODY READS."""
        return spoken()

    def holding(self):
        """TRUE WHILE THE KEY IS DOWN."""
        return bool(self.key) and self.key.holding()

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
        self.room.drain()
        self.lapsed()
        self.deafness()
        self.recorder.refit()  # A DIFFERENT MICROPHONE WAS PICKED WHILE THE LAST TAKE RAN.

        # THE KEY IS ALREADY HOLDING THE DEVICE, AND WHAT IS BEING SAID INTO IT IS ITS TAKE.
        if self.holding():
            return

        if not self.room.begun():
            return

        # WHEN SOMEBODY STARTED TALKING, WHICH IS NOT WHEN WE FIND OUT WHAT THEY SAID.
        began = time.monotonic()

        with self.mic:
            where = self.room.taken()

        if where is None:  # A DOOR, A COUGH, ANYTHING BRIEFER THAN A WORD.
            return

        # THE KEY TOOK THE DEVICE PART WAY THROUGH. THIS IS THE FRONT OF WHAT IS BEING SAID
        # INTO THE KEY, AND READING IT WOULD ANSWER HALF A SENTENCE TWICE.
        if self.holding():
            where.unlink(missing_ok=True)
            return

        self.considered(where, began)

    def deafness(self):
        """A DEVICE HANDING OVER NOTHING IS NOT A QUIET ROOM, AND NOTHING ELSE HERE SAYS SO."""
        gone = self.recorder.deaf()

        if gone and not self.silent:
            show.trouble(DEAD.format(name=self.recorder.hearing()))

        self.silent = gone

    # ── THE KEY ──

    def pushing(self):
        """THE OTHER WAY IN, WATCHED ON ITS OWN THREAD BECAUSE THE ROOM'S LOOP BLOCKS."""
        moaned = None

        while self.running:
            try:
                self.key.refit()  # A DIFFERENT KEY WAS PICKED WHILE THE LAST TAKE RAN.
                self.key.reset()  # THE KEYBOARD FROM WHILE THAT TAKE WAS BEING READ.
                self.key.wait_press()

                if not self.running:
                    return

                # BEFORE THE LOCK, NEVER AFTER IT: THE FACE ANSWERS WHAT THE PERSON JUST DID,
                # AND THE ROOM MAY STILL BE A MOMENT LETTING GO OF THE DEVICE.
                show.listening()

                with self.mic:
                    self.pressed()

                moaned = None
            except Exception as error:
                if str(error) != moaned:
                    moaned = str(error)
                    show.trouble(f"Key: {moaned}")

                time.sleep(POLL_SECONDS)

    def pressed(self):
        """ONE PRESS: RECORD WHILE IT IS DOWN, AND HAND OVER WHATEVER WAS SAID INTO IT.

        NOTHING IS MATCHED AGAINST HIS NAME HERE. HOLDING THE KEY IS ALREADY SOMEBODY SAYING
        WHO THEY ARE TALKING TO, AND SAYING IT TWICE IS SAYING IT ONCE TOO OFTEN."""
        self.held.clear()  # A PRESS IS A NEW QUESTION, NOT THE REST OF THE LAST ONE.

        self.recorder.start()

        self.key.wait_release()

        where = self.recorder.stop()

        if where is None:  # THE KEY WAS BRUSHED, NOT HELD.
            show.idle()
            return

        started = time.perf_counter()
        text = (engines.transcribe(where) or "").strip()
        seconds = time.perf_counter() - started

        if not text or ending.nothing(text):
            where.unlink(missing_ok=True)
            show.idle()
            return

        self.remember(Heard(text=text, audio=where, seconds=seconds))

    # ── WHAT WAS HEARD ──

    def considered(self, where, began):
        """READ THE TAKE AND EITHER HAND IT ON, HOLD IT, OR FORGET IT."""
        started = time.perf_counter()
        text = engines.transcribe(where)
        seconds = time.perf_counter() - started

        wanted = self.meant(text, began)

        if wanted is None:  # SOMEBODY ELSE'S SENTENCE. HE WAS NEVER IN IT.
            where.unlink(missing_ok=True)
            return

        whole = ending.joined(self.held.text, wanted)

        if not whole or ending.nothing(whole):
            # HIS NAME AND NOTHING ELSE, OR NOTHING BUT THINKING NOISES. THE
            # QUESTION IS STILL COMING, SO WAIT FOR IT WITHOUT NEEDING THE NAME.
            self.waiting("", where, patience())
            return

        # STOPPING IS NOT FINISHING. A LINE THAT TRAILS OFF MID THOUGHT IS THE
        # FRONT OF A SENTENCE, AND ANSWERING IT NOW IS TALKING OVER SOMEBODY.
        if ending.unfinished(whole) and self.held.times < MOST_CARRIES:
            self.waiting(whole, where, carry_on(), seconds)
            return

        self.held.keep(where)
        self.remember(self.held.taken(whole, seconds))

    def meant(self, text, began):
        """WHAT WAS ASKED OF HAPPY IN THIS TAKE."""
        if not (text or "").strip():
            return None

        found = addressed(text, phrases())

        # ALREADY WOKEN, OR PART WAY THROUGH SAYING SOMETHING.
        if found is None and self.held.open(began):
            return text.strip()

        return found

    def waiting(self, whole, where, wait, seconds=None):
        self.held.hold(whole, where, wait, seconds)
        show.listening()

    def lapsed(self):
        """THE WAIT FOR THE REST OF A SENTENCE RAN OUT."""
        found = self.held.ran_out()

        if found is None:
            return

        if isinstance(found, Heard):
            self.remember(found)
            return

        show.idle()

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


def patience():
    return settings.get(AFTER)


def carry_on():
    return settings.get(MORE)
