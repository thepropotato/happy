"""COMPLETELY LOCAL VOICE ASSISTANT."""

import os
import subprocess
import sys
from pathlib import Path

from face import silence

SERVE = "--serve"  # THE WINDOW PASSES THIS TO THE HAPPY IT STARTS.
TERMINAL = "--terminal"  # NO WINDOW AT ALL: HOLD THE KEY AT A PROMPT.

WINDOW = Path(__file__).resolve().parent / "face" / "window"

# npm WRITES A .cmd SHIM ON WINDOWS AND A PLAIN LINK EVERYWHERE ELSE.
ELECTRON = "electron.cmd" if os.name == "nt" else "electron"

MISSING = """The window has no dependencies yet. Once, then this will work:

    cd face/window && npm install
"""


# SPAWNS THE WINDOW AND WAITS ON IT, AND IT COMES BACK FOR THIS FILE WITH --serve.
def launch():
    electron = WINDOW / "node_modules" / ".bin" / ELECTRON

    if not electron.exists():
        sys.exit(MISSING)

    # VS CODE'S TERMINAL EXPORTS ELECTRON_RUN_AS_NODE=1, AND INHERITING IT WOULD START
    # ELECTRON AS PLAIN NODE WITH NO WINDOW — THE STRIP face/window/start.js ALSO DOES.
    clean = {name: value for name, value in os.environ.items() if name != "ELECTRON_RUN_AS_NODE"}

    return subprocess.call([str(electron), ".", *sys.argv[1:]], cwd=WINDOW, env=clean)


# STARTED BY HAND THIS IS ONLY THE LAUNCHER, AND IT MUST NOT PAY FOR THE IMPORTS BELOW.
if SERVE not in sys.argv and TERMINAL not in sys.argv:
    raise SystemExit(launch())

silence.configure()  # MUST RUN BEFORE THE IMPORTS BELOW OPEN AN ONNX SESSION.

from bones import systems

systems.heal()  # BEFORE ANYTHING GOES LOOKING FOR A PROGRAM, AND THE WINDOW STARTS HIM WITH ALMOST NO PATH.

import threading

import brain
import ears
import heart
import mcps
import memory
import voice
from face import allowing, console, handing, log, requests, show, telling
from mcps.servers.whatsapp import chatting

# ONE TURN AT A TIME. A LINE TYPED INTO THE WINDOW ARRIVES ON ITS OWN THREAD.
taking = threading.Lock()


def main():
    windowed = SERVE in sys.argv

    if windowed:
        telling.only()  # BEFORE ANY LIBRARY GETS A CHANCE TO PRINT ON THE CHANNEL.

    log.opened("with the window" if windowed else "in a terminal")

    show.attach(telling if windowed else console)
    show.attach(log)  # THE ONE FACE THAT IS STILL THERE TOMORROW.
    show.state(telling.LOADING)

    # BEFORE THE MODELS, SO THE DIALOGS ARE ANSWERED WHILE THE LOADING HAPPENS ANYWAY.
    allowing.asked()

    happy, speaker = start()

    recorder = ears.Recorder()

    # SOMEBODY WHO HAS STARTED TALKING HAS STOPPED LISTENING.
    key = held(speaker)

    # THE ONLY WAY IN: NOTHING IS HEARD UNTIL THE KEY GOES DOWN.
    holding = ears.Holding(recorder, key=key)

    brain.watches(show.step)
    brain.troubles(show.trouble)
    brain.doings(show.working)

    chatting.listen(lambda text, context=None: distant(happy, text, context))

    # THE ONE THING ONLY THIS FILE CAN HAND OVER: SPEAKING WHEN NOBODY ASKED.
    heart.start(lambda text: aloud(speaker, text))

    thrown = memory.prune(recorder.recordings)  # ONLY IF A SETTING SAYS TO.

    if thrown:
        show.note(f"Threw away {thrown}")

    if windowed:
        attend(happy, speaker, recorder, holding)
    else:
        show.note(f"{inviting(key)} Ctrl+C to quit.")

        if key and key.deaf:
            show.note(ears.DEAF)

    try:
        listen(holding, happy, speaker)
    except KeyboardInterrupt:
        show.note("\nBye")
    finally:
        shut(speaker, recorder, holding)


def held(speaker):
    """THE KEY HE WAKES TO, OR None WHERE THE OS WILL NOT HAND ONE OVER."""
    try:
        return ears.PushToTalk(on_press=speaker.stop)
    except Exception as error:
        show.trouble(f"No hold to talk key ({error})")

        return None


def inviting(key):
    """THE WAY IN, IN WORDS, FOR SOMEBODY WHO HAS JUST STARTED HIM."""
    if not key:
        return "Nothing can be heard without the key, so type to him."

    return f"Hold {key.key_name} to talk."


