"""Everything Happy downloads before he can listen and talk, fetched once by setup so his first window already works.

With HAPPY_SETUP_PROGRESS set, progress goes to stdout as `:: <percent> <text>` lines and a failure as `::error <text>`,
which the Mac and Windows setup windows read; anything else is for the log. Without it, the same lines are plain text.
"""

import logging
import os
import sys
import threading
import time
from pathlib import Path

# THE SETUP WINDOWS GIVE PREPARING THE PART OF THE BAR FROM HERE TO 100; setup.sh AND setup.ps1 HAVE THE PART BEFORE.
START = 50
SPEECH_END = 86
VOICE_END = 96
SIZES = {"stt": 482_000_000, "vad": 2_300_000}


WINDOWED = bool(os.environ.get("HAPPY_SETUP_PROGRESS"))
# THE DOWNLOAD BARS ARE REDRAWN IN PLACE, WHICH IN A LOG FILE IS ONLY NOISE; THE SETUP WINDOW HAS ITS OWN BAR.
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")


def report(percent, text):
    print(f":: {int(percent)} {text}" if WINDOWED else text, flush=True)


def failed(text):
    print(f"::error {text}" if WINDOWED else text, flush=True)


def folder_size(folder):
    total = 0
    for root, _, files in os.walk(folder):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total


def speech():
    from happy.speech import models

    wanted = {name: 0 for name in models.missing()}
    if not wanted:
        report(SPEECH_END, "The speech models are here")
        return
    whole = sum(SIZES[name] for name in wanted)
    shown = [0.0]

    def progress(name, done, _):
        wanted[name] = done
        got = sum(wanted.values())
        now = time.monotonic()
        if now - shown[0] > 0.5:
            shown[0] = now
            report(START + (SPEECH_END - START) * min(got / whole, 1),
                   f"Downloading the speech models ({got // 1_000_000} of {whole // 1_000_000} MB)")

    report(START, "Downloading the speech models")
    models.ensure(progress=progress)
    report(SPEECH_END, "The speech models are here")


def voice():
    """Loads the voice once, which downloads it, and keeps the chosen speaker ready in ~/.happy/models/voices."""
    from huggingface_hub import constants

    from happy.config import Config
    from happy.speech.speaker import Speaker

    cache = Path(constants.HF_HUB_CACHE)
    before = folder_size(cache) if cache.exists() else 0
    finished = threading.Event()

    def watch():
        # pocket-tts SAYS NOTHING WHILE IT DOWNLOADS, SO THE CACHE GROWING IS THE ONLY PROGRESS THERE IS.
        while not finished.wait(1.0):
            grown = (folder_size(cache) if cache.exists() else 0) - before
            if grown > 1_000_000:
                report(SPEECH_END + 2, f"Downloading the voice ({grown // 1_000_000} MB)")

    report(SPEECH_END, "Getting the voice ready")
    threading.Thread(target=watch, daemon=True).start()
    try:
        cfg = Config()
        Speaker(cfg.get("voice") or "alba", speed=cfg.get("speech_speed")).warm()
    finally:
        finished.set()
    report(VOICE_END, "The voice is ready")


def whatsapp():
    """WhatsApp's own Python; Happy works without it, so a failure here only waits for the next setup."""
    from happy.integrations import whatsapp as bridge

    report(VOICE_END, "Installing WhatsApp")
    try:
        if not bridge.install():
            print("WhatsApp was not installed: uv is missing.", flush=True)
    except Exception as error:
        print(f"WhatsApp was not installed this time: {error}", flush=True)


def main():
    logging.basicConfig(level=logging.WARNING, stream=sys.stdout)
    try:
        speech()
        voice()
    except Exception as error:
        failed(f"Happy's speech could not be downloaded ({error}). Check the internet connection and try again; "
               "whatever already arrived is kept.")
        return 1
    whatsapp()
    report(100, "Happy is ready")
    return 0
