"""EMBEDDINGS, LOADED ONLY WHEN ASKED."""

import threading
from pathlib import Path

import numpy as np

MODELS = Path(__file__).resolve().parent.parent / "models" / "minilm"
REPO = "sentence-transformers/all-MiniLM-L6-v2"

# HALF A DOWNLOAD IS NOT A MODEL.
PARTS = (
    "config.json",
    "config_sentence_transformers.json",
    "modules.json",
    "sentence_bert_config.json",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.txt",
    "model.safetensors",
    "1_Pooling/config.json",
)

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

            from sentence_transformers import SentenceTransformer

            # THE FOLDER, NOT THE NAME — OFF DISK, AND NEVER OUT TO HUGGINGFACE AGAIN.
            loaded = SentenceTransformer(str(MODELS), local_files_only=True)

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
    made = model().encode([asked], convert_to_numpy=True)[0]

    return np.asarray(made, dtype=np.float32)
