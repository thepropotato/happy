"""SAYS WHAT HAPPY WRITES, A SENTENCE BEHIND HIM.

TWO THREADS BEHIND ONE QUEUE EACH: ONE TURNS SENTENCES INTO SOUND, THE OTHER
PLAYS IT. SENTENCE THREE IS BEING MADE WHILE SENTENCE TWO IS STILL IN THE AIR.

BARGE IN IS stop(). A PERSON WHO STARTS TALKING HAS STOPPED LISTENING.
"""

import queue
import threading

import numpy as np
import sounddevice as sd

from face import show
from memory import settings
from voice.piper import Voice
from voice.sentences import Sentences

IDLE_POLL_SECONDS = 0.1  # SHORT HOPS SO CTRL+C STILL LANDS WHILE WAITING.

# HOW FINELY THE SHAPE OF A CLIP IS MEASURED FOR WHATEVER IS DRAWING IT.
ENVELOPE_MS = 40


class Speaker:
    def __init__(self, voice=None):
        self.voice = voice or Voice()
        self.pieces = Sentences()

        self.sentences = queue.Queue()
        self.clips = queue.Queue()

        # BUMPED BY stop(). WORK STAMPED WITH AN OLDER ONE IS THROWN AWAY, WHICH
        # CANCELS A SENTENCE ALREADY HALFWAY THROUGH SYNTHESIS.
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
        """SPEAK A STREAM, HANDING EACH PIECE BACK SO IT CAN BE PRINTED TOO."""
        try:
            for piece in pieces:
                self.feed(piece)

                yield piece
        finally:
            self.flush()  # AN ANSWER CUT SHORT STILL SAYS WHAT IT HAD.

    def feed(self, piece):
        for sentence in self.pieces.feed(piece):
            self.send(sentence)

    def flush(self):
        for sentence in self.pieces.flush():
            self.send(sentence)

    def stop(self):
        """BARGE IN. DROP EVERYTHING QUEUED AND CUT WHAT IS PLAYING."""
        self.era += 1
        self.pieces.clear()

        empty(self.sentences)
        empty(self.clips)
        sd.stop()
        show.hush()

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
        if settings.get("voice.muted"):  # HAPPY STILL ANSWERS, HE JUST WRITES IT.
            return

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
                show.envelope(shape(samples, self.voice.rate), len(samples) / self.voice.rate)
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


def shape(samples, rate):
    """A CLIP AS A HANDFUL OF LOUDNESSES, ONE PER SLICE, FOR DRAWING."""
    step = max(1, int(rate * ENVELOPE_MS / 1000))
    slices = len(samples) // step

    if not slices:
        return []

    blocks = np.abs(samples[: slices * step]).reshape(slices, step).mean(axis=1)

    return [round(float(value), 3) for value in blocks]


def empty(waiting):
    while True:
        try:
            waiting.get_nowait()
        except queue.Empty:
            return
