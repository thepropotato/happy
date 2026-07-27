"""SILENCES THE LIBRARIES. CALL configure() BEFORE ANYTHING IMPORTS WHISPERX."""

import logging
import os
import warnings

LEVEL = logging.ERROR

NOISY = (
    "whisperx",
    "lightning",
    "lightning.pytorch",
    "lightning.fabric",
    "lightning_fabric",
    "pytorch_lightning",
    "pyannote",
    "pyannote.audio",
    "speechbrain",
    "faster_whisper",
    "transformers",
    "torio",
    "numba",
    "urllib3",
    "huggingface_hub",
    "filelock",
)

done = False


def configure(level=LEVEL):
    global done

    warnings.filterwarnings("ignore")
    variables()
    claim_whisperx(level)
    load_lightning()

    logging.basicConfig(level=level, format="%(message)s")

    for name in NOISY:
        logging.getLogger(name).setLevel(level)

    done = True


def variables():
    # READ AT IMPORT TIME BY THEIR LIBRARIES, SO SET THEM BEFORE THEY LOAD.
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


def claim_whisperx(level):
    # WHISPERX CALLS ITS OWN setup_logging() AT INFO, BUT ONLY IF ITS LOGGER HAS
    # NO HANDLERS YET. A NULL HANDLER MAKES IT LEAVE OUR LEVEL ALONE.
    logger = logging.getLogger("whisperx")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    logger.setLevel(level)
    logger.propagate = True


def load_lightning():
    # lightning.pytorch RESETS ITS LOGGER TO INFO ON IMPORT, SO IMPORT IT NOW AND
    # LET THE CLAMP ABOVE LAND AFTERWARDS.
    try:
        import lightning.pytorch  # noqa: F401
    except ImportError:
        pass


def configured():
    return done
