"""Speech to text with NVIDIA Parakeet, run on the CPU through sherpa-onnx."""

import os

import numpy as np
import sherpa_onnx

from happy.speech import models

RATE = 16000


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
        )

    def __call__(self, samples: np.ndarray) -> str:
        if len(samples) < RATE // 4:
            return ""
        stream = self.recognizer.create_stream()
        stream.accept_waveform(RATE, samples.astype(np.float32))
        self.recognizer.decode_stream(stream)
        return stream.result.text.strip()
