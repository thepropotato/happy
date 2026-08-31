"""VOICEBENCH: SPOKEN INSTRUCTIONS THROUGH HAPPY'S OWN EARS, THEN ITS OWN BRAIN.

TRANSCRIPTION IS SCORED AGAINST THE WRITTEN PROMPT (WER). THE REPLY IS RECORDED BUT
NOT GRADED HERE, BECAUSE GRADING IT NEEDS A JUDGE MODEL AND THAT IS A SEPARATE CHOICE.
"""

import io
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bench import sandbox

DB = sandbox.throwaway("voicebench.db")

import soundfile as sf
from datasets import Audio, load_dataset

# THE SPLITS WORTH RUNNING: PLAIN SPEECH, THEN ACCENTS, INDIAN ENGLISH INCLUDED.
SUITES = [
    ("commoneval", "test"),
    ("sd-qa", "ind_s"),
    ("sd-qa", "usa"),
    ("sd-qa", "gbr"),
]


def words(text):
    return re.findall(r"[a-z0-9']+", (text or "").lower())


def wer(said, heard):
    """WORD ERROR RATE BY EDIT DISTANCE, THE STANDARD VOICEBENCH ASR MEASURE."""
    a, b = words(said), words(heard)
    if not a:
        return 0.0 if not b else 1.0

    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        nxt = [i]
        for j, y in enumerate(b, 1):
            nxt.append(min(row[j] + 1, nxt[j - 1] + 1, row[j - 1] + (x != y)))
        row = nxt

    return row[-1] / len(a)


def clip(raw, folder, index):
    """THE AUDIO ON DISK AS A WAV, BECAUSE THAT IS WHAT transcribe() TAKES."""
    data, rate = sf.read(io.BytesIO(raw))
    where = folder / f"{index:04d}.wav"
    sf.write(where, data, rate)
    return where, len(data) / rate


def run(config, split, limit, engine, answer):
    import ears.engines as engines

    rows = load_dataset("hlt-lab/voicebench", config, split=split)
    rows = rows.cast_column("audio", Audio(decode=False))
    folder = Path(__file__).resolve().parent / "runs" / "audio" / f"{config}-{split}"
    folder.mkdir(parents=True, exist_ok=True)

    results = []
    for i in range(min(limit, len(rows))):
        row = rows[i]
        said = row.get("prompt") or row.get("question") or ""
        path, seconds = clip(row["audio"]["bytes"], folder, i)

        started = time.perf_counter()
        heard = engines.transcribe(str(path), engine=engine) or ""
        listened = time.perf_counter() - started

        got = dict(i=i, said=said, heard=heard.strip(), wer=round(wer(said, heard), 3),
                   audio_seconds=round(seconds, 1), asr_seconds=round(listened, 2))

        if answer:
            from brain.thinking import Happy
            tools, calls = answer
            calls.clear()
            happy = Happy(tools=tools)
            happy.thread = f"vb-{config}-{split}-{i}"
            started = time.perf_counter()
            try:
                got["reply"] = happy.say(got["heard"])[:400]
            except Exception as error:
                got["reply"] = f"ERROR {type(error).__name__}: {error}"
            got["reply_seconds"] = round(time.perf_counter() - started, 1)
            got["called"] = [c["name"] for c in calls]

        results.append(got)
        print(f"  [{i:>3}] wer {got['wer']:<6} {got['asr_seconds']:>5}s  "
              f"heard: {got['heard'][:56]}", flush=True)

    return results


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    engine = sys.argv[2] if len(sys.argv) > 2 else None
    with_brain = "--brain" in sys.argv

    answer = None
    if with_brain:
        tools, calls = sandbox.harness()
        sandbox.assert_no_real_tools(tools)
        answer = (tools, calls)
        print(f"{len(tools)} tools mocked")

    print(f"db -> {DB}\nengine -> {engine or 'configured default'}, {limit} clips per suite\n")

    report = {}
    for config, split in SUITES:
        print(f"{config}/{split}", flush=True)
        got = run(config, split, limit, engine, answer)
        mean = sum(r["wer"] for r in got) / len(got) if got else 0
        audio = sum(r["audio_seconds"] for r in got)
        heard_in = sum(r["asr_seconds"] for r in got)
        report[f"{config}/{split}"] = dict(
            clips=len(got), mean_wer=round(mean, 3),
            realtime_factor=round(heard_in / audio, 3) if audio else None, results=got)
        print(f"  -> mean WER {mean:.3f} over {len(got)} clips\n", flush=True)

    out = Path(__file__).resolve().parent / "runs" / f"voicebench-{engine or 'default'}.json"
    out.write_text(json.dumps(report, indent=2))
    print("summary")
    for name, got in report.items():
        print(f"  {name:<22} WER {got['mean_wer']:.3f}  rtf {got['realtime_factor']}")
    print(f"report -> {out}")


if __name__ == "__main__":
    main()
