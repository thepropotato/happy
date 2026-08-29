"""SAYS WHAT HAPPY WRITES, A SENTENCE BEHIND HIM."""

import queue
import threading

import numpy as np
import sounddevice as sd

from face import show
from memory import settings
from voice import clips, engines, numbers, stripping
from voice.sentences import Sentences

IDLE_POLL_SECONDS = 0.1  # SHORT HOPS SO CTRL+C STILL LANDS WHILE WAITING.

# HOW MUCH SOUND GOES INTO THE DEVICE AT ONCE, WHICH IS ALSO HOW LONG BARGING IN CAN TAKE.
BLOCK_MS = 60

ENVELOPE_MS = 40

CHANNELS = 1


class Speaker:
    def __init__(self, voice=None):
        self.voice = voice or engines.build()
        self.engine = engines.chosen()
        self.pieces = Sentences()

        # THE LAST VOICE HEARD BEFORE ANYBODY PICKED IT, AS (NAME, VOICE).
        self.heard = None

        self.sentences = queue.Queue()
        self.clips = queue.Queue()

        # BUMPED BY stop(). WORK STAMPED WITH AN OLDER ONE IS THROWN AWAY.
        self.era = 0

        # EVERY SENTENCE HANDED OVER AND EVERY PIECE MADE OF IT, UNTIL EACH HAS BEEN PLAYED.
        # THE SENTENCE HOLDS ONE OF ITS OWN SO THE COUNT CANNOT REACH NOUGHT BETWEEN PIECES.
        self.pending = 0
        self.quiet = threading.Condition()

        # THE OUTPUT DEVICE'S OWN LIFECYCLE. BARGING IN REACHES FOR IT FROM WHICHEVER THREAD
        # THE PERSON WAS ON, AND COREAUDIO THROWS IF THAT LANDS WHILE A CLIP IS BEING SET UP.
        self.device = threading.Lock()

        # HELD OPEN BETWEEN CLIPS, WHICH IS WHERE AN EIGHTH OF A SECOND PER PIECE USED TO GO.
        self.stream = None

        self.running = True

        self.workers = [
            threading.Thread(target=self.synthesise, daemon=True),
            threading.Thread(target=self.play, daemon=True),
        ]

        for worker in self.workers:
            worker.start()

    def warm(self):
        self.voice.warm()

    def refit(self):
        """A DIFFERENT ENGINE WAS PICKED. A VOICE IS REPLACED, NOT RETUNED."""
        if engines.chosen() == self.engine:
            return

        self.engine = engines.chosen()
        self.voice, why = engines.attempt()

        if why:
            show.trouble(why)

        self.voice.warm()

    def say(self, pieces):
        """SPEAK A STREAM, HANDING EACH PIECE BACK SO IT CAN BE PRINTED TOO."""
        try:
            for piece in pieces:
                self.feed(piece)

                yield piece
        finally:
            self.flush()

    def feed(self, piece):
        for sentence in self.pieces.feed(piece):
            self.send(sentence)

    def flush(self):
        for sentence in self.pieces.flush():
            self.send(sentence)

    def stop(self):
        """BARGE IN. DROP EVERYTHING QUEUED AND CUT WHAT IS PLAYING."""
        # THE ERA AND THE COUNT MOVE TOGETHER: A SENTENCE ARRIVING AT THIS MOMENT IS EITHER
        # WHOLLY BEFORE THE BARGE, AND DROPPED WITH THE REST, OR WHOLLY AFTER IT AND COUNTED.
        with self.quiet:
            self.era += 1
            self.pending = 0
            self.quiet.notify_all()

        self.pieces.clear()

        empty(self.sentences)
        empty(self.clips)

        with self.device:
            self.cut()

        show.hush()

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

        self.sentences.put((self.era, None, None))
        self.clips.put((self.era, None, None))

        with self.device:
            self.shut()

    def send(self, sentence):
        if settings.get("voice.muted"):
            return

        self.sample(sentence)

    def sample(self, sentence, name=None):
        """A LINE SAID BECAUSE SOMEBODY ASKED TO HEAR IT, WHICH MUTE HAS NOTHING TO SAY ABOUT:
        MUTE IS ABOUT ANSWERS, AND A BUTTON PRESSED TO LISTEN THAT STAYS SILENT READS AS BROKEN.
        A NAME SAYS WHICH VOICE, WHICH IS HOW ONE IS HEARD BEFORE IT IS PICKED."""
        # THE PANEL DRAWS THE MARKDOWN. NOTHING OUT HERE SHOULD HEAR IT.
        sentence = stripping.spoken(sentence)

        # A FIGURE IS SAID AS THE WORDS IT IS READ AS, WHICH NO VOICE MODEL DOES ON ITS OWN.
        sentence = numbers.spoken(sentence)

        if not sentence:
            return

        # THE ERA IS READ WHERE IT IS COUNTED, SO THE SENTENCE IS NEVER STAMPED WITH ONE ERA
        # AND COUNTED AGAINST ANOTHER.
        with self.quiet:
            era = self.era
            self.pending += 1

        self.sentences.put((era, sentence, name))

    def pinned(self, name):
        """ONE VOICE OFF THE LIST, HELD TO ITS NAME WHATEVER THE SETTING SAYS, AND KEPT SO THAT
        AUDITIONING THE SAME ONE TWICE LOADS IT ONCE."""
        if not self.heard or self.heard[0] != name:
            self.heard = (name, engines.pinned(name))

        return self.heard[1]

    def synthesise(self):
        """SENTENCES INTO SOUND, ONE AHEAD OF WHAT IS PLAYING."""
        while self.running:
            era, sentence, name = self.sentences.get()

            if sentence is None:
                return

            if era != self.era:  # BARGED IN ON WHILE IT SAT IN THE QUEUE.
                self.settle(era)
                continue

            try:
                voice = self.pinned(name) if name else self.voice
            except Exception as error:
                print(f"\n[voice] {error}")
                self.settle(era)

                continue

            # THE RATE TRAVELS WITH THE CLIP: A PINNED VOICE IS NOT ALWAYS THE ONE THAT IS SET,
            # AND TWO VOICES DO NOT ALWAYS RUN AT THE SAME RATE.
            self.pour(era, voice.stream(sentence), voice.rate)

    def pour(self, era, pieces, rate):
        """A SENTENCE'S PIECES ONTO THE QUEUE THE MOMENT EACH IS MADE, SO THE FIRST IS ALREADY
        PLAYING WHILE THE LAST IS STILL BEING SYNTHESISED.

        EACH PIECE TAKES A COUNT OF ITS OWN AND THE SENTENCE KEEPS ITS ONE UNTIL THERE ARE NO
        MORE PIECES, WHICH IS WHAT STOPS HAPPY FROM READING AS FINISHED IN THE GAP BETWEEN A
        PIECE PLAYING OUT AND THE NEXT ONE EXISTING."""
        out = native(rate)

        try:
            for samples in pieces:
                if not len(samples):
                    continue

                # PUT TO THE DEVICE'S RATE HERE RATHER THAN ON THE WAY OUT: THE THREAD THAT
                # PLAYS HAS A PIECE ALREADY RUNNING, AND ANYTHING IT STOPS TO DO IS A GAP.
                ready = clips.resampled(samples, rate, out)

                with self.quiet:
                    if era != self.era:  # BARGED IN ON PART WAY THROUGH SAYING IT.
                        return

                    self.pending += 1

                self.clips.put((era, ready, out))
        except Exception as error:  # A VOICE THAT GAVE UP HALF A SENTENCE IN.
            print(f"\n[voice] {error}")
        finally:
            self.settle(era)  # THE SENTENCE ITSELF, WHICH HAS NOW BEEN WHOLLY HANDED OVER.

    def play(self):
        while self.running:
            era, samples, rate = self.clips.get()

            if samples is None:
                return

            try:
                if era == self.era and len(samples):
                    show.envelope(levels(samples, rate), len(samples) / rate)
                    self.sound(samples, rate, era)
            except Exception as error:
                print(f"\n[speaker] {error}")
            finally:
                self.settle(era)
                self.rest()

    def sound(self, samples, rate, era):
        """ONE CLIP INTO THE DEVICE, A BLOCK AT A TIME.

        NOT sd.play(): THAT BUILDS A WHOLE STREAM PER CLIP, WHICH IS AN EIGHTH OF A SECOND OF
        SILENCE BEFORE EVERY PIECE AND MORE THAN A SECOND WHEN COREAUDIO HAS LET THE DEVICE
        SLEEP. ONE STREAM IS KEPT INSTEAD AND WRITTEN INTO, WHICH BLOCKS FOR THE LENGTH OF THE
        SOUND WITHOUT SITTING INSIDE PORTAUDIO FOR IT: THE LOCK IS LET GO BETWEEN BLOCKS, SO
        BARGING IN LANDS WITHIN ONE OF THEM RATHER THAN AT THE END OF THE CLIP."""
        step = max(1, int(rate * BLOCK_MS / 1000))
        samples = np.ascontiguousarray(samples, dtype=np.float32).reshape(-1, CHANNELS)

        for at in range(0, len(samples), step):
            # UNDER THE LOCK, BECAUSE CLOSING TAKES IT TOO AND A CHECK MADE OUTSIDE IT CAN BE
            # OVERTAKEN BY ONE, LEAVING A FRESH STREAM OPENED BEHIND A SHUT DEVICE.
            with self.device:
                if not self.running or era != self.era:
                    return

                self.opened(rate).write(samples[at : at + step])

    def opened(self, rate):
        """THE OUTPUT DEVICE, HELD OPEN BETWEEN CLIPS AND REBUILT ONLY IF THE RATE MOVES.

        THE DEVICE ITSELF CAN VANISH FROM UNDER A HELD STREAM: AIRPODS DROPPING OR THE OUTPUT
        SWITCHING LEAVES A STREAM THAT STILL LOOKS OPEN BUT THROWS ON start(). A FRESH STREAM
        COVERS THAT, BUT PORTAUDIO'S OWN DEVICE LIST CAN ALSO HAVE GONE STALE AGAINST COREAUDIO
        (-9986 EVEN ON A BRAND NEW STREAM), WHICH ONLY A REINIT OF PORTAUDIO ITSELF CLEARS."""
        if self.stream is not None and self.stream.samplerate != rate:
            self.shut()

        if self.stream is None:
            self.stream = sd.OutputStream(samplerate=rate, channels=CHANNELS, dtype="float32")

        try:
            if not self.stream.active:
                self.stream.start()
        except sd.PortAudioError:
            self.shut()
            self.stream = sd.OutputStream(samplerate=rate, channels=CHANNELS, dtype="float32")

            try:
                self.stream.start()
            except sd.PortAudioError:
                self.shut()
                sd._terminate()
                sd._initialize()
                self.stream = sd.OutputStream(samplerate=rate, channels=CHANNELS, dtype="float32")
                self.stream.start()

        return self.stream

    def rest(self):
        """NOTHING LEFT TO SAY, SO THE DEVICE STOPS PULLING. THE STREAM ITSELF IS KEPT, WHICH
        IS WHAT MAKES STARTING AGAIN THIRTY MILLISECONDS INSTEAD OF A SECOND AND A HALF, AND
        ONLY THE WHOLE TURN ENDING COUNTS: MID SENTENCE THERE IS ALWAYS SOMETHING PENDING."""
        if self.pending > 0 or not self.clips.empty():
            return

        with self.device:
            try:
                if self.stream is not None and self.stream.active:
                    self.stream.stop()
            except Exception:
                pass

    def cut(self):
        """WHAT IS BUFFERED THROWN AWAY RATHER THAN PLAYED OUT. THE DEVICE STAYS OPEN, WHICH IS
        WHAT KEEPS THE NEXT THING SAID FROM WAITING ON COREAUDIO WAKING IT UP AGAIN."""
        try:
            if self.stream is not None and self.stream.active:
                self.stream.abort()
        except Exception:
            pass

    def shut(self):
        try:
            if self.stream is not None:
                self.stream.abort()
                self.stream.close()
        except Exception:
            pass
        finally:
            self.stream = None

    def settle(self, era):
        """ONE THING DONE WITH. WORK FROM BEFORE A BARGE COUNTS FOR NOTHING: ITS COUNT WENT
        WITH THE ERA IT WAS RAISED IN, AND TAKING ONE OFF NOW WOULD TAKE IT OFF WHATEVER IS
        BEING SAID INSTEAD, WHICH IS HOW HAPPY USED TO READ AS FINISHED WHILE STILL TALKING."""
        with self.quiet:
            if era != self.era:
                return

            self.pending = max(0, self.pending - 1)

            if self.pending == 0:
                self.quiet.notify_all()


def native(fallback):
    """THE RATE THE OUTPUT DEVICE ITSELF RUNS AT, BECAUSE PORTAUDIO ANSWERS ANY OTHER ONE WITH
    ITS OWN CONVERTER, WHICH ON COREAUDIO ASKS FOR FIFTEEN SAMPLES AT A TIME AND CRACKLES."""
    try:
        return int(sd.query_devices(kind="output")["default_samplerate"])
    except Exception:
        return fallback


def levels(samples, rate):
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
