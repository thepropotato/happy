"""EMBEDDINGS, LOADED ONLY WHEN ASKED."""

import threading
from pathlib import Path

import numpy as np

MODELS = Path(__file__).resolve().parent.parent / "models" / "minilm"
REPO = "sentence-transformers/all-MiniLM-L6-v2"

# HALF A DOWNLOAD IS NOT A MODEL.
PARTS = ("tokenizer.json", "onnx/model.onnx")

# WHAT THE MODEL WAS TRAINED TO TAKE, OUT OF ITS OWN sentence_bert_config.json.
LONGEST = 256

loaded = None
loading = threading.Lock()


def whole():
    return all((MODELS / part).exists() for part in PARTS)


def fetch():
    """THE WEIGHTS, INTO models/minilm. NINETY MEGABYTES, THE ONE TIME."""
    from huggingface_hub import snapshot_download

    snapshot_download(REPO, local_dir=MODELS, allow_patterns=list(PARTS))

    return MODELS


def model():
    global loaded

    # THE WARM THREAD AND A REAL CALL CAN ARRIVE TOGETHER, AND THE DOWNLOAD IS NOT
    # SOMETHING TO DO TWICE.
    with loading:
        if loaded is None:
            if not whole():
                from face import show

                show.note("Getting the memory model, this happens once.")
                fetch()

            import onnxruntime
            from tokenizers import Tokenizer

            words = Tokenizer.from_file(str(MODELS / "tokenizer.json"))
            words.enable_truncation(max_length=LONGEST)

            # THE FOLDER, NOT THE NAME — OFF DISK, AND NEVER OUT TO HUGGINGFACE AGAIN.
            session = onnxruntime.InferenceSession(
                str(MODELS / "onnx" / "model.onnx"),
                providers=["CPUExecutionProvider"],
            )

            loaded = (words, session)

    return loaded


def warm():
    # LOAD IN THE BACKGROUND SO THE FIRST REAL CALL COSTS NOTHING.
    threading.Thread(target=ready, daemon=True).start()


def ready():
    """WHAT THE THREAD RUNS. A MODEL THAT WILL NOT COME IS SAID ONCE, NOT THROWN."""
    try:
        model()
    except Exception as error:
        from face import show

        show.trouble(f"The memory model would not load, going on without it ({error})")


def vector(text):
    asked = str(text or "").strip()
    words, session = model()

    encoded = words.encode(asked)
    ids = np.array([encoded.ids], dtype=np.int64)
    mask = np.array([encoded.attention_mask], dtype=np.int64)

    states = session.run(
        None,
        {"input_ids": ids, "attention_mask": mask, "token_type_ids": np.zeros_like(ids)},
    )[0]

    # THE AVERAGE OF THE REAL TOKENS, THEN ONTO THE UNIT SPHERE: WHAT THE THREE STEPS IN THE
    # MODEL'S OWN modules.json DO, AND WHAT EVERY VECTOR ALREADY IN THE DATABASE CAME OUT OF.
    weights = mask[..., None].astype(np.float32)
    pooled = (states * weights).sum(axis=1) / np.clip(weights.sum(axis=1), 1e-9, None)
    made = pooled / np.linalg.norm(pooled, axis=1, keepdims=True)

    return np.asarray(made[0], dtype=np.float32)
