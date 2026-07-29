"""COMPLETELY LOCAL VOICE ASSISTANT.

    hold key ─► record ─► transcribe ─► think ─► speak
      ears        ears        ears       brain    voice
                                           │
                                           ▼
                                     hands and eyes

PLAIN FOR A TERMINAL. WITH --serve IT TALKS JSON TO A WINDOW, WHICH IS HOW
face/window RUNS IT.
"""

from face import silence

silence.configure()  # MUST RUN BEFORE THE IMPORTS BELOW OPEN AN ONNX SESSION.

import os
import sys
import threading
import time

import brain
import conscience
import ears
import memory
import voice
from face import console, orders, panel, show

SERVE = "--serve"

# ONE TURN AT A TIME. A LINE TYPED INTO THE WINDOW ARRIVES ON ITS OWN THREAD AND
# MUST NOT LAND IN THE MIDDLE OF A SPOKEN ONE.
taking = threading.Lock()


def main():
    windowed = SERVE in sys.argv

    show.attach(panel if windowed else console)
    show.state(panel.LOADING)

    happy, speaker = start()

    recorder = ears.Recorder()

    # THE KEY GOING DOWN CUTS HAPPY OFF MID SENTENCE. SOMEONE WHO HAS STARTED
    # TALKING HAS STOPPED LISTENING, AND THE MIC MUST NOT HEAR HIM EITHER.
    ptt = ears.PushToTalk(on_press=speaker.stop)

    # THE FACE WANTS TO KNOW WHERE EACH TURN'S TIME WENT.
    brain.watches(show.step)

    thrown = memory.prune(recorder.recordings)  # ONLY IF A SETTING SAYS TO.

    if thrown:
        show.note(f"Threw away {thrown}")

    if windowed:
        attend(happy, speaker, recorder, ptt)
    else:
        show.note(f"Hold {ptt.key_name} to talk. Ctrl+C to quit.")

    try:
        listen(recorder, ptt, happy, speaker)
    except KeyboardInterrupt:
        show.note("\nBye")
    finally:
        shut(speaker, recorder, ptt)


def attend(happy, speaker, recorder, ptt):
    """HAND THE WINDOW THE FEW THINGS ONLY THIS FILE CAN DO."""
    conscience.asks(panel.confirm)

    orders.serve(
        forget=happy.forget,
        say=lambda text: typed(happy, speaker, text),
        quit=lambda: leave(speaker, recorder, ptt),
    )

    panel.ready(key=ptt.key_name)
    show.state(panel.IDLE)


def start():
    """LOAD EVERY MODEL UP FRONT, SO NO TAKE PAYS FOR IT LATER."""
    show.note("Loading models")

    try:
        ears.load_model()
        ears.warm()
    except ears.EarsError as error:  # NO HEARING AT ALL. NOTHING TO DO BUT SAY SO.
        raise SystemExit(error)

    speaker, mute = voice.create()

    if mute:  # HAPPY STILL ANSWERS, HE JUST ANSWERS IN WRITING.
        show.note(mute)

    speaker.warm()

    try:
        happy = brain.Happy()
    except brain.LLMError as error:  # NO BACKEND AT ALL. NOTHING TO DO BUT SAY SO.
        raise SystemExit(error)

    # A BACKEND THAT CANNOT BE TOLD A CONTEXT LENGTH SAYS SO NOW, RATHER THAN
    # LETTING IT BE FOUND OUT THROUGH ANSWERS THAT QUIETLY GET WORSE.
    caveat = brain.caveat()

    if caveat:
        show.note(caveat)

    try:
        happy.warm()
    except brain.LLMError as error:  # HE STILL HEARS, HE JUST CANNOT ANSWER YET.
        show.note(error)

    return happy, speaker


def listen(recorder, ptt, happy, speaker):
    """ONE TURN PER LAP: HOLD, SPEAK, RELEASE, HEAR AN ANSWER."""
    while True:
        audio = capture(recorder, ptt)

        if audio is None:  # THE KEY WAS BRUSHED. NOT A TURN, SAY NOTHING.
            continue

        with taking:
            spoken(happy, speaker, audio)


def capture(recorder, ptt):
    """THE WAV, OR None IF THE KEY WAS ONLY BRUSHED."""
    ptt.refit()  # A DIFFERENT KEY WAS PICKED WHILE THE LAST TAKE WAS RUNNING.
    ptt.reset()  # IGNORE THE KEYBOARD FROM WHILE THAT TAKE WAS TRANSCRIBING.
    ptt.wait_press()

    show.listening()
    recorder.start()

    ptt.wait_release()

    return recorder.stop()


def spoken(happy, speaker, audio):
    show.begin()

    started = time.perf_counter()
    speech = ears.transcribe(audio)
    heard = time.perf_counter() - started

    if not speech:
        show.trouble("nothing heard")
        show.end()
        return

    show.said(speech, heard)
    respond(happy, speaker, speech, audio)
    show.end()


def typed(happy, speaker, text):
    """THE SAME TURN, WRITTEN INSTEAD OF SPOKEN. THE WINDOW HAS A BOX FOR IT."""
    text = (text or "").strip()

    if not text:
        return

    with taking:
        show.begin()
        show.said(text)
        respond(happy, speaker, text)
        show.end()


def respond(happy, speaker, speech, audio=None):
    speaker.refit()  # A DIFFERENT ENGINE WAS PICKED WHILE THE LAST TURN RAN.
    show.opening()

    try:
        # SPOKEN AND PRINTED OFF THE ONE STREAM. THE SPEAKER HOLDS EACH PIECE
        # BACK UNTIL IT HAS A WHOLE SENTENCE, THE PRINTING DOES NOT WAIT. THE WAV
        # GOES IN THE CONVERSATION SO A LINE CAN BE HEARD AGAIN LATER.
        for piece in speaker.say(happy.say_streaming(speech, audio=audio)):
            show.piece(piece)
    except brain.LLMError as error:  # A DEAD MODEL MUST NOT END THE SESSION.
        show.trouble(error)


def shut(speaker, recorder, ptt):
    speaker.close()
    recorder.close()
    ptt.stop()


def leave(speaker, recorder, ptt):
    """THE WINDOW ASKED US TO GO, AND THE MAIN THREAD IS SAT ON A KEY PRESS."""
    shut(speaker, recorder, ptt)
    os._exit(0)


if __name__ == "__main__":
    main()
