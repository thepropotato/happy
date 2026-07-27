"""COMPLETELY LOCAL VOICE ASSISTANT.

    hold key ─► record ─► transcribe ─► think ─► speak
      ears        ears        ears       brain    voice
                                           │
                                           ▼
                                     hands and eyes
"""

from face import silence

silence.configure()  # MUST RUN BEFORE THE IMPORTS BELOW PULL IN WHISPERX.

import time

import brain
import ears
import voice
from face import console


def main():
    happy, speaker = start()

    recorder = ears.Recorder()

    # THE KEY GOING DOWN CUTS HAPPY OFF MID SENTENCE. SOMEONE WHO HAS STARTED
    # TALKING HAS STOPPED LISTENING, AND THE MIC MUST NOT HEAR HIM EITHER.
    ptt = ears.PushToTalk(on_press=speaker.stop)

    # THE TERMINAL WANTS TO KNOW WHERE EACH TURN'S TIME WENT.
    brain.watches(console.step)

    console.note(f"Hold {ptt.key_name} to talk. Ctrl+C to quit.")

    try:
        listen(recorder, ptt, happy, speaker)
    except KeyboardInterrupt:
        console.note("\nBye")
    finally:
        speaker.close()
        recorder.close()
        ptt.stop()


def start():
    """LOAD EVERY MODEL UP FRONT, SO NO TAKE PAYS FOR IT LATER."""
    console.note("Loading models")
    ears.load_model()

    speaker, mute = voice.create()

    if mute:  # HAPPY STILL ANSWERS, HE JUST ANSWERS IN WRITING.
        console.note(mute)

    speaker.warm()

    try:
        happy = brain.Happy()
    except brain.LLMError as error:  # NO BACKEND AT ALL. NOTHING TO DO BUT SAY SO.
        raise SystemExit(error)

    # A BACKEND THAT CANNOT BE TOLD A CONTEXT LENGTH SAYS SO NOW, RATHER THAN
    # LETTING IT BE FOUND OUT THROUGH ANSWERS THAT QUIETLY GET WORSE.
    caveat = brain.caveat()

    if caveat:
        console.note(caveat)

    try:
        happy.warm()
    except brain.LLMError as error:  # HE STILL HEARS, HE JUST CANNOT ANSWER YET.
        console.note(error)

    return happy, speaker


def listen(recorder, ptt, happy, speaker):
    """ONE TURN PER LAP: HOLD, SPEAK, RELEASE, HEAR AN ANSWER."""
    while True:
        audio = capture(recorder, ptt)

        if audio is None:  # THE KEY WAS BRUSHED. NOT A TURN, SAY NOTHING.
            continue

        console.begin()

        started = time.perf_counter()
        speech = ears.transcribe(audio)
        heard = time.perf_counter() - started

        if not speech:
            console.trouble("nothing heard")
            console.end()
            continue

        console.said(speech, heard)
        respond(happy, speaker, speech, audio)
        console.end()


def capture(recorder, ptt):
    """THE WAV, OR None IF THE KEY WAS ONLY BRUSHED."""
    ptt.reset()  # IGNORE THE KEYBOARD FROM WHILE THE LAST TAKE WAS TRANSCRIBING.
    ptt.wait_press()

    console.listening()
    recorder.start()

    ptt.wait_release()

    return recorder.stop()


def respond(happy, speaker, speech, audio=None):
    console.opening()

    try:
        # SPOKEN AND PRINTED OFF THE ONE STREAM. THE SPEAKER HOLDS EACH PIECE
        # BACK UNTIL IT HAS A WHOLE SENTENCE, THE PRINTING DOES NOT WAIT. THE WAV
        # GOES IN THE CONVERSATION SO A LINE CAN BE HEARD AGAIN LATER.
        for piece in speaker.say(happy.say_streaming(speech, audio=audio)):
            console.piece(piece)
    except brain.LLMError as error:  # A DEAD MODEL MUST NOT END THE SESSION.
        console.trouble(error)


if __name__ == "__main__":
    main()
