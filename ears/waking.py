"""SAY HIS NAME AND HE LISTENS.

THE MICROPHONE IS NEVER OFF NOW, WHICH IS THE WHOLE POINT AND ALSO THE WHOLE
COST: EVERY RUN OF SOUND IN THE ROOM IS CAPTURED AND TRANSCRIBED, AND THEN
THROWN AWAY AGAIN UNLESS HIS NAME WAS IN IT. NOTHING LEAVES THIS MACHINE EITHER
WAY, AND A TAKE NOBODY WAS TALKING TO HIM IN IS DELETED RATHER THAN FILED.

THERE IS NO SECOND LITTLE WAKE WORD MODEL HERE ON PURPOSE. IT WOULD BE ONE MORE
THING TO DOWNLOAD AND ONE MORE THING TO BE WRONG ABOUT A LANGUAGE, AND THE
SPEECH MODEL THAT IS ALREADY LOADED AND ALREADY WARM READS THE NAME AS WELL AS
ANYTHING WOULD. SO LOUDNESS DECIDES WHERE AN UTTERANCE STARTS AND STOPS, AND THE
MODEL DECIDES WHOSE IT WAS.

WHILE HAPPY IS TALKING, NOTHING IS LISTENED TO. THE MICROPHONE HEARS THE
SPEAKERS, AND THE ALTERNATIVE IS HAPPY WAKING HIMSELF UP ON HIS OWN ANSWER AND
TRANSCRIBING IT BACK. THAT IS ALSO WHY CUTTING HIM OFF BY VOICE IS GONE: WITH NO
ECHO CANCELLING THERE IS NOTHING TO HEAR OVER HIM WITH. THE WINDOW HAS A STOP.
"""

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

# HOW CLOSE A MISHEARD WORD STILL COUNTS AS THAT WORD, AND HOW CLOSE THE LAST
# ONE HAS TO BE. THE PHRASE AS A WHOLE IS NOT WORTH SCORING: "MAKE ME HAPPY"
# LOOKS A LOT LIKE "HEY HAPPY" ADDED UP, AND NOBODY IN IT SAID HIS NAME.
EACH_CLOSE = 0.55
NAME_CLOSE = 0.8

# EVERY LANGUAGE'S WORDS, SO A PHRASE SOMEBODY SET IN THEIR OWN SCRIPT STILL
# SPLITS INTO ONES. WHAT IS DROPPED IS PUNCTUATION, WHICH IS ALL THAT MATTERS:
# WHISPER WRITES "HEY, HAPPY." AND NOBODY SAID A COMMA.
WORDS = re.compile(r"\w+", re.UNICODE)

# WHAT WAS ASKED, THE RECORDING IT WAS ASKED IN, AND WHAT THE HEARING COST.
Heard = collections.namedtuple("Heard", "text audio seconds")


class Waking:
    """THE ROOM, LISTENED TO, WITH THE PART MEANT FOR HAPPY HANDED ON.

    THE RECORDER IS DRIVEN AND NOT REPLACED: IT ALREADY KEEPS THE MOMENT BEFORE
    A TAKE BEGINS, WHICH MATTERS MORE HERE THAN IT EVER DID ON A KEY. LOUDNESS
    NOTICES A VOICE ONLY ONCE IT IS UNDER WAY, SO THE FIRST SYLLABLE OF EVERY
    UTTERANCE IS ALWAYS ALREADY PAST.
    """

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

        if not self.begun():
            return

        where = self.taken()

        if where is None:  # A DOOR, A COUGH, ANYTHING BRIEFER THAN A WORD.
            show.idle()
            return

        self.considered(where)

    def begun(self):
        """WAIT UNTIL SOMEBODY IS TALKING. FALSE MEANS ONLY THAT IT IS TIME TO LOOK
        AT running AGAIN."""
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
        """CAPTURE UNTIL THE TALKING STOPS. THE SAVED WAV, OR None IF IT WAS NOTHING."""
        show.listening()

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

    def considered(self, where):
        """READ THE TAKE AND EITHER HAND IT ON OR FORGET IT EVER HAPPENED."""
        started = time.perf_counter()
        text = engines.transcribe(where)
        seconds = time.perf_counter() - started

        wanted = self.meant(text)

        if wanted is None:
            where.unlink(missing_ok=True)
            show.idle()
            return

        if not wanted:  # HIS NAME AND NOTHING ELSE. THE QUESTION IS STILL COMING.
            self.open_until = time.monotonic() + patience()
            where.unlink(missing_ok=True)
            show.listening()
            return

        self.open_until = 0.0
        self.remember(Heard(text=wanted, audio=where, seconds=seconds))

    def meant(self, text):
        """WHAT WAS ASKED OF HAPPY IN THIS TAKE.

        None IS NOT HIS. "" IS HIS NAME WITH NOTHING AFTER IT, WHICH IS SOMEBODY
        ABOUT TO SAY THE REST. ANYTHING ELSE IS THE QUESTION.
        """
        if not (text or "").strip():
            return None

        found = addressed(text, self.phrase())

        # ALREADY WOKEN. HIS NAME IS WELCOME AGAIN BUT IS NO LONGER ASKED FOR, SO
        # A TAKE WITHOUT IT IS THE REST OF WHAT SOMEBODY WAS ALREADY SAYING.
        if found is None and time.monotonic() < self.open_until:
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
    """WHAT FOLLOWS HIS NAME IN THIS LINE, OR None WHEN HIS NAME IS NOT IN IT.

    THE NAME IS LOOKED FOR AS A RUN OF WORDS ANYWHERE, NOT ONLY AT THE FRONT, AND
    NOT LETTER FOR LETTER. "HEY HAPPY" COMES BACK AS "HEY, HAPPY", AS "HAY HAPPY"
    AND AS "HEY HAPPIE", AND ALL THREE OF THOSE ARE SOMEBODY SAYING HIS NAME.

    WHAT COMES BACK IS CUT OUT OF THE LINE AS IT WAS WRITTEN, PUNCTUATION AND ALL.
    THE WORDS ARE ONLY PULLED APART TO COMPARE THEM, AND "WHAT'S THE TIME" HANDED
    TO THE MODEL AS "WHAT S THE TIME" IS A WORSE QUESTION THAN IT WAS ASKED.
    """
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
    """WHETHER THIS RUN OF WORDS IS SOMEBODY SAYING THAT NAME.

    WORD BY WORD, AND THE LAST WORD STRICTEST OF ALL. THE FRONT OF A WAKE PHRASE
    IS A GREETING AND COMES BACK AS "HAY" OR "A" AS OFTEN AS AS "HEY"; THE END OF
    IT IS THE NAME, AND THE NAME IS THE ONLY PART THAT SAYS IT WAS MEANT FOR HIM.
    """
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
