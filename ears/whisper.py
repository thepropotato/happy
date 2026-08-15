"""SPEECH INTO TEXT, LOCALLY, WITH WHISPER."""

import numpy as np

import tongue
from ears.engines import EarsError
from ears.languages import LANGUAGES, collect, complete, download, picked, spoken
from ears.nonsense import clean, looping
from face import show
from memory import settings

RATE = 16000

# CPU IS THE SAFE BASELINE EVERYWHERE.
PROVIDERS = {"cpu": ["CPUExecutionProvider"]}

# NOT A FINE-TUNE AND NOT IN LANGUAGES: IT IS THE GENERAL MODEL'S OWN BEST
# LANGUAGE, ALREADY LOADED, WITH NOTHING TO DOWNLOAD AND NOTHING TO WAIT FOR.
ENGLISH = "en"


def missing(path):
    return f"No speech model in {path}. Get it with:\n  python -m ears --get"
model = None
built = None
cached = {}


def wanted():
    return settings.get("ears.device")


def whole():
    return complete(picked())


def load_model(language=None):
    """CALLED AT STARTUP, AND AGAIN WHEN A SETTING PICKS A DIFFERENT ONE."""
    global model, built, cached

    asked = wanted()
    choice = picked(language)
    state = (asked, choice["name"], str(choice["path"]), choice["quantization"])

    if state in cached:
        model = cached[state]
        built = state
        return model

    if not complete(choice):
        raise EarsError(missing(choice["path"]))

    import onnx_asr

    try:
        if choice["quantization"]:
            model = onnx_asr.load_model(
                choice["name"],
                choice["path"],
                quantization=choice["quantization"],
                providers=PROVIDERS.get(asked),
            )
        else:
            model = onnx_asr.load_model(
                choice["name"],
                choice["path"],
                providers=PROVIDERS.get(asked),
            )

        cached[state] = model
        built = state
    except Exception as error:
        if model is None:
            raise

        show.trouble(f"{asked} would not load, still hearing on {built} ({error})")

    return model


def transcribe(audio_file):
    language = spoken()
    source = str(audio_file)

    if language != "auto":
        return clean(load_model(language).recognize(source, language=language))

    guess = firstly(source)

    # IT HAS NAMED ONE WE KEEP A MODEL FOR.
    if guess in LANGUAGES:
        return sharper(source, settled(audio_file, guess)) or english(source)

    # ENGLISH, OR IT WOULD NOT SAY.
    if guess in (ENGLISH, REFUSAL):
        return english(source) or second(source, audio_file)

    # FORCING NO LANGUAGE MAKES WHISPER PICK ONE ITSELF, HERE, WITH NOTHING OVER THE
    # NETWORK.
    raw = (load_model("auto").recognize(source) or "").strip()
    heard = "" if looping(raw) else raw
    found = tongue.language(raw)

    # OFF THE RAW TEXT, LOOP AND ALL: REPEATING ITSELF COSTS WHISPER THE WORDS BUT NOT THE
    # SCRIPT, AND WHICH ALPHABET IT REACHED FOR IS THE SUREST THING IT KNOWS ABOUT A TAKE.
    if found in LANGUAGES and not tongue.mixed(raw):
        return sharper(source, settled(audio_file, found)) or heard

    # NOTHING AT ALL IS NOT ONLY WHAT SILENCE SOUNDS LIKE.
    if not heard:
        return second(source, audio_file) or english(source)

    return heard


def quickly(source):
    """ONE PASS AND NO LANGUAGE HUNTING, FOR WHERE ONLY THE WORDS MATTER AND THE SCRIPT
    THEY LAND IN DOES NOT. THE GENERAL MODEL IS ALREADY LOADED, SO THIS COSTS ONE DECODE."""
    return clean(load_model("auto").recognize(str(source)) or "")


def settled(audio_file, found):
    """AN INDIAN SCRIPT ON THE PAGE ALREADY SAYS THIS WAS NOT ENGLISH, AND THAT IS THE ONE
    PLACE THE SOUND JUDGES BETTER THAN THE WRITING: ASKED FOR TELUGU WITHOUT BEING TOLD,
    WHISPER WILL HEAR IT AND WRITE THE WHOLE THING DOWN IN DEVANAGARI."""
    listened = tongue.aloud(audio_file)

    return listened if listened in LANGUAGES else found


REFUSAL = "nocaptions"


def firstly(source):
    """WHISPER'S OWN FIRST ANSWER, IN THREE TOKENS: THE LANGUAGE IT THINKS IT IS HEARING, OR
    nocaptions FOR ONE IT WILL NOT WRITE AT ALL."""
    try:
        from onnx_asr.utils import read_wav_files

        model = load_model("auto")
        inner = model.asr
        waveforms, lengths = model.resampler(*read_wav_files(source))[:2]

        seed = np.repeat(inner._detect_lang_input, len(waveforms), axis=0)
        first = inner._decoding(inner._encode(waveforms, lengths), seed, 3)[:, 1]
        token = inner._vocab[int(first[0])]

        return token[2:-2] if token.startswith("<|") and token.endswith("|>") else None
    except Exception:
        return None


def second(source, audio_file):
    """ONLY EVER REACHED WHERE ENGLISH CAME BACK WITH NOTHING IN IT, WHICH IS THE ONE PLACE
    THIS DETECTOR IS WORTH ASKING: IT HEARS AN ACCENT AS READILY AS A LANGUAGE, AND ON A
    TAKE THAT DID HAVE ENGLISH WORDS IN IT, IT IS CONFIDENTLY WRONG."""
    listened = tongue.aloud(audio_file)

    return sharper(source, listened) or "" if listened in LANGUAGES else ""


def english(source):
    """THE GENERAL MODEL, TOLD WHAT IT IS LISTENING TO."""
    try:
        return clean(load_model(ENGLISH).recognize(source, language=ENGLISH))
    except Exception as error:
        show.trouble(f"English would not hear this one ({error})")
        return ""


def sharper(source, language):
    """THE MODEL TRAINED ON THIS ONE LANGUAGE, IF IT IS ON THIS MACHINE."""
    if not complete(picked(language)):
        collect(language)
        return None

    try:
        return clean(load_model(language).recognize(source, language=language))
    except Exception as error:
        show.trouble(f"The {language} model would not hear this one, keeping what it had ({error})")
        return None


def warm():
    """RECOGNISE ONCE NOW. THE FIRST CALL IS THE ONE THAT BUILDS THE SESSION."""
    load_model(spoken()).recognize(np.zeros(RATE // 2, dtype=np.float32), sample_rate=RATE)


def fetch():
    """THE WEIGHTS FOR WHATEVER IS SET NOW. ONLY EVER RUN BY HAND, OR ONCE AT STARTUP."""
    return download()
