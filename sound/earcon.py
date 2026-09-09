"""A QUIET PULSE THAT SAYS HAPPY IS STILL THINKING."""

import threading

import numpy as np
import sounddevice as sd

from sound.device import quiet, surrender

RATE = 44100
CHANNELS = 1
SECONDS = 2.6
STEP = RATE // 20

# THE TWO THUDS OF ONE BEAT, AS HOW FAR INTO THE LOOP EACH FALLS AND HOW HARD IT LANDS.
BEATS = ((0.0, 1.0), (0.34, 0.62))
THUD = 0.20
PITCH = 62

lock = threading.RLock()
ending = threading.Event()
worker = None
stream = None

# WHICH PULSE IS THE CURRENT ONE. A WORKER WHOSE ERA HAS PASSED STOPS, SO THE ONE LEAVING
# CANNOT BEAT OVER THE ONE ARRIVING.
era = 0

# HOW FAR INTO THE LOOP THE LAST PULSE GOT. A TURN IS MANY CALLS, AND EACH ONE START()S: FROM
# ZERO EVERY TIME, A RUN OF SHORT TOOL CALLS WOULD SOUND THE LOUD DOWNBEAT OVER AND OVER,
# WHICH IS A HAMMER RATHER THAN A HEARTBEAT. CARRYING THE POSITION KEEPS ONE STEADY RHYTHM
# ACROSS THE WHOLE TURN, HOWEVER MANY TIMES THE PULSE IS ASKED TO BEGIN.
position = 0


def start():
    """BEGIN THE THINKING PULSE ONCE, WITHOUT MAKING THE MODEL CALL WAIT FOR AUDIO."""
    global worker

    with lock:
        # A WORKER THAT IS ALIVE BUT ENDING IS ON ITS WAY OUT AND WILL NOT PLAY AGAIN, SO IT
        # IS NOT ONE TO STAND ASIDE FOR. STANDING ASIDE FOR IT LEAVES THE TURN SILENT: stop()
        # AND THE NEXT TOOL CALL ARE A MOMENT APART, AND FOR THAT MOMENT THE OLD LOOP IS
        # STILL DRAINING ITS LAST BLOCK.
        if worker is not None and worker.is_alive() and not ending.is_set():
            return

        # AN OLD WORKER MAY STILL BE DRAINING ITS LAST BLOCK. IT OWNS ITS OWN STREAM AND
        # SHUTS IT ON THE WAY OUT, SO THE NEW ONE NEED NOT WAIT: WAITING WOULD PUT THAT BLOCK
        # IN FRONT OF THE MODEL CALL, WHICH IS THE DELAY THIS WHOLE ARRANGEMENT AVOIDS. THE
        # ERA IS WHAT KEEPS THEM APART, SO THE LEAVING ONE CANNOT SPEAK OVER THE ARRIVING ONE.
        global era
        era += 1
        ending.clear()
        worker = threading.Thread(target=loop, args=(era,), daemon=True)
        worker.start()


def stop():
    """END THE PULSE, INCLUDING WHEN THERE WAS NOTHING TO STOP.

    THE STREAM IS NOT CLOSED HERE. THE BEAT IS WRITTEN OUTSIDE THE LOCK, SO CLOSING IT FROM
    THIS SIDE FREES A STREAM THE WRITER MAY BE INSIDE OF, AND PORTAUDIO TAKES THAT AS A
    SEGMENTATION FAULT RATHER THAN AN EXCEPTION. THE FLAG IS SET AND THE LOOP SHUTS ITS OWN
    STREAM, WHICH IS WITHIN ONE BLOCK. NOTHING WAITS ON IT: THE POINT OF RETURNING AT ONCE IS
    THAT THE FIRST SPOKEN WORD DOES NOT QUEUE BEHIND A BLOCK OF PULSE."""
    ending.set()


