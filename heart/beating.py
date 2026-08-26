"""THE TICK. IT READS THE WALL CLOCK, WHICH IS THE ONLY THING THAT SURVIVES A SLEEP."""

import threading

from face import show
from heart import firing, rules

# SHORT ENOUGH THAT NOTHING IS NOTICEABLY LATE, LONG ENOUGH TO COST NOTHING. A TIMER SET
# FOR THE ACTUAL HOUR WOULD NOT SURVIVE THE LID GOING DOWN, WHICH IS WHY THIS POLLS.
TICK = 20

beating = threading.Event()

thread = None


def start(saying):
    """BEGIN. saying IS THE ONE THING ONLY main.py CAN DO: SPEAK WHEN NOBODY ASKED."""
    global thread

    if thread is not None:
        return thread

    beating.clear()
    thread = threading.Thread(target=beat, args=(saying,), daemon=True)
    thread.start()

    return thread


def stop():
    beating.set()


def beat(saying):
    # BEFORE THE FIRST TICK, SO WHAT WENT BY WHILE HE WAS OFF IS ACCOUNTED FOR IN ONE
    # BREATH RATHER THAN GOING OFF ONE AT A TIME AS THE LOOP CATCHES UP WITH THEM.
    catch(saying)

    while not beating.is_set():
        try:
            firing.due(saying, rules.now())
        except Exception as error:
            show.trouble(f"A reminder would not go off ({error})")

        beating.wait(TICK)


def catch(saying):
    try:
        firing.missed(saying, rules.now())
    except Exception as error:
        show.trouble(f"Could not work out what was missed ({error})")
