"""Speech to text with NVIDIA Parakeet, run on the CPU through sherpa-onnx."""

import difflib
import os
import re

import numpy as np
import sherpa_onnx

from happy.speech import models

RATE = 16000
# HOW HARD A KNOWN NAME IS PREFERRED OVER WHAT IT SOUNDS LIKE; 2.0 FIXED EVERY NAME TRIED AND BENT NO ORDINARY SENTENCE.
NAME_PULL = 2.0


def vocab_for(folder):
    """The model's word pieces in the form sherpa-onnx reads to spell hotwords, made once beside the model."""
    vocab = folder / "bpe.vocab"
    if not vocab.exists():
        pieces = [line.rsplit(" ", 1)[0] for line in (folder / "tokens.txt").read_text().splitlines() if line.strip()]
        vocab.write_text("".join(f"{piece}\t{-i}\n" for i, piece in enumerate(pieces)))
    return vocab


def words(text):
    return re.findall(r"[a-z']+", text.lower())


class Transcriber:
    def __init__(self):
        folder = models.ensure(["stt"])["stt"]
        self.recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=str(folder / "encoder.int8.onnx"),
            decoder=str(folder / "decoder.int8.onnx"),
            joiner=str(folder / "joiner.int8.onnx"),
            tokens=str(folder / "tokens.txt"),
            num_threads=min(4, os.cpu_count() or 2),
            model_type="nemo_transducer",
            # BEAM SEARCH IS WHAT LETS KNOWN NAMES STEER THE WORDS AS THEY ARE HEARD, AND IT COSTS NO MORE THAN GREEDY HERE.
            decoding_method="modified_beam_search",
            max_active_paths=4,
            modeling_unit="bpe",
            bpe_vocab=str(vocab_for(folder)),
            hotwords_score=NAME_PULL,
        )
        self.names = ""
        self.name_words = set()

    def know(self, names):
        """The names to hear as themselves, like the person's contacts."""
        self.names = "/".join(names)
        self.name_words = {word for name in names for word in words(name)}

    def __call__(self, samples: np.ndarray) -> str:
        if len(samples) < RATE // 4:
            return ""
        # A LONG LIST OF NAMES PULLS WORDS OUT OF NOISE, SO THE NAMES ONLY RESPELL WHAT WAS HEARD WITHOUT THEM.
        plain = self.decode(samples, "")
        if not plain or not self.names:
            return plain
        named = self.decode(samples, self.names)
        return named if self.respelled(plain, named) else plain

    def respelled(self, plain, named):
        """Whether the names only swapped heard words for names, adding nothing that is not a name."""
        before, after = words(plain), words(named)
        for kind, _, _, start, end in difflib.SequenceMatcher(a=before, b=after, autojunk=False).get_opcodes():
            if kind != "equal" and not all(word in self.name_words for word in after[start:end]):
                return False
        return True

    def decode(self, samples, hotwords):
        stream = self.recognizer.create_stream(hotwords=hotwords)
        stream.accept_waveform(RATE, samples.astype(np.float32))
        self.recognizer.decode_stream(stream)
        return stream.result.text.strip()
