"""COMPLETELY LOCAL VOICE ASSISTANT.

    say his name ─► record ─► transcribe ─► think ─► speak
        ears         ears        ears       brain    voice
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

import brain
import ears
import mcps
import memory
import voice
from mcps.servers.whatsapp import chatting
from face import console, handing, log, orders, panel, show

SERVE = "--serve"

# ONE TURN AT A TIME. A LINE TYPED INTO THE WINDOW ARRIVES ON ITS OWN THREAD.
taking = threading.Lock()


def main():
    windowed = SERVE in sys.argv

    log.opened("with the window" if windowed else "in a terminal")

    show.attach(panel if windowed else console)
    show.attach(log)  # THE ONE FACE THAT IS STILL THERE TOMORROW.
    show.state(panel.LOADING)

    happy, speaker = start()

    recorder = ears.Recorder()

    # NOTHING IS LISTENED TO WHILE HAPPY IS THE LOUDEST THING IN THE ROOM.
    waking = ears.Waking(recorder, busy=speaker.talking)

    brain.watches(show.step)

    chatting.listen(lambda text, context=None: distant(happy, text, context))

    thrown = memory.prune(recorder.recordings)  # ONLY IF A SETTING SAYS TO.

    if thrown:
        show.note(f"Threw away {thrown}")

    if windowed:
        attend(happy, speaker, recorder, waking)
    else:
        show.note(f'Say "{waking.phrase()}" to talk. Ctrl+C to quit.')

    try:
        listen(waking, happy, speaker)
    except KeyboardInterrupt:
        show.note("\nBye")
    finally:
        shut(speaker, recorder, waking)


def attend(happy, speaker, recorder, waking):
    """HAND THE WINDOW THE FEW THINGS ONLY THIS FILE CAN DO."""
    # SENT AGAIN WHENEVER A KNOB MOVES: THE NAME HAPPY WAKES TO IS ONE OF THEM,
    # AND A HINT STILL NAMING THE OLD ONE IS A HINT THAT IS WRONG.
    def ready():
        panel.ready(wake=waking.phrase(), amiss=blocked())

    orders.serve(
        forget=happy.forget,
        say=lambda text: typed_soon(happy, speaker, text),
        stop=lambda: stop_turn(happy, speaker),
        ready=ready,
        quit=lambda: leave(speaker, recorder, waking),
    )

    ready()
    show.state(panel.IDLE)


def blocked():
    """THE ONE THING WORTH A BANNER: A PERMISSION HAPPY IS STILL WAITING ON.

    HEARING NO LONGER NEEDS ONE — HIS NAME IS SAID INTO A MICROPHONE AND NOT
    TYPED — BUT READING A WINDOW AND CLICKING IN IT BOTH STILL DO, AND THE
    BUTTON THAT FIXES IT IS THE SAME BUTTON IT ALWAYS WAS.
    """
    from eyes import attention

    if not (attention.on_mac() or attention.on_windows()):
        return ""

    return attention.allowed() or ""


def start():
    """LOAD EVERY MODEL UP FRONT, SO NO TAKE PAYS FOR IT LATER."""
    show.note("Loading models")

    mcps.start()  # IN THE BACKGROUND. THE TOOLS ARE BOUND ALREADY, FROM LAST TIME.

    from memory import embedding
    embedding.warm()

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


def listen(waking, happy, speaker):
    """ONE TURN PER LAP: HIS NAME, WHAT WAS ASKED, AN ANSWER.

    THE HEARING IS ALL DONE BY THE TIME ANYTHING GETS HERE. WHAT ARRIVES IS A
    QUESTION SOMEBODY PUT TO HAPPY BY NAME, AND EVERY OTHER SOUND IN THE ROOM
    HAS ALREADY BEEN LISTENED TO AND FORGOTTEN.
    """
    while True:
        heard = waking.next()

        if heard is None:  # NOBODY SAID ANYTHING. GO ROUND, SO CTRL+C LANDS.
            continue

        stop_turn(happy, speaker)

        with taking:
            happy.start_turn()
            spoken(happy, speaker, heard)


def spoken(happy, speaker, heard):
    show.begin()
    show.said(heard.text, heard.seconds)
    respond(happy, speaker, heard.text, heard.audio)
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


def typed_soon(happy, speaker, text):
    threading.Thread(target=typed, args=(happy, speaker, text), daemon=True).start()


def distant(happy, text, context=None):
    """A TURN THAT ARRIVED IN A MESSAGE. NOTHING IS SPOKEN INTO THE ROOM FOR IT.

    GIVES BACK WHAT TO SAY AND ANY PICTURES TO SEND WITH IT. THIS IS THE ONLY KIND
    OF TURN THAT CAN CARRY ONE: WHOEVER ASKED IS NOT LOOKING AT THE SCREEN.

    context IS WHOSE CHAT IT CAME FROM, WHICH ONLY THE MODEL NEEDS. WHAT IS SHOWN
    IS WHAT THE PERSON ACTUALLY WROTE.
    """
    with taking:
        show.begin()
        show.said(text)

        handing.opened()

        try:
            said = "".join(piece for piece in stream(happy, text, context))
        finally:
            show.end()
            pictures = handing.closed()  # IN HERE, OR A THROW LEAVES THE TURN OPEN FOREVER.

        return said, pictures


def stream(happy, text, context=None):
    try:
        for piece in happy.say_streaming(text, context):
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


def shut(speaker, recorder, waking):
    mcps.stop()  # BEFORE THE REST: IT IS THE ONLY PART THAT OWNS OTHER PROCESSES.
    waking.stop()  # BEFORE THE RECORDER, WHOSE BLOCKS IT IS STILL BEING HANDED.
    speaker.close()
    recorder.close()
    log.closed()  # LAST, SO ANYTHING THE REST OF THIS SAID IS IN THERE.


def leave(speaker, recorder, waking):
    """THE WINDOW ASKED US TO GO, AND THE MAIN THREAD IS SAT WAITING TO BE SPOKEN TO."""
    shut(speaker, recorder, waking)
    os._exit(0)


if __name__ == "__main__":
    main()