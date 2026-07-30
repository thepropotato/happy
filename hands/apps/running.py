"""STARTING THINGS, AND ASKING THE SYSTEM SMALL QUESTIONS ABOUT ITSELF."""

import subprocess

OPEN_TIMEOUT_SECONDS = 15

# HOW LONG A BROWSER GETS TO FAIL BEFORE WE CALL IT LAUNCHED. SEE released().
EARLY_SECONDS = 2

ASK_TIMEOUT_SECONDS = 5


def launch(command):
    """RUN AN OPENER. RETURNS THE COMPLAINT, OR None WHEN IT WORKED."""
    try:
        done = subprocess.run(
            command, capture_output=True, text=True, timeout=OPEN_TIMEOUT_SECONDS
        )
    except (OSError, subprocess.SubprocessError) as error:
        return f"Could not open it: {error}"

    if done.returncode != 0:
        return f"Could not open it: {(done.stderr or '').strip() or 'the system refused'}"

    return None


def released(command):
    """START SOMETHING AND DO NOT WAIT FOR IT TO FINISH.

    A BROWSER THAT WAS NOT ALREADY RUNNING BECOMES THE BROWSER AND DOES NOT
    RETURN UNTIL IT IS CLOSED. ONE THAT WAS RUNNING FORWARDS THE ADDRESS AND
    EXITS AT ONCE. BOTH ARE SUCCESS, SO THE EXIT CODE IS NOT THE TEST: OPERA
    EXITS 24 HAVING DONE EXACTLY WHAT WAS ASKED. STDERR IS THE TEST.
    """
    try:
        started = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            start_new_session=True,  # NOT OURS TO OUTLIVE. IT IS THE PERSON'S BROWSER.
            text=True,
        )
    except OSError as error:
        return f"Could not open it: {error}"

    try:
        _, complaint = started.communicate(timeout=EARLY_SECONDS)
    except subprocess.TimeoutExpired:
        return None

    said = (complaint or "").strip()

    return f"Could not open it: {said[:200]}" if said else None


def ask(command):
    """RUN SOMETHING SMALL AND HAND BACK WHAT IT SAID, OR None IF IT WOULD NOT."""
    try:
        done = subprocess.run(
            command, capture_output=True, text=True, timeout=ASK_TIMEOUT_SECONDS
        )
    except (OSError, subprocess.SubprocessError):
        return None

    return done.stdout if done.returncode == 0 else None
