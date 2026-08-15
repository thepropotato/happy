"""HIS NAME, HEARD WHILE THE SENTENCE IS STILL BEING SAID.

A TAKE IS ONLY READ ONCE IT HAS ENDED, AND IT ENDS ON SILENCE, SO THE FACE COULD NOT ANSWER
"HEY HAPPY" UNTIL THE PAUSE AFTER IT HAD BEEN WAITED OUT, THE TAIL KEPT, AND THE WHOLE THING
READ — THE BEST PART OF TWO SECONDS OF SOMEBODY WATCHING A WINDOW DO NOTHING. SO ONE LOOK IS
TAKEN AT THE FRONT OF THE TAKE WHILE THE REST IS STILL ARRIVING, AND IF HIS NAME IS IN IT THE
FACE STARTS LISTENING THERE AND THEN. IT DECIDES NOTHING AND IT ANSWERS NOTHING: THE WHOLE
TAKE IS STILL READ AFTERWARDS, THE SAME WAY, AND THAT READING IS WHAT HAPPY ACTS ON."""

import tempfile
import threading
from pathlib import Path

from ears import engines
from ears.calling import addressed, phrases
from face import show

# LONG ENOUGH TO HOLD A NAME. EARLIER THAN THIS THERE IS NOTHING WORTH READING YET.
ENOUGH_SECONDS = 1.1

# ONE FILE, WRITTEN OVER EVERY TIME. IT IS NEVER KEPT AND NEVER PLAYED BACK.
GLIMPSE = "happy-glimpse.wav"


def watch(recorder):
    """START LISTENING FOR HIS NAME IN A TAKE THAT HAS ONLY JUST BEGUN."""
    return Look(recorder)


class Look:
    """ONE READ OF THE FRONT OF A TAKE, ON ITS OWN THREAD, DROPPED IF THE TAKE ENDS FIRST."""

    def __init__(self, recorder):
        self.recorder = recorder
        self.over = threading.Event()
        self.where = Path(tempfile.gettempdir()) / GLIMPSE

        threading.Thread(target=self.looking, daemon=True, name="rousing").start()

    def stop(self):
        """THE TAKE HAS ENDED, SO WHATEVER THIS FINDS NOW IS THE OTHER PATH'S TO SAY."""
        self.over.set()

    def looking(self):
        if self.over.wait(ENOUGH_SECONDS):
            return

        taken = self.recorder.peek(self.where)

        if taken is None:
            return

        try:
            text = engines.quickly(taken)
        except Exception:
            return  # A LOOK THAT FAILED COSTS NOTHING: THE WHOLE TAKE IS STILL COMING.
        finally:
            Path(taken).unlink(missing_ok=True)

        # CHECKED LAST, NOT FIRST: THE TAKE MAY HAVE ENDED WHILE THIS WAS BEING READ, AND
        # THEN THE FACE IS ALREADY PAST LISTENING AND MUST NOT BE PUT BACK TO IT.
        if not self.over.is_set() and addressed(text, phrases()) is not None:
            show.listening()
