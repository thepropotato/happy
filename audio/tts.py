"""
SPEAKING. THE REPLY ARRIVES IN PIECES, SO IT IS SAID IN SENTENCES.

WAITING FOR THE WHOLE ANSWER BEFORE MAKING A SOUND WOULD ADD THE WHOLE OF THE
MODEL'S THINKING TO THE SILENCE. SO PIECES ARE GATHERED UNTIL A SENTENCE ENDS,
AND THAT SENTENCE GOES OFF TO BE SPOKEN WHILE THE NEXT ONE IS STILL BEING
WRITTEN.

TWO THREADS BEHIND ONE QUEUE EACH. ONE TURNS SENTENCES INTO SOUND, THE OTHER
PLAYS IT. THEY ARE SEPARATE SO SENTENCE THREE IS BEING MADE WHILE SENTENCE TWO
IS STILL IN THE AIR, WHICH IS THE DIFFERENCE BETWEEN SPEECH AND STAMMERING ON A
VOICE THAT RUNS NEAR REAL TIME.

BARGE IN IS stop(). EVERYTHING QUEUED IS DROPPED AND WHATEVER IS PLAYING IS CUT,
BECAUSE A PERSON WHO STARTS TALKING HAS STOPPED LISTENING.

THE VOICE IS PIPER: A SMALL ONNX MODEL, SIXTY MEGABYTES, THAT ANSWERS IN UNDER
TWENTY MILLISECONDS AND RUNS FIFTY TIMES FASTER THAN REAL TIME. IT SOUNDS LESS
LIKE A PERSON THAN THE HEAVIER OPTIONS AND THAT IS THE TRADE, TAKEN ON PURPOSE:
A REPLY THAT STARTS AT ONCE AND KEEPS UP READS AS SOMEONE WHO KNOWS THE ANSWER,
AND ONE THAT DRAGS READS AS SOMEONE WHO DOES NOT, WHATEVER THE TIMBRE.

PHONEMES COME FROM AN ESPEAK-NG THAT SHIPS INSIDE THE PACKAGE, SO THERE IS
NOTHING TO INSTALL BESIDE THE VOICE FILE AND IT WORKS THE SAME ON WINDOWS.

GET A VOICE:
    python -m piper.download_voices en_US-hfc_male-medium --download-dir models/piper
"""

import queue
import re
import threading
from pathlib import Path

import numpy as np
import sounddevice as sd

MODELS = Path(__file__).resolve().parent.parent / "models" / "piper"
SUFFIX = "*.onnx"

# WHICH FILE, WHEN THERE IS MORE THAN ONE. EMPTY MEANS TAKE WHATEVER IS THERE.
VOICE = ""

# BELOW ONE IS FASTER SPEECH. A SHADE BRISK READS AS SOMEONE WITH THE ANSWER
# ALREADY IN HAND, WHICH IS THE WHOLE POINT OF PICKING THIS ONE.
LENGTH_SCALE = 0.95

RATE = 22050  # ONLY THE FALLBACK'S. A REAL VOICE REPORTS ITS OWN.

GET_THEM = (
    f"No voice in {MODELS}. Get one with:\n"
    "  python -m piper.download_voices en_US-hfc_male-medium --download-dir models/piper"
)

# A SENTENCE ENDS AT A FULL STOP FOLLOWED BY SPACE, OR AT A LINE BREAK. THE
# SPACE MATTERS: IT KEEPS "3.5" AND "8.30" IN ONE PIECE.
ENDINGS = re.compile(r"(?<=[.!?])[\"')\]]*\s+|\n+")

# TOO SHORT AND EVERY FRAGMENT GETS ITS OWN BREATH, WHICH SOUNDS CLIPPED. SO A
# SHORT SENTENCE WAITS AND GOES OUT JOINED TO THE ONE AFTER IT.
MIN_CHARS = 24

# EXCEPT THE FIRST ONE OF A REPLY, WHICH IS THE ONLY ONE ANYONE IS WAITING ON.
# "DONE." SAID NOW BEATS A SMOOTHER PARAGRAPH SAID IN A SECOND'S TIME.
MIN_CHARS_FIRST = 4

# A FULL STOP AFTER ONE OF THESE IS PART OF THE WORD, NOT THE END OF A SENTENCE.
# WITHOUT THIS, "MR. STARK IS ON THE PHONE" IS SAID AS TWO BROKEN HALVES, AND
# THE SHORT FLOOR ABOVE MAKES THAT LIKELY RATHER THAN RARE.
SHORTENED = {
    "mr", "mrs", "ms", "dr", "prof", "st", "jr", "sr", "vs", "etc", "eg", "ie",
    "no", "approx", "inc", "ltd", "co", "dept", "fig", "al", "am", "pm",
}

