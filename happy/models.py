"""Downloads the speech models once, into ~/.happy/models."""

import shutil
import sys
import tarfile
import tempfile
from pathlib import Path

import httpx

from happy import paths

RELEASES = "https://github.com/k2-fsa/sherpa-onnx/releases/download"

SPEECH = {
    "stt": f"{RELEASES}/asr-models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8.tar.bz2",
    "kws": f"{RELEASES}/kws-models/sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01.tar.bz2",
    "vad": f"{RELEASES}/asr-models/silero_vad_v5.onnx",
}


def where(name):
    url = SPEECH[name]
    file = url.rsplit("/", 1)[1]
    return paths.MODELS / (file.removesuffix(".tar.bz2") if file.endswith(".tar.bz2") else file)


def fetch(url, into):
    with httpx.stream("GET", url, follow_redirects=True, timeout=60) as reply:
        reply.raise_for_status()
        whole = int(reply.headers.get("content-length") or 0)
        done = 0
        with open(into, "wb") as out:
            for chunk in reply.iter_bytes(1 << 20):
                out.write(chunk)
                done += len(chunk)
                if whole and sys.stdout.isatty():
                    print(f"\r  {into.name}: {done * 100 // whole}%", end="", flush=True)
    if sys.stdout.isatty():
        print()


def ensure(names=tuple(SPEECH)):
    """Downloads whichever of the named models are missing and returns their paths."""
    paths.MODELS.mkdir(parents=True, exist_ok=True)
    for name in names:
        target = where(name)
        if target.exists():
            continue
        url = SPEECH[name]
        print(f"Downloading the {name} model…", flush=True)
        with tempfile.TemporaryDirectory(dir=paths.MODELS) as tmp:
            file = Path(tmp) / url.rsplit("/", 1)[1]
            fetch(url, file)
            if file.name.endswith(".tar.bz2"):
                with tarfile.open(file) as archive:
                    archive.extractall(tmp, filter="data")
                shutil.move(str(Path(tmp) / target.name), target)
            else:
                shutil.move(str(file), target)
    return {name: where(name) for name in names}


if __name__ == "__main__":
    ensure()