def attend(happy, speaker, recorder, holding):
    """HAND THE WINDOW THE FEW THINGS ONLY THIS FILE CAN DO."""
    key = holding.key

    # SENT AGAIN WHENEVER A KNOB MOVES: THE KEY HAPPY WAKES TO IS ONE OF THEM, AND
    # A HINT STILL NAMING THE OLD ONE IS A HINT THAT IS WRONG.
    def ready():
        telling.ready(
            key=key.key_said if key else "",
            amiss=blocked() or (ears.DEAF if key and key.deaf else ""),
        )

    requests.serve(
        forget=happy.forget,
        say=lambda text: typed_soon(happy, speaker, text),
        preview=lambda name=None: preview(speaker, name),
        stop=lambda: stop_turn(happy, speaker),
        ready=ready,
        quit=lambda: leave(speaker, recorder, holding),
    )

    ready()
    show.state(telling.IDLE)


def preview(speaker, name=None):
    """ONE LINE IN ONE VOICE OFF THE LIST, SO PICKING ONE IS NOT PICKING BLIND."""
    speaker.refit()  # THE ENGINE MAY HAVE CHANGED SINCE THE LAST TURN, AND THE VOICE WITH IT.
    speaker.stop()  # AUDITIONING IS TAPPING DOWN A LIST, NOT QUEUEING ONE UP.
    speaker.sample(voice.sample(name), name)


def blocked():
    """WHAT THE SYSTEM IS STILL WITHHOLDING, IN ONE LINE, FOR THE BANNER."""
    from face import allowing

    short = allowing.missing()

    if not short:
        return ""

    return f"{joined(short)} still to allow. Settings, Permissions."


def joined(names):
    """a, b and c."""
    if len(names) == 1:
        return names[0]

    return f"{', '.join(names[:-1])} and {names[-1]}"


def start():
    """LOAD EVERY MODEL UP FRONT, SO NO TAKE PAYS FOR IT LATER."""
    show.note("Loading models")

    mcps.start()  # IN THE BACKGROUND. THE TOOLS ARE BOUND ALREADY, FROM LAST TIME.

    from memory import embedding
    embedding.warm()

    # THE SAME MODEL, ALREADY ON ITS WAY. THIS ONLY EMBEDS THE LINES IT COMPARES AGAINST.
    from hands.apps import telling
    telling.warm()

    try:
        ears.load_model()
    except ears.EarsError:
        show.note("Downloading speech model, this may take a few minutes...")
        ears.fetch()
        show.note("Done.")
        ears.load_model()

    ears.warm()

    speech = voice.engines.part()

    try:
        speech.find()
    except voice.VoiceError:
        show.note("Downloading voice model, this may take a few minutes...")
        speech.fetch()
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


def listen(holding, happy, speaker):
    """ONE TURN PER LAP: THE KEY, WHAT WAS ASKED, AN ANSWER."""
    while True:
        heard = holding.next()

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


def aloud(speaker, text):
    """SOMETHING HAPPY SAYS THAT NOBODY ASKED FOR — A REMINDER COMING ROUND.

    IT TAKES THE SAME LOCK A TURN DOES, SO IT WAITS ITS GO RATHER THAN TALKING OVER ONE."""
    said = (text or "").strip()

    if not said:
        return

    with taking:
        speaker.refit()
        show.waking()
        show.unprompted(said)  # THE CAPSULE COMES UP OFF THIS.
        memory.begin(unprompted=True)
        show.state(telling.SPEAKING)

        try:
            for piece in speaker.say([said]):
                pass

            speaker.wait()
        finally:
            memory.close(said)
            show.end()


def typed_soon(happy, speaker, text):
    threading.Thread(target=typed, args=(happy, speaker, text), daemon=True).start()


def distant(happy, text, context=None):
    """A TURN THAT ARRIVED IN A MESSAGE."""
    with taking:
        show.begin()
        show.said(text)

        # THE WINDOW OPENS EVERY TURN ON "MAKING IT OUT", WHICH IS THE EARS WORKING OUT WHAT
        # WAS SAID.
        show.opening()

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


def shut(speaker, recorder, holding):
    heart.stop()  # BEFORE THE SPEAKER, WHICH IT MAY BE PART WAY THROUGH SAYING SOMETHING ON.
    mcps.stop()  # BEFORE THE REST: IT IS THE ONLY PART THAT OWNS OTHER PROCESSES.
    holding.stop()  # BEFORE THE RECORDER, WHICH IT MAY BE PART WAY THROUGH A TAKE ON.
    speaker.close()
    recorder.close()
    log.closed()  # LAST, SO ANYTHING THE REST OF THIS SAID IS IN THERE.


def leave(speaker, recorder, holding):
    """THE WINDOW ASKED US TO GO, AND THE MAIN THREAD IS SAT WAITING TO BE SPOKEN TO."""
    shut(speaker, recorder, holding)
    os._exit(0)


if __name__ == "__main__":
    main()
