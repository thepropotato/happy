"""On macOS, the microphone through the system's voice processing, which takes out whatever the speakers are playing."""

import logging

import numpy as np

log = logging.getLogger("happy.microphone")

RATE = 16000
BLOCK = 1600
TAPS = 63


class Resampler:
    """Any input rate down to exactly 16 kHz, a block at a time, filtered first so nothing above the new rate folds back."""

    def __init__(self, source_rate):
        self.ratio = source_rate / RATE
        middle = np.arange(TAPS) - (TAPS - 1) / 2
        cutoff = 0.45 / self.ratio
        taps = 2 * cutoff * np.sinc(2 * cutoff * middle) * np.hamming(TAPS)
        self.taps = (taps / taps.sum()).astype(np.float32)
        self.history = np.zeros(TAPS - 1, np.float32)
        self.left = np.zeros(0, np.float32)
        self.at = 0.0

    def __call__(self, samples):
        joined = np.concatenate([self.history, samples])
        self.history = joined[-(TAPS - 1):]
        smooth = np.convolve(joined, self.taps, mode="valid").astype(np.float32)
        source = np.concatenate([self.left, smooth])
        count = int(np.floor((len(source) - 1 - self.at) / self.ratio)) + 1 if len(source) - 1 >= self.at else 0
        where = self.at + np.arange(count) * self.ratio
        out = np.interp(where, np.arange(len(source)), source).astype(np.float32)
        after = self.at + count * self.ratio
        drop = min(int(after), len(source))
        self.left = source[drop:]
        self.at = after - drop
        return out


class EchoCancelled:
    """Hands over 16 kHz blocks of what the person said, with the video or music the Mac is playing removed."""

    def __init__(self, deliver):
        self.deliver = deliver
        self.engine = None
        self.pending = np.zeros(0, np.float32)

    def start(self):
        from AVFoundation import AVAudioEngine

        self.engine = AVAudioEngine.alloc().init()
        node = self.engine.inputNode()
        ok, error = node.setVoiceProcessingEnabled_error_(True, None)
        if not ok:
            raise RuntimeError(f"voice processing would not start: {error}")
        try:
            node.setVoiceProcessingOtherAudioDuckingConfiguration_((False, 10))
        except Exception:
            log.info("this macOS cannot turn down the ducking of other audio")
        source = node.outputFormatForBus_(0)
        self.resample = Resampler(source.sampleRate())
        log.info("the microphone hands over %d Hz", source.sampleRate())
        # A FIXED SAMPLE COUNT IS A LONGER WAIT ON A SLOWER DEVICE, SO EACH DELIVERY IS ONE BLOCK'S WORTH OF TIME.
        node.installTapOnBus_bufferSize_format_block_(0, round(source.sampleRate() * BLOCK / RATE), source, self.arrived)
        self.engine.prepare()
        ok, error = self.engine.startAndReturnError_(None)
        if not ok:
            raise RuntimeError(f"the microphone would not start: {error}")

    def arrived(self, buffer, when):
        frames = buffer.frameLength()
        samples = np.array(buffer.floatChannelData()[0][:frames], dtype=np.float32)
        down = self.resample(samples)
        self.pending = np.concatenate([self.pending, down])
        while len(self.pending) >= BLOCK:
            self.deliver(self.pending[:BLOCK].copy())
            self.pending = self.pending[BLOCK:]

    def stop(self):
        if self.engine is not None:
            self.engine.stop()
            self.engine.inputNode().removeTapOnBus_(0)
            self.engine = None
