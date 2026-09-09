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


def start():
    """BEGIN THE THINKING PULSE ONCE, WITHOUT MAKING THE MODEL CALL WAIT FOR AUDIO."""
    global worker

    with lock:
        if worker is not None and worker.is_alive():
            return

        ending.clear()
        worker = threading.Thread(target=loop, daemon=True)
        worker.start()


def stop():
    """END THE PULSE AND CLOSE ITS STREAM, INCLUDING WHEN THERE WAS NOTHING TO STOP."""
    ending.set()
    shut()


def loop():
    global stream

    pulse = tone()
    position = 0

    try:
        with lock:
            if ending.is_set():
                return

            try:
                with quiet():
                    stream = sd.OutputStream(
                        samplerate=RATE, channels=CHANNELS, dtype="float32"
                    )
                    stream.start()
            except Exception:
                # NO DEVICE, OR ONE THAT WILL NOT OPEN. THE PULSE IS A COMFORT, NOT THE TURN.
                return

        while not ending.is_set():
            part = pulse[position : position + STEP]
            position = (position + len(part)) % len(pulse)

            with lock:
                if ending.is_set() or stream is None:
                    return

                try:
                    stream.write(part)
                except Exception:
                    # THE DEVICE WENT AWAY MID-BEAT, WHICH IS HEADPHONES COMING OUT. THE TURN
                    # CARRIES ON WITHOUT IT AND SAYS NOTHING, BECAUSE NOTHING WAS LOST.
                    return
    finally:
        shut()


def shut():
    global stream

    with lock:
        current = stream
        stream = None

        if current is None:
            return

        try:
            with quiet():
                current.abort()
                current.close()
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


surrender(stop)

__all__ = ["start", "stop"]