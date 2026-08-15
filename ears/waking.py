"""SAY HIS NAME AND HE LISTENS."""

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

# HOW MANY TIMES ONE QUESTION MAY BE PICKED BACK UP. WITHOUT A CAP, SOMEBODY WHO
# ENDS EVERY BREATH ON "AND" IS NEVER ANSWERED AT ALL.
MOST_CARRIES = 3


class Waking:
    """THE ROOM, LISTENED TO, WITH THE PART MEANT FOR HAPPY HANDED ON."""

    def __init__(self, recorder, busy=None):
        self.room = Room(recorder, busy=busy)
        self.held = ending.Held()

        # ONE QUESTION DEEP: TWO THINGS ASKED WHILE HE WAS THINKING MEANS THE
        # SECOND ONE IS WHAT WAS WANTED, NOT A BACKLOG TO WORK THROUGH.
        self.asked = queue.Queue(maxsize=1)

        self.running = True

        self.listener = threading.Thread(target=self.watching, daemon=True, name="waking")
        self.listener.start()

    def next(self):
        """THE NEXT THING ASKED OF HAPPY, OR None SO THE CALLER CAN DRAW BREATH."""
        try:
            return self.asked.get(timeout=POLL_SECONDS)
        except queue.Empty:
            return None

    def stop(self):
        self.running = False
        self.room.close()

    def phrase(self):
        """EVERY NAME HE ANSWERS TO, IN WORDS, FOR A HINT SOMEBODY READS."""
        return spoken()

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

        if not self.room.begun():
            return

        # WHEN SOMEBODY STARTED TALKING, WHICH IS NOT WHEN WE FIND OUT WHAT THEY SAID.
        began = time.monotonic()

        where = self.room.taken()

        if where is None:  # A DOOR, A COUGH, ANYTHING BRIEFER THAN A WORD.
            return

        self.considered(where, began)

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
