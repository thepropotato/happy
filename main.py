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
import mcps
import memory
import voice
from mcps.servers.whatsapp import chatting
from face import console, orders, panel, show

SERVE = "--serve"

# ONE TURN AT A TIME. A LINE TYPED INTO THE WINDOW ARRIVES ON ITS OWN THREAD.
taking = threading.Lock()


def main():
    windowed = SERVE in sys.argv

    show.attach(panel if windowed else console)
    show.state(panel.LOADING)

    happy, speaker = start()

    recorder = ears.Recorder()

    # SOMEBODY WHO HAS STARTED TALKING HAS STOPPED LISTENING.
    ptt = ears.PushToTalk(on_press=speaker.stop)

    brain.watches(show.step)

    chatting.listen(lambda text: distant(happy, text))

    thrown = memory.prune(recorder.recordings)  # ONLY IF A SETTING SAYS TO.

    if thrown:
        show.note(f"Threw away {thrown}")

    if windowed:
        attend(happy, speaker, recorder, ptt)
    else:
        show.note(f"Hold {ptt.key_name} to talk. Ctrl+C to quit.")

        if ptt.deaf:
            show.note(ears.DEAF)

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
        stop=lambda: stop_turn(happy, speaker),
        quit=lambda: leave(speaker, recorder, ptt),
    )

    panel.ready(key=ptt.key_said, code=ptt.chosen, deaf=ptt.deaf)
    show.state(panel.IDLE)


def start():
    """LOAD EVERY MODEL UP FRONT, SO NO TAKE PAYS FOR IT LATER."""
    show.note("Loading models")

    mcps.start()  # IN THE BACKGROUND. THE TOOLS ARE BOUND ALREADY, FROM LAST TIME.

    try:
        ears.load_model()
    except ears.EarsError:
        show.note("Downloading speech model, this may take a few minutes...")
        ears.fetch()
        show.note("Done.")
        ears.load_model()

    ears.warm()

    speech = voice.engines.part()
    spoken = speech.target_language()

    if spoken != "auto" and not speech.has_language(spoken):
        show.note("Downloading voice model, this may take a few minutes...")
        speech.fetch(spoken)
        show.note("Done.")

    try:
        speech.find()
    except voice.VoiceError:
        show.note("Downloading voice model, this may take a few minutes...")
        speech.fetch(spoken)
        show.note("Done.")

    speaker, mute = voice.create()

    if mute:
        show.note(mute)

    speaker.warm()

    try:
        happy = brain.Happy()
    except brain.LLMError as error:
        raise SystemExit(error)

    caveat = brain.caveat()

    if caveat:
        show.note(caveat)

    try:
        happy.warm()
    except brain.LLMError as error:
        show.note(error)

    return happy, speaker


def listen(recorder, ptt, happy, speaker):
    """ONE TURN PER LAP: HOLD, SPEAK, RELEASE, HEAR AN ANSWER."""
    while True:
        audio = capture(recorder, ptt)

        if audio is None:
            continue

        stop_turn(happy, speaker)

        with taking:
            happy.start_turn()
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

    stop_turn(happy, speaker)

    with taking:
        happy.start_turn()
        show.begin()
        show.said(text)
        respond(happy, speaker, text)
        show.end()


def distant(happy, text):
    """A TURN THAT ARRIVED IN A MESSAGE. NOTHING IS SPOKEN INTO THE ROOM FOR IT.

    NOBODY IS AT THE MACHINE TO ANSWER conscience, SO IT IS TOLD NO FOR THE LENGTH
    OF THE TURN. HAPPY LOOKS AND ANSWERS FROM AFAR; HE DOES NOT DO THE UNDOABLE.
    """
    with taking:
        show.begin()
        show.said(text)

        was = conscience.handler
        conscience.asks(lambda what, why: False)

        try:
            said = "".join(piece for piece in stream(happy, text))
        finally:
            conscience.asks(was)
            show.end()

        return said


def stream(happy, text):
    try:
        for piece in happy.say_streaming(text):
            show.piece(piece)

            yield piece
    except brain.LLMError as error:
        show.trouble(error)

        yield str(error)


def stop_turn(happy, speaker):
    happy.stop()
    speaker.stop()


def respond(happy, speaker, speech, audio=None):
    speaker.refit()  # A DIFFERENT ENGINE WAS PICKED WHILE THE LAST TURN RAN.
    show.opening()

    try:
        # SPOKEN AND PRINTED OFF THE ONE STREAM: THE SPEAKER HOLDS EACH PIECE
        # BACK UNTIL IT HAS A WHOLE SENTENCE, THE PRINTING DOES NOT WAIT.
        for piece in speaker.say(happy.say_streaming(speech, audio=audio)):
            show.piece(piece)
    except brain.LLMError as error:
        show.trouble(error)


def shut(speaker, recorder, ptt):
    mcps.stop()  # BEFORE THE REST: IT IS THE ONLY PART THAT OWNS OTHER PROCESSES.
    speaker.close()
    recorder.close()
    ptt.stop()


def leave(speaker, recorder, ptt):
    """THE WINDOW ASKED US TO GO, AND THE MAIN THREAD IS SAT ON A KEY PRESS."""
    shut(speaker, recorder, ptt)
    os._exit(0)


if __name__ == "__main__":
    main()