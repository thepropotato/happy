"""EMBEDDINGS, LOADED ONLY WHEN ASKED."""

import threading

import numpy as np

MODEL = "all-MiniLM-L6-v2"
loaded = None


def model():
    global loaded

    if loaded is None:
        from sentence_transformers import SentenceTransformer

        # NEVER REACH OUT TO HUGGINGFACE — THE MODEL IS ALREADY ON DISK.
        loaded = SentenceTransformer(MODEL, local_files_only=True)

    return loaded


def warm():
    # LOAD IN THE BACKGROUND SO THE FIRST REAL CALL COSTS NOTHING.
    threading.Thread(target=model, daemon=True).start()


def vector(text):
    asked = str(text or "").strip()
    made = model().encode([asked], convert_to_numpy=True)[0]

    return np.asarray(made, dtype=np.float32)
