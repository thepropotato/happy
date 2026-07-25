"""
CENTRAL LOGGING CONFIG.

Call configure() as the very first thing in main.py, before importing anything
that pulls in whisperx / torch / lightning.
"""

import logging
import os
import warnings

LEVEL = logging.ERROR

# THIRD PARTY LOGGERS THAT CHATTER AT INFO DURING MODEL LOAD AND INFERENCE.
NOISY_LOGGERS = (
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

_configured = False


def configure(level=LEVEL):
    global _configured

    _silence_warnings()
    _silence_env()
    _claim_whisperx_logger(level)
    _silence_lightning()

    logging.basicConfig(level=level, format="%(message)s")

    for name in NOISY_LOGGERS:
        logging.getLogger(name).setLevel(level)

    _configured = True


def _silence_warnings():
    warnings.filterwarnings("ignore")


def _silence_env():
    # THESE ARE READ AT IMPORT TIME BY THEIR LIBRARIES, SO SET THEM BEFORE THEY LOAD.
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


def _claim_whisperx_logger(level):
    # WHISPERX CALLS ITS OWN setup_logging() AT INFO THE FIRST TIME IT BUILDS A
    # LOGGER, BUT ONLY IF THE "whisperx" LOGGER HAS NO HANDLERS YET. PUTTING A
    # NULL HANDLER THERE FIRST MAKES IT SKIP THAT AND LEAVE OUR LEVEL ALONE.
    logger = logging.getLogger("whisperx")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    logger.setLevel(level)
    logger.propagate = True  # SO REAL ERRORS STILL REACH THE ROOT HANDLER.


def _silence_lightning():
    # lightning.pytorch SETS ITS OWN LOGGER BACK TO INFO WHEN IT IS IMPORTED, SO
    # IMPORT IT HERE AND CLAMP IT AFTERWARDS. THIS IS WHAT KILLS THE
    # "Lightning automatically upgraded your loaded checkpoint" MESSAGE.
    try:
        import lightning.pytorch  # noqa: F401
    except ImportError:
        pass


def is_configured():
    return _configured
