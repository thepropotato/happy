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


def configured():
    return done