# AN INITIAL, AS IN "J. JONAH JAMESON". ONE LETTER AND A DOT IS NEVER A SENTENCE.
INITIAL = 1

# THE WORD IMMEDIATELY BEFORE A CANDIDATE FULL STOP.
BEFORE = re.compile(r"([A-Za-z]+)\.[\"')\]]*\s*$")

# AND A SENTENCE THAT NEVER ENDS MUST NOT HOLD UP THE SOUND FOREVER.
MAX_CHARS = 260

IDLE_POLL_SECONDS = 0.1  # SHORT HOPS SO CTRL+C STILL LANDS WHILE WAITING.


class Voice:
    """SENTENCES IN, SOUND OUT. THE ONLY PART THAT KNOWS WHAT A MODEL IS."""

    def __init__(self, path=None, length=LENGTH_SCALE):
        from piper import PiperVoice, SynthesisConfig

        self.path = path or find()
        self.voice = PiperVoice.load(self.path)
        self.rate = self.voice.config.sample_rate
        self.how = SynthesisConfig(length_scale=length)

    def say(self, text):
        # ONE SENTENCE COMES BACK IN A HANDFUL OF CHUNKS. THE PLAYER WANTS ONE.
        parts = [chunk.audio_float_array for chunk in self.voice.synthesize(text, self.how)]

        return np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)

    def warm(self):
        """SYNTHESISE ONCE NOW. THE FIRST CALL COSTS THIRTY TIMES THE REST."""
        self.say("Ready.")


def whole(path):
    """A VOICE IS TWO FILES. HALF A DOWNLOAD IS NOT A VOICE."""
    return path.exists() and path.with_suffix(".onnx.json").exists()


def find():
    """THE VOICE FILE, OR A COMPLAINT SAYING HOW TO GET ONE."""
    if VOICE:
        chosen = MODELS / f"{VOICE}.onnx"

        if not whole(chosen):
            raise VoiceError(f"No complete voice at {chosen}.\n{GET_THEM}")

        return chosen

    found = [path for path in sorted(MODELS.glob(SUFFIX)) if whole(path)] if MODELS.is_dir() else []

    if not found:
        raise VoiceError(GET_THEM)

    return found[0]


class Mute:
    """STANDS IN WHEN THE VOICE WILL NOT LOAD, SO NOTHING ELSE NEEDS AN IF."""

    rate = RATE

    def say(self, text):
        return np.zeros(0, dtype=np.float32)

    def warm(self):
        pass


class VoiceError(Exception):
    pass


