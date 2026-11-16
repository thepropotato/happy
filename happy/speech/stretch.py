"""Streaming pitch-preserving overlap-add, using only numpy."""

import numpy as np


class Stretcher:
    def __init__(self, rate):
        self.hop = max(1, round(rate * 0.0125))
        self.frame = 2 * self.hop
        self.search = round(rate * 0.01)
        self.window = np.hanning(self.frame + 1)[:self.hop].astype(np.float32)
        self.reset()

    def reset(self):
        self.input = np.empty(0, np.float32)
        self.tail = None
        self.position = 0.0
        self.goal = 0.0
        self.emitted = 0
        self.speed = 1.0

    def process(self, samples, speed):
        """Adds raw sound and returns the complete overlap frames available."""
        if speed == 1.0 and self.tail is None and not len(self.input):
            return samples
        self.speed = speed
        self.goal += len(samples) / speed
        self.input = np.concatenate((self.input, samples))
        return self._render(False)

    def _render(self, ending):
        parts = []
        while self.emitted < round(self.goal):
            expected = round(self.position)
            lo = max(0, expected - self.search) if self.tail is not None else expected
            hi = expected + self.search if self.tail is not None else expected
            if hi + self.frame > len(self.input):
                if not ending:
                    break
                self.input = np.pad(self.input, (0, hi + self.frame - len(self.input)))
            at = lo
            if self.tail is not None:
                candidates = np.lib.stride_tricks.sliding_window_view(
                    self.input[lo:hi + self.hop], self.hop)
                correlation = np.einsum("ij,j->i", candidates, self.tail)
                energy = np.sqrt(np.einsum("ij,ij->i", candidates, candidates) + 1e-12)
                scores = correlation / energy
                # TIES IN SILENCE SHOULD STAY NEAR THE EXPECTED POSITION.
                best = np.max(scores)
                choices = np.flatnonzero(scores >= best - 1e-7)
                at += int(choices[np.argmin(np.abs(choices + lo - expected))])
            frame = self.input[at:at + self.frame]
            head = frame[:self.hop]
            if self.tail is not None:
                head = self.tail * (1 - self.window) + head * self.window
            take = min(self.hop, round(self.goal) - self.emitted) if ending else self.hop
            parts.append(head[:take].copy())
            self.tail = frame[self.hop:].copy()
            self.emitted += take
            self.position += self.hop * self.speed
            discard = max(0, int(self.position) - self.search)
            discard = min(discard, len(self.input))
            self.input = self.input[discard:]
            self.position -= discard
        return np.concatenate(parts) if parts else np.empty(0, np.float32)

    def flush(self):
        """Finishes a sentence, including its last partial frame."""
        sound = self._render(True)
        self.reset()
        return sound

    def unstretched(self):
        """Hands unplayed raw sound back when returning to normal speed."""
        sound = self.input[round(self.position):].copy()
        if self.tail is not None:
            take = min(self.hop, len(sound))
            sound[:take] = self.tail[:take] * (1 - self.window[:take]) + sound[:take] * self.window[:take]
        self.reset()
        return sound
