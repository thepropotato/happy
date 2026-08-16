"""GETTING A MISSING VOICE, BEHIND THE CONVERSATION, SO NO REPLY IS HELD UP BY A DOWNLOAD."""

import threading

from face import show

# ONE ATTEMPT EACH PER RUN. A FAILED DOWNLOAD SHOULD NOT RETRY ON EVERY SENTENCE. EACH ENGINE
# COUNTS ITS OWN, SO ONE FAILING TO GET A LANGUAGE DOES NOT STOP THE OTHER TRYING.
getting = set()


def collect(wanted, known, fetch):
    """SET A LANGUAGE'S VOICE DOWNLOADING, IF THIS ENGINE HAS ONE AND IS NOT ALREADY ON IT."""
    if wanted not in known or (fetch.__module__, wanted) in getting:
        return

    getting.add((fetch.__module__, wanted))
    show.note(f"Getting the {wanted} voice. This reply is spoken in the one already here.")

    threading.Thread(target=bring, args=(wanted, fetch), daemon=True).start()


def bring(wanted, fetch):
    try:
        fetch(wanted)
        show.note(f"The {wanted} voice is ready.")
    except Exception as error:
        show.trouble(f"Could not get the {wanted} voice ({error})")