class Speaker:
    """SAYS WHAT HAPPY WRITES, A SENTENCE BEHIND HIM."""

    def __init__(self, voice=None):
        self.voice = voice or Voice()
        self.buffer = ""
        self.started = False  # HAS THIS REPLY MADE A SOUND YET.

        self.sentences = queue.Queue()
        self.clips = queue.Queue()

        # BUMPED BY stop(). WORK STAMPED WITH AN OLDER ONE IS THROWN AWAY, WHICH
        # IS HOW A SENTENCE ALREADY HALFWAY THROUGH SYNTHESIS GETS CANCELLED.
        self.era = 0

        self.pending = 0
        self.quiet = threading.Condition()
        self.running = True

        self.workers = [
            threading.Thread(target=self.synthesise, daemon=True),
            threading.Thread(target=self.play, daemon=True),
        ]

        for worker in self.workers:
            worker.start()

    def warm(self):
        self.voice.warm()

    def say(self, pieces):
        """SPEAK A STREAM OF PIECES, HANDING EACH ONE BACK SO IT CAN BE PRINTED TOO."""
        try:
            for piece in pieces:
                self.feed(piece)

                yield piece
        finally:
            self.flush()  # AN ANSWER CUT SHORT BY AN ERROR STILL SAYS WHAT IT HAD.

    def feed(self, piece):
        """TAKE A PIECE OF THE REPLY. WHOLE SENTENCES LEAVE, THE REST WAITS."""
        self.buffer += piece

        while True:
            cut = self.edge()

            if cut is None:
                return

            head, self.buffer = self.buffer[:cut].strip(), self.buffer[cut:]

            if head:
                self.send(head)

    def flush(self):
        """SAY WHATEVER IS LEFT, EVEN WITHOUT A FULL STOP ON THE END."""
        rest, self.buffer = self.buffer.strip(), ""

        if rest:
            self.send(rest)

        self.started = False  # THE NEXT REPLY GETS ITS QUICK FIRST SENTENCE AGAIN.

    def edge(self):
        """WHERE THE NEXT THING WORTH SAYING ENDS, OR None IF IT HAS NOT YET."""
        least = MIN_CHARS if self.started else MIN_CHARS_FIRST

        for found in ENDINGS.finditer(self.buffer):
            if found.end() >= least and not self.shortened(found.end()):
                return found.end()

        if len(self.buffer) < MAX_CHARS:
            return None

        space = self.buffer.rfind(" ", 0, MAX_CHARS)  # NEVER CUT A WORD IN HALF.

        return space + 1 if space > 0 else MAX_CHARS

    def shortened(self, at):
        """TRUE WHEN THE FULL STOP ENDING AT at BELONGS TO A WORD, NOT A SENTENCE."""
        word = BEFORE.search(self.buffer[:at])

        if not word:
            return False

        return len(word.group(1)) == INITIAL or word.group(1).lower() in SHORTENED

    def stop(self):
        """BARGE IN. DROP EVERYTHING QUEUED AND CUT WHAT IS PLAYING."""
        self.era += 1
        self.buffer = ""
        self.started = False

        empty(self.sentences)
        empty(self.clips)
        sd.stop()

        with self.quiet:
            self.pending = 0
            self.quiet.notify_all()

    def wait(self):
        """BLOCK UNTIL HAPPY HAS FINISHED TALKING."""
        with self.quiet:
            while self.pending > 0:
                self.quiet.wait(IDLE_POLL_SECONDS)

    def talking(self):
        return self.pending > 0

    def close(self):
        self.running = False
        self.stop()

        self.sentences.put((self.era, None))
        self.clips.put((self.era, None))

    def send(self, sentence):
        self.started = True

        with self.quiet:
            self.pending += 1

        self.sentences.put((self.era, sentence))

    def synthesise(self):
        """SENTENCES INTO SOUND, ONE AHEAD OF WHAT IS PLAYING."""
        while self.running:
            era, sentence = self.sentences.get()

            if sentence is None:
                return

            if era != self.era:  # BARGED IN ON WHILE IT SAT IN THE QUEUE.
                self.settle()
                continue

            try:
                samples = self.voice.say(sentence)
            except Exception as error:  # A BAD SENTENCE MUST NOT END THE SESSION.
                print(f"\n[voice] {error}")
                self.settle()
                continue

            self.clips.put((era, samples))

    def play(self):
        while self.running:
            era, samples = self.clips.get()

            if samples is None:
                return

            if era != self.era or not len(samples):
                self.settle()
                continue

            try:
                sd.play(samples, self.voice.rate)
                sd.wait()  # RETURNS EARLY WHEN stop() CUTS IT.
            except Exception as error:
                print(f"\n[speaker] {error}")
            finally:
                self.settle()

    def settle(self):
        with self.quiet:
            self.pending = max(0, self.pending - 1)

            if self.pending == 0:
                self.quiet.notify_all()


def empty(waiting):
    while True:
        try:
            waiting.get_nowait()
        except queue.Empty:
            return


def create(**kwargs):
    """A SPEAKER, PLUS THE REASON IT IS MUTE WHEN IT IS.

    CATCHES EVERYTHING ON PURPOSE. A HALF DOWNLOADED MODEL FAILS SOMEWHERE DEEP
    INSIDE A RUNTIME WE DO NOT CONTROL, AND LOSING THE VOICE IS NOT A REASON TO
    LOSE THE ASSISTANT. HAPPY GOES BACK TO ANSWERING IN WRITING.
    """
    try:
        return Speaker(Voice(**kwargs)), None
    except Exception as error:
        return Speaker(Mute()), f"{error}"


if __name__ == "__main__":  # HEAR IT WITHOUT THE REST OF HAPPY ATTACHED.
    import sys

    if "--voices" in sys.argv:
        print("\n".join(str(p.stem) for p in sorted(MODELS.glob(SUFFIX))) or GET_THEM)
        raise SystemExit

    words = " ".join(sys.argv[1:]) or (
        "Right, I opened your downloads folder. There are forty one things in it, "
        "and eleven of them are called screenshot. You might want to look at that."
    )

    speaker, why = create()

    if why:
        print(why)

    # FED A WORD AT A TIME, THE WAY THE MODEL ACTUALLY DELIVERS AN ANSWER.
    for word in speaker.say(part + " " for part in words.split(" ")):
        print(word, end="", flush=True)

    print()
    speaker.wait()
    speaker.close()
