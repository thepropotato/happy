"""On macOS, the microphone through the system's voice processing, which takes out whatever the speakers are playing."""

import logging

import numpy as np

log = logging.getLogger("happy.microphone")

RATE = 16000
BLOCK = 1600


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
        self.step = max(1, round(source.sampleRate() / RATE))
        node.installTapOnBus_bufferSize_format_block_(0, 4800, source, self.arrived)
        self.engine.prepare()
        ok, error = self.engine.startAndReturnError_(None)
        if not ok:
            raise RuntimeError(f"the microphone would not start: {error}")

    def arrived(self, buffer, when):
        frames = buffer.frameLength()
        samples = np.array(buffer.floatChannelData()[0][:frames], dtype=np.float32)
        usable = len(samples) - len(samples) % self.step
        down = samples[:usable].reshape(-1, self.step).mean(axis=1)
        self.pending = np.concatenate([self.pending, down])
        while len(self.pending) >= BLOCK:
            self.deliver(self.pending[:BLOCK].copy())
            self.pending = self.pending[BLOCK:]

    def stop(self):
        if self.engine is not None:
            self.engine.stop()
            self.engine.inputNode().removeTapOnBus_(0)
            self.engine = None
