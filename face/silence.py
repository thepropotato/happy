"""SILENCES THE LIBRARIES. CALL configure() BEFORE THE HEAVY IMPORTS."""

import logging
import warnings

LEVEL = logging.ERROR

QUIET = 3  # ONNXRUNTIME'S OWN SCALE, WHERE 3 IS ERROR.

NOISY = (
    "onnx_asr",
    "urllib3",
    "huggingface_hub",
    "filelock",
)

# A CONNECTION REFRESHING ITSELF IS BUILT WITH NO WAY TO OPEN A BROWSER, ON
# PURPOSE. THE SDK LOGS A TRACEBACK ABOUT THAT AND mcps/pool.py ALREADY HANDLES IT.
HUSHED = ("mcp.client.auth.oauth2",)

done = False


def configure(level=LEVEL):
    global done

    warnings.filterwarnings("ignore")
    hush_onnx()

    logging.basicConfig(level=level, format="%(message)s")

    for name in NOISY:
        logging.getLogger(name).setLevel(level)

    for name in HUSHED:
        logging.getLogger(name).setLevel(logging.CRITICAL)

    done = True


def hush_onnx():
    # ITS LOGGER IS C++ AND PYTHON'S logging CANNOT REACH IT.
    try:
        import onnxruntime
    except ImportError:
        return

    onnxruntime.set_default_logger_severity(QUIET)


def hush_tree(prefix, level=LEVEL):
    """FOR A PACKAGE THAT SETS A LEVEL ON EVERY ONE OF ITS OWN LOGGERS.

    THE PARENT CANNOT QUIET THOSE, BECAUSE A LOGGER'S OWN LEVEL IS WHAT DECIDES
    WHETHER IT SPEAKS. THEY ONLY EXIST ONCE IT IS IMPORTED, SO THIS IS CALLED THEN
    RATHER THAN IN configure().
    """
    logging.getLogger(prefix).setLevel(level)

    for name, logger in list(logging.Logger.manager.loggerDict.items()):
        if name.startswith(f"{prefix}.") and isinstance(logger, logging.Logger):
            logger.setLevel(level)


def configured():
    return done
