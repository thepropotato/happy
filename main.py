"""
COMPLETELY LOCAL VOICE ASSISTANT
"""

import logs

logs.configure()  # MUST RUN BEFORE THE IMPORTS BELOW PULL IN WHISPERX.

from audio.recorder import Recorder
from audio.stt import load_model, transcribe_speech
from controls import PushToTalk


def main():
    print("Loading model")
    load_model()

    recorder = Recorder()
    ptt = PushToTalk()

    print(f"HOLD {ptt.key_name} TO TALK. CTRL+C TO QUIT.")

    try:
        while True:
            ptt.reset()  # IGNORE THE KEYBOARD FROM WHILE THE LAST TAKE WAS TRANSCRIBING.
            ptt.wait_press()

            print("Listening")
            recorder.start()

            ptt.wait_release()
            audio_file_path = recorder.stop()

            if audio_file_path is None:
                print("Too short, nothing saved")
                continue

            speech = transcribe_speech(audio_file_path)
            print(speech if speech else "Nothing heard")

    except KeyboardInterrupt:
        print("\nBye")
    finally:
        recorder.close()
        ptt.stop()


if __name__ == "__main__":
    main()
