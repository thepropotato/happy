"""THE TELUGU EAR, OUT OF ITS OWNER'S WEIGHTS AND INTO THE FILES ears.languages READS.

Run once, by hand, on a machine that has torch and optimum installed:

    pip install torch optimum[onnxruntime]
    python -m ears --export

It writes models/whisper-telugu-small/, and those files go up as assets on a release
named whisper-telugu-small-v1. Nothing at runtime imports this, which is the whole
point of it existing.

The weights are vasista22/whisper-telugu-small, Apache 2.0, from SPRING Lab at IIT
Madras. Only the ONNX graphs are ours, and the licence travels with the release. This
file exists so that stays checkable: it says where they came from and remakes them.
"""

from ears.languages import LOCAL_PARTS, TELUGU, picked

WHERE = picked("te")["path"]


def export():
    from optimum.onnxruntime import ORTModelForSpeechSeq2Seq
    from transformers import WhisperProcessor

    WHERE.mkdir(parents=True, exist_ok=True)

    # MERGED, BECAUSE THE RUNTIME READS ONE decoder_model_merged.onnx RATHER THAN A PAIR OF
    # GRAPHS THAT DIFFER ONLY IN WHETHER THERE IS ANYTHING IN THE CACHE YET.
    graphs = ORTModelForSpeechSeq2Seq.from_pretrained(TELUGU, export=True, use_merged=True)
    graphs.save_pretrained(WHERE)

    # THE VOCABULARY AND THE ADDED TOKENS, WHICH ARE THE OWNER'S AND NOT THE EXPORTER'S.
    WhisperProcessor.from_pretrained(TELUGU).save_pretrained(WHERE)

    missing = [part for part in LOCAL_PARTS if not (WHERE / part).exists()]

    if missing:
        raise SystemExit(f"Exported, but {', '.join(missing)} never appeared in {WHERE}")

    print(f"Wrote {', '.join(LOCAL_PARTS)} into {WHERE}")
    print(f"Put them up as assets on a release, then {TELUGU} is what Happy hears Telugu with.")
