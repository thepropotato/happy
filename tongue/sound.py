"""WHICH LANGUAGE A PIECE OF SOUND IS IN, WHEN THE WORDS THEMSELVES NEVER CAME BACK."""

import threading
import wave
from pathlib import Path

import numpy as np

from face import show

MODELS = Path(__file__).resolve().parent.parent / "models" / "voxlingua107"
SOURCE = "speechbrain/lang-id-voxlingua107-ecapa"

NETWORK = MODELS / "lang.onnx"
BANK = MODELS / "mel.npy"
LABELS = MODELS / "labels.txt"

# HALF A DOWNLOAD IS NOT A MODEL.
PARTS = (NETWORK, BANK, LABELS)

# SPEECHBRAIN'S OWN ECAPA, TRACED TO ONNX BY tongue.exporting AND PUT UP ON A RELEASE.
RELEASE = "https://github.com/thepropotato/happy/releases/download/voxlingua107-v1"

RATE = 16000

# THE FBANK THE MODEL WAS TRAINED ON: A 25ms WINDOW EVERY 10ms, INTO SIXTY MEL BANDS.
WINDOW = 400
STRIDE = 160
MELS = 60

# THE PERIODIC HAMMING, WHICH IS THE ONE TORCH MADE WHEN THE MODEL WAS TRAINED.
SHAPE = np.hamming(WINDOW + 1)[:WINDOW].astype(np.float32)

# QUIET BANDS GO TO MINUS INFINITY IN A LOG, AND EIGHTY DECIBELS DOWN IS SILENCE ENOUGH.
FLOOR = 1e-10
RANGE = 80.0

# UNDER A SECOND IT ANSWERS CONFIDENTLY AND WRONGLY. A SHORT TAKE IS NOT WORTH ASKING ABOUT.
SHORTEST = 1.0

model = None
loading = threading.Lock()
getting = False


def whole():
    return MODELS.is_dir() and all(part.exists() for part in PARTS)


def load_model():
    """THE GRAPH, THE MEL WEIGHTS AND THE NAMES, ONCE."""
    global model

    with loading:
        if model is None:
            import onnxruntime

            session = onnxruntime.InferenceSession(
                str(NETWORK), providers=["CPUExecutionProvider"]
            )
            named = LABELS.read_text(encoding="utf-8").split("\n")

            model = (session, np.load(BANK), named)

    return model


def sound(audio):
    """SIXTEEN KILOHERTZ MONO FLOATS, WHATEVER SHAPE THEY ARRIVED IN."""
    if isinstance(audio, np.ndarray):
        return audio.astype(np.float32)

    with wave.open(str(audio), "rb") as file:
        rate = file.getframerate()
        channels = file.getnchannels()
        frames = np.frombuffer(file.readframes(file.getnframes()), dtype=np.int16)

    heard = frames.astype(np.float32) / 32768

    if channels > 1:
        heard = heard.reshape(-1, channels).mean(axis=1)

    return heard if rate == RATE else evenly(heard, rate)


def evenly(heard, rate):
    """THE MODEL WAS TRAINED AT ONE RATE AND HEARS A PITCH SHIFT AS A DIFFERENT LANGUAGE."""
    wanted = int(round(len(heard) * RATE / rate))

    if wanted < 1:
        return np.zeros(0, dtype=np.float32)

    # WHERE EACH NEW SAMPLE FALLS AMONG THE OLD ONES, AND WHAT WAS THERE AT THAT MOMENT.
    when = np.linspace(0, len(heard) - 1, wanted, dtype=np.float32)

    return np.interp(when, np.arange(len(heard), dtype=np.float32), heard).astype(np.float32)


def features(heard, bank):
    """THE SIXTY LOG MEL BANDS THE NETWORK WAS TRAINED ON, FRAME BY FRAME."""
    # THE FIRST FRAME IS CENTRED ON THE FIRST SAMPLE, SO HALF A WINDOW GOES ON EACH END.
    padded = np.pad(heard, WINDOW // 2, mode="constant")
    count = 1 + (len(padded) - WINDOW) // STRIDE

    # ONE VIEW OVER THE SAMPLES INSTEAD OF A COPY PER FRAME.
    step = padded.strides[0]
    frames = np.lib.stride_tricks.as_strided(
        padded, (count, WINDOW), (step * STRIDE, step), writeable=False
    )

    spectrum = np.abs(np.fft.rfft(frames * SHAPE, WINDOW, axis=-1)) ** 2
    banded = spectrum.astype(np.float32) @ bank

    loud = 10 * np.log10(np.clip(banded, FLOOR, None))
    loud = np.maximum(loud, loud.max() - RANGE)

    # WHAT SPEECHBRAIN CALLS SENTENCE NORMALISATION: EVERY BAND ABOUT ITS OWN AVERAGE, SO
    # A QUIET ROOM AND A LOUD ONE LOOK THE SAME BY THE TIME THE NETWORK SEES THEM.
    return (loud - loud.mean(axis=0, keepdims=True))[None].astype(np.float32)


def aloud(audio):
    """THE LANGUAGE IT WAS SAID IN, OR NOTHING WHERE THAT CANNOT BE ANSWERED."""
    heard = sound(audio)

    if heard is None or len(heard) / RATE < SHORTEST:
        return None

    if not whole():
        collect()
        return None

    try:
        session, bank, named = load_model()
        scores = session.run(None, {"feats": features(heard, bank)})[0][0]

        return named[int(np.argmax(scores))].split(":")[0]
    except Exception as error:
        show.trouble(f"The language detector would not answer, going on without it ({error})")
        return None


def fetch():
    """THE THREE FILES, OFF THE RELEASE. EIGHTY FIVE MEGABYTES, THE ONE TIME."""
    import urllib.request

    MODELS.mkdir(parents=True, exist_ok=True)

    for part in PARTS:
        if part.exists():
            continue

        # BESIDE IT, THEN MOVED: A DOWNLOAD CUT OFF HALFWAY MUST NOT LOOK LIKE A MODEL.
        half = part.with_suffix(part.suffix + ".part")

        urllib.request.urlretrieve(f"{RELEASE}/{part.name}", half)
        half.replace(part)

    return MODELS


def collect():
    """GET IT BEHIND THE CONVERSATION. ONE ATTEMPT A RUN, AND THIS TAKE GOES ON WITHOUT IT."""
    global getting

    if getting:
        return

    getting = True
    show.note("Getting the language detector. This take is heard as it is.")

    threading.Thread(target=pull, daemon=True).start()


def pull():
    try:
        fetch()
        load_model()
        show.note("The language detector is ready.")
    except Exception as error:
        show.trouble(f"Could not get the language detector ({error})")
