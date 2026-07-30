"""THE ONE EVENT LOOP EVERY CONNECTION LIVES ON, AND THE THREAD THAT TURNS IT.

THE PROTOCOL IS ASYNC AND THE GRAPH IN brain/ IS NOT, SO SOMETHING HAS TO STAND
BETWEEN THEM. ONE LOOP ON ONE DAEMON THREAD, STARTED THE FIRST TIME ANYBODY ASKS
AND STOPPED AT EXIT. A TOOL CALL HANDS IT A COROUTINE AND WAITS FOR THE ANSWER.
"""

import asyncio
import atexit
import threading

GOODBYE_SECONDS = 2  # LONG ENOUGH FOR A CLEAN CLOSE, SHORT ENOUGH TO NEVER HANG A QUIT.

turning = None
loop = None
lock = threading.Lock()


def spin():
    """THE LOOP, RUNNING. STARTS THE THREAD THE FIRST TIME SOMEBODY NEEDS IT."""
    global turning, loop

    with lock:
        if loop is not None:
            return loop

        ready = threading.Event()
        loop = asyncio.new_event_loop()

        turning = threading.Thread(target=turn, args=(loop, ready), daemon=True, name="mcps")
        turning.start()
        ready.wait()

        return loop


def turn(here, ready):
    asyncio.set_event_loop(here)
    here.call_soon(ready.set)
    here.run_forever()


def submit(work):
    """START SOMETHING ON THE LOOP AND HAND BACK A FUTURE THIS THREAD CAN WAIT ON."""
    return asyncio.run_coroutine_threadsafe(work, spin())


def run(work, timeout=None):
    """START SOMETHING AND WAIT FOR IT. THE CALLER'S THREAD BLOCKS, THE LOOP DOES NOT."""
    waiting = submit(work)

    try:
        return waiting.result(timeout)
    except TimeoutError:
        waiting.cancel()

        raise


def running():
    return loop is not None and not loop.is_closed()


def stop():
    """PUT THE LOOP DOWN. WHAT WAS STILL IN FLIGHT IS GIVEN A MOMENT TO FINISH."""
    global turning, loop

    with lock:
        if loop is None:
            return

        here, thread = loop, turning
        loop, turning = None, None

    here.call_soon_threadsafe(here.stop)

    if thread is not None:
        thread.join(GOODBYE_SECONDS)


atexit.register(stop)
