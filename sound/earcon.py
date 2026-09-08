"""A QUIET PULSE THAT SAYS HAPPY IS STILL THINKING."""

import threading

import numpy as np
import sounddevice as sd

from sound.device import quiet, surrender

RATE = 44100
CHANNELS = 1
SECONDS = 1.1
STEP = RATE // 20

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
            except Exception as error:
                return

        while not ending.is_set():
            part = pulse[position : position + STEP]
            position = (position + len(part)) % len(pulse)

            with lock:
                if ending.is_set() or stream is None:
                    return

                try:
                    stream.write(part)
                except Exception as error:
                    print(f"[earcon] write failed: {error}")  # TEMPORARY
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
    """A ZERO-ENDED PULSE LOOPS WITHOUT A CLICK, AND ITS LOW LEVEL KEEPS IT UNDER SPEECH."""
    count = int(RATE * SECONDS)
    times = np.arange(count, dtype=np.float32) / RATE
    wave = np.sin(2 * np.pi * 220 * times)
    envelope = np.ones(count, dtype=np.float32)
    attack = int(RATE * 0.18)
    decay = int(RATE * 0.28)
    envelope[:attack] = np.linspace(0, 1, attack, endpoint=False)
    envelope[-decay:] = np.linspace(1, 0, decay, endpoint=True)

    return np.ascontiguousarray((wave * envelope * 0.3), dtype=np.float32)


surrender(stop)

__all__ = ["start", "stop"]