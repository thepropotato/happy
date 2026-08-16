"""THE DETECTOR, OUT OF SPEECHBRAIN AND INTO THE THREE FILES tongue.sound READS.

Run once, by hand, on a machine that has torch and speechbrain installed:

    pip install torch torchaudio speechbrain onnx
    python -m tongue --export

It writes models/voxlingua107/, and those files go up as assets on a release.
Nothing at runtime imports this, which is the whole point of it existing.
"""

import numpy as np

from tongue.sound import BANK, LABELS, MELS, MODELS, NETWORK, SOURCE

# THE ONE SHAPE IT IS TRACED AT, AND THE TIME AXIS IS LOOSENED AFTERWARDS.
FRAMES = 300

# THE HALF SPECTRUM OFF A 400 POINT FFT.
BINS = 201


def export():
    import torch
    from speechbrain.inference.classifiers import EncoderClassifier

    MODELS.mkdir(parents=True, exist_ok=True)

    trained = EncoderClassifier.from_hparams(source=SOURCE, savedir=str(MODELS)).eval()

    network(trained, torch)
    bank(trained, torch)
    labels(trained)

    print(f"Wrote {NETWORK.name}, {BANK.name} and {LABELS.name} into {MODELS}")


def network(trained, torch):
    """THE TWO NETS AS ONE GRAPH: FEATURES IN, A SCORE PER LANGUAGE OUT."""

    class Together(torch.nn.Module):
        def __init__(self, embedding, classifier):
            super().__init__()
            self.embedding = embedding
            self.classifier = classifier

        def forward(self, feats):
            return self.classifier(self.embedding(feats)).squeeze(1)

    both = Together(trained.mods.embedding_model, trained.mods.classifier).eval()

    with torch.no_grad():
        torch.onnx.export(
            both,
            (torch.randn(1, FRAMES, MELS),),
            str(NETWORK),
            input_names=["feats"],
            output_names=["scores"],
            dynamic_axes={"feats": {1: "time"}},
            opset_version=17,
            dynamo=False,
        )


def bank(trained, torch):
    """THE MEL WEIGHTS, TAKEN OUT BY ASKING THE FILTERBANK ABOUT ONE BIN AT A TIME.

    Reading them off the settings is guesswork — every toolkit spaces its triangles
    slightly differently — so the filterbank itself builds them and an identity
    spectrum reads them straight back out.
    """
    filters = trained.mods.compute_features.compute_fbanks
    logged = filters.log_mel

    filters.log_mel = False  # OR EVERY WEIGHT COMES BACK IN DECIBELS.

    try:
        with torch.no_grad():
            weights = filters(torch.eye(BINS).unsqueeze(0))[0].numpy()
    finally:
        filters.log_mel = logged

    np.save(BANK, weights.astype(np.float32))


def labels(trained):
    """THE HUNDRED AND SEVEN NAMES, IN THE ORDER THE SCORES COME OUT IN."""
    named = trained.hparams.label_encoder.ind2lab

    LABELS.write_text("\n".join(named[index] for index in range(len(named))), encoding="utf-8")
