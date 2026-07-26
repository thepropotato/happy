"""
COMPLETELY LOCAL VOICE ASSISTANT
"""

import logs

logs.configure()  # MUST RUN BEFORE THE IMPORTS BELOW PULL IN WHISPERX.

import time

import brain
import chat
import console
from agents import browser
from audio import tts
from audio.recorder import Recorder
from audio.stt import load_model, transcribe_speech
from controls import PushToTalk

QUIET_POLL_SECONDS = 0.2  # HOW OFTEN A WAITING ANNOUNCEMENT CHECKS FOR A GAP.


def main():
    happy, speaker = start()

    recorder = Recorder()

    # THE KEY GOING DOWN CUTS HAPPY OFF MID SENTENCE. SOMEONE WHO HAS STARTED
    # TALKING HAS STOPPED LISTENING, AND THE MIC MUST NOT HEAR HIM EITHER.
    ptt = PushToTalk(on_press=speaker.stop)

    # A BROWSER ERRAND TAKES MINUTES, SO IT REPORTS BACK UNASKED WHEN IT LANDS.
    browser.announces(announcing(speaker, recorder))

    # AND THE TERMINAL WANTS TO KNOW WHERE EACH TURN'S TIME WENT.
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
    load_model()

    speaker, mute = tts.create()

    if mute:  # HAPPY STILL ANSWERS, HE JUST ANSWERS IN WRITING.
        console.note(mute)

    speaker.warm()

    try:
        happy = brain.Happy()
    except brain.LLMError as error:  # NO BACKEND AT ALL. NOTHING TO DO BUT SAY SO.
        raise SystemExit(error)

    # A BACKEND THAT CANNOT BE TOLD A CONTEXT LENGTH SAYS SO NOW, RATHER THAN
    # LETTING IT BE FOUND OUT LATER THROUGH ANSWERS THAT QUIETLY GET WORSE.
    caveat = brain.caveat()

    if caveat:
        console.note(caveat)

    try:
        happy.warm()
    except brain.LLMError as error:  # THE ASSISTANT STILL HEARS, IT JUST CANNOT ANSWER YET.
        console.note(error)

    return happy, speaker


def announcing(speaker, recorder):
    """HOW WORK THAT FINISHES ON ITS OWN GETS A WORD IN.

    CALLED FROM THE JOB'S THREAD, NOT THIS ONE, SO IT WAITS FOR A GAP FIRST.
    CUTTING ACROSS SOMEONE MID SENTENCE IS WORSE THAN BEING LATE BY A SENTENCE.
    """

    def speak(words):
        while recorder.is_recording():
            time.sleep(QUIET_POLL_SECONDS)

        chat.replied(words, unprompted=True)
        console.unprompted(words)
        speaker.feed(words)
        speaker.flush()

    return speak


def listen(recorder, ptt, happy, speaker):
    """ONE TURN PER LAP: HOLD, SPEAK, RELEASE, HEAR AN ANSWER."""
    while True:
        audio_file_path = capture(recorder, ptt)

        if audio_file_path is None:  # THE KEY WAS BRUSHED. NOT A TURN, SAY NOTHING.
            continue

        console.begin()

        started = time.perf_counter()
        speech = transcribe_speech(audio_file_path)
        heard = time.perf_counter() - started

        if not speech:
            console.trouble("nothing heard")
            console.end()
            continue

        console.said(speech, heard)
        respond(happy, speaker, speech, audio_file_path)
        console.end()


def capture(recorder, ptt):
    """RETURNS THE WAV, OR None IF THE KEY WAS ONLY BRUSHED."""
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
        # BACK UNTIL IT HAS A WHOLE SENTENCE, THE PRINTING DOES NOT WAIT.
        # THE WAV GOES IN THE CONVERSATION SO A LINE CAN BE HEARD AGAIN LATER.
        for piece in speaker.say(happy.say_streaming(speech, audio=audio)):
            console.piece(piece)
    except brain.LLMError as error:  # A DEAD MODEL MUST NOT END THE SESSION.
        console.trouble(error)


if __name__ == "__main__":
    main()
