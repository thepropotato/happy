"""THE VOICE THAT SAYS NOTHING, SO NOTHING ELSE NEEDS AN IF."""

import numpy as np

RATE = 22050  # NOTHING PLAYS IT, BUT THE PLAYER STILL ASKS.


class Mute:
    rate = RATE

    def say(self, text):
        return np.zeros(0, dtype=np.float32)

    def stream(self, text):
        return iter(())

    def refit(self):
        pass

    def warm(self):
        pass
