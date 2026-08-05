"""WHICH LANGUAGE A PIECE OF SOUND IS IN, WHEN THE WORDS THEMSELVES NEVER CAME BACK."""

import logging
import threading
import wave
from pathlib import Path

import numpy as np

from face import show, silence

MODELS = Path(__file__).resolve().parent.parent / "models" / "voxlingua107"
SOURCE = "speechbrain/lang-id-voxlingua107-ecapa"

# HALF A DOWNLOAD IS NOT A MODEL.
PARTS = ("hyperparams.yaml", "embedding_model.ckpt", "classifier.ckpt", "label_encoder.ckpt")

RATE = 16000

# UNDER A SECOND IT ANSWERS CONFIDENTLY AND WRONGLY. A SHORT TAKE IS NOT WORTH ASKING ABOUT.
SHORTEST = 1.0

model = None
getting = False


def whole():
    return MODELS.is_dir() and all((MODELS / part).exists() for part in PARTS)


def load_model():
    global model

    if model is None:
        from speechbrain.inference.classifiers import EncoderClassifier

        # IT NARRATES EVERY FILE IT OPENS, ON LOGGERS THAT SOME OF THEM ONLY COME INTO
        # BEING PART WAY THROUGH THE LOAD, SO LEVELS SET BEFOREHAND CANNOT CATCH THEM ALL.
        # NOTHING OF HAPPY'S OWN GOES THROUGH logging, SO SHUTTING IT LOSES NOTHING.
        silence.hush_tree("speechbrain")
        logging.disable(logging.WARNING)

        try:
            model = EncoderClassifier.from_hparams(source=SOURCE, savedir=str(MODELS))
        finally:
            logging.disable(logging.NOTSET)

        # ONLY THE HIGHEST SCORE IS EVER READ, SO HOW MANY THERE ARE IS NOT OURS TO PROMISE.
        # SAYING SO IS WHAT STOPS IT WARNING ABOUT THE COUNT THE FIRST TIME IT IS ASKED.
        model.hparams.label_encoder.ignore_len()

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
    import torch
    import torchaudio

    return torchaudio.functional.resample(torch.from_numpy(heard), rate, RATE).numpy()


def aloud(audio):
    """THE LANGUAGE IT WAS SAID IN, OR NOTHING WHERE THAT CANNOT BE ANSWERED."""
    heard = sound(audio)

    if heard is None or len(heard) / RATE < SHORTEST:
        return None

    if not whole():
        collect()
        return None

    try:
        import torch

        found = load_model()
        scores = found.classify_batch(torch.from_numpy(heard).unsqueeze(0))[0][0]

        return found.hparams.label_encoder.ind2lab[int(torch.argmax(scores))].split(":")[0]
    except Exception as error:
        show.trouble(f"The language detector would not answer, going on without it ({error})")
        return None


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
        load_model()
        show.note("The language detector is ready.")
    except Exception as error:
        show.trouble(f"Could not get the language detector ({error})")