def loop(mine):
    """ONE PULSE, HELD BY THE WORKER THAT OPENED IT.

    THE STREAM IS A LOCAL AND NEVER READ BACK OFF THE MODULE. A TURN START()S ON EVERY CALL,
    SO A LEAVING WORKER AND AN ARRIVING ONE OVERLAP BY A BLOCK; SHARING ONE GLOBAL THERE MEANS
    THE ARRIVING ONE REPLACES A STREAM THE LEAVING ONE IS STILL INSIDE, AND CLOSING THAT IS A
    SEGMENTATION FAULT RATHER THAN AN EXCEPTION."""
    global position

    pulse = tone()
    mine_stream = None

    try:
        with lock:
            if ending.is_set() or mine != era:
                return

            try:
                with quiet():
                    mine_stream = sd.OutputStream(
                        samplerate=RATE, channels=CHANNELS, dtype="float32"
                    )
                    mine_stream.start()
            except Exception:
                # NO DEVICE, OR ONE THAT WILL NOT OPEN. THE PULSE IS A COMFORT, NOT THE TURN.
                mine_stream = None

                return

            keep(mine, mine_stream)

        # THE WRITE IS MADE OUTSIDE THE LOCK. IT BLOCKS FOR THE LENGTH OF THE BLOCK IT IS
        # GIVEN, AND stop() WANTS THE SAME LOCK: HELD ACROSS THE WRITE, IT WOULD PUT THAT WHOLE
        # BLOCK IN FRONT OF THE FIRST SPOKEN WORD, WHICH IS THE VERY DELAY voice/speaker.py
        # DROPS ITS OWN LOCK BETWEEN BLOCKS TO AVOID.
        while not ending.is_set() and mine == era:
            part = pulse[position : position + STEP]
            position = (position + len(part)) % len(pulse)

            try:
                mine_stream.write(part)
            except Exception:
                # THE DEVICE WENT AWAY MID-BEAT, WHICH IS HEADPHONES COMING OUT. THE TURN
                # CARRIES ON WITHOUT IT AND SAYS NOTHING, BECAUSE NOTHING WAS LOST.
                return
    finally:
        drop(mine, mine_stream)


def keep(mine, opened):
    """THE LIVE STREAM, NAMED SO A RESET CAN FIND IT WITHOUT TAKING IT FROM ITS WRITER."""
    global stream

    with lock:
        if mine == era:
            stream = opened


def drop(mine, opened):
    """ONE WORKER'S STREAM, SHUT BY THAT WORKER AND NOBODY ELSE."""
    global stream

    with lock:
        if stream is opened:
            stream = None

    if opened is None:
        return

    try:
        with quiet():
            opened.abort()
            opened.close()
    except Exception:
        pass


def tone():
    """TWO SOFT THUDS AND A LONG REST, WHICH IS A RHYTHM THE BODY READS WITHOUT LISTENING.

    A HELD TONE IS THE WORST THING TO PUT UNDER A CONVERSATION: A PURE PITCH HAS NOTHING FOR
    THE EAR TO HABITUATE TO, SO IT KEEPS CATCHING ATTENTION BACK FOR AS LONG AS IT RUNS. A
    BEAT SPENDS MOST OF ITS LOOP SILENT, AND EVERY THUD DIES INSIDE ITS OWN LENGTH, SO THERE
    IS NEVER A CONTINUOUS SOUND TO WEAR ON ANYBODY."""
    count = int(RATE * SECONDS)
    pulse = np.zeros(count, dtype=np.float32)
    length = int(RATE * 0.30)
    times = np.arange(length, dtype=np.float32) / RATE

    # A LOW SINE UNDER A STEEP DECAY IS A THUD; THE DECAY IS WHAT KEEPS IT FROM RINGING.
    thud = np.sin(2 * np.pi * PITCH * times) * np.exp(-np.linspace(0, 7, length))

    for offset, level in BEATS:
        at = int(offset * RATE)
        pulse[at : at + length] += thud * level

    return np.ascontiguousarray(pulse * THUD, dtype=np.float32)


def release():
    """A RESET IS TAKING PORTAUDIO DOWN, SO THE PULSE MUST BE ALL THE WAY OUT OF ITS STREAM.

    UNLIKE stop(), THIS WAITS. _terminate() INVALIDATES EVERY STREAM IN THE PROCESS, AND A
    WRITER STILL INSIDE ONE WOULD BE HOLDING A DEAD POINTER."""
    stop()
    current = worker

    if current is not None and current is not threading.current_thread():
        current.join(timeout=1.0)


surrender(release)

__all__ = ["start", "stop"]