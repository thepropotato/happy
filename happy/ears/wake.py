"""Listening for the name with a tiny open-vocabulary keyword spotter, so any name works."""

import re
import tempfile
from pathlib import Path

import numpy as np
import sentencepiece
import sherpa_onnx

from happy import models

RATE = 16000
GREETINGS = {"hey", "hi", "ok", "okay", "yo", "hello", "oi", "oh", "um", "uh", "so", "and", "ah", "hay", "a"}


class WakeWord:
    def __init__(self, name, threshold=0.2, boost=1.5):
        folder = models.ensure(["kws"])["kws"]
        tokens = str(folder / "tokens.txt")
        pieces = sentencepiece.SentencePieceProcessor(model_file=str(folder / "bpe.model"))
        phrases = [name.upper(), f"HEY {name.upper()}"]
        lines = [f"{' '.join(pieces.encode(p, out_type=str))} :{boost} #{threshold}" for p in phrases]
        self.keywords = Path(tempfile.gettempdir()) / f"happy-keywords-{name.lower()}.txt"
        self.keywords.write_text("\n".join(lines) + "\n")
        stem = "epoch-12-avg-2-chunk-16-left-64.int8.onnx"
        self.spotter = sherpa_onnx.KeywordSpotter(
            tokens=tokens,
            encoder=str(folder / f"encoder-{stem}"),
            decoder=str(folder / f"decoder-{stem}"),
            joiner=str(folder / f"joiner-{stem}"),
            keywords_file=str(self.keywords),
            num_threads=1,
            max_active_paths=4,
            keywords_score=boost,
            keywords_threshold=threshold,
            num_trailing_blanks=1,
        )
        self.stream = self.spotter.create_stream()

    def feed(self, samples: np.ndarray) -> bool:
        """True once the name has just been said."""
        self.stream.accept_waveform(RATE, samples)
        heard = False
        while self.spotter.is_ready(self.stream):
            self.spotter.decode_stream(self.stream)
            if self.spotter.get_result(self.stream):
                self.spotter.reset_stream(self.stream)
                heard = True
        return heard


def addressed(text, name):
    """The request that follows the name, or None when the name was only used in passing."""
    words = re.findall(r"[\w']+|[.,!?;]", text)
    target = name.lower()
    for i, word in enumerate(words):
        if word.lower().strip("'") not in (target, target + "s", target + "'s"):
            continue
        before = []
        for prior in reversed(words[:i]):
            if prior in ".!?":
                break
            before.append(prior.lower())
        if all(b in GREETINGS or b == "," for b in before):
            rest = text.split(word, 1)[1] if word in text else ""
            return rest.lstrip(" ,.!?;:-").strip()
    return None
