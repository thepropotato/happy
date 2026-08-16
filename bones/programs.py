"""THE PROGRAMS HAPPY NEEDS THAT ARE NOT PYTHON, AND GETTING THEM ONTO THIS MACHINE."""

import json
import time
import urllib.error
import urllib.request

from bones import saying, systems

# WHAT EACH ONE IS CALLED TO EVERY PACKAGE MANAGER WE KNOW.
NAMES = {
    "node": {"brew": "node", "winget": "OpenJS.NodeJS.LTS", "apt-get": "nodejs",
             "dnf": "nodejs", "pacman": "nodejs", "zypper": "nodejs"},
    "tesseract": {"brew": "tesseract", "winget": "UB-Mannheim.TesseractOCR",
                  "apt-get": "tesseract-ocr", "dnf": "tesseract", "pacman": "tesseract",
                  "zypper": "tesseract-ocr"},
    "ollama": {"brew": "ollama", "winget": "Ollama.Ollama"},
}

# npm COMES WITH NODE BUT IS THE THING WE ACTUALLY CALL, AND apt SHIPS IT SEPARATELY.
ALSO = {"apt-get": {"node": "npm"}}

# THE LINUX PACKAGES ARE ALWAYS STALE, AND OLLAMA SAYS SO ITSELF.
OLLAMA_SCRIPT = "curl -fsSL https://ollama.com/install.sh | sh"

SERVER = "http://localhost:11434"
TAGS = f"{SERVER}/api/tags"

# A COLD SERVER HAS TO OPEN EVERY MODEL FILE IT OWNS BEFORE IT WILL ANSWER.
WAKING = 30
BEAT = 0.5


def have(program):
    return systems.found(program) is not None


def get(program):
    """INSTALL ONE OUTSIDE PROGRAM, AND SAY WHY NOT WHERE IT CANNOT BE DONE."""
    picked = systems.manager()

    if not picked:
        return False, systems.cannot_install()

    name, _ = picked
    called = NAMES.get(program, {}).get(name)

    if not called:
        return False, f"{name} has no {program}, so it has to go on by hand."

    if not systems.install(called):
        return False, f"{name} would not install {called}."

    # NODE WITHOUT NPM IS NODE WE CANNOT USE.
    beside = ALSO.get(name, {}).get(program)

    if beside:
        systems.install(beside)

    return True, ""


def serving():
    """TRUE WHERE THE MODEL SERVER IS UP AND ANSWERING."""
    try:
        with urllib.request.urlopen(TAGS, timeout=2) as answer:
            json.load(answer)

        return True
    except (urllib.error.URLError, OSError, ValueError):
        return False


def serve():
    """START THE SERVER BEHIND US AND WAIT FOR IT TO ANSWER, OR SAY IT NEVER DID."""
    import subprocess

    if serving():
        return True

    where = systems.found("ollama")

    if not where:
        return False

    try:
        subprocess.Popen(
            [where, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        return False

    for _ in range(int(WAKING / BEAT)):
        if serving():
            return True

        time.sleep(BEAT)

    return False


def models():
    """EVERY MODEL THE SERVER ALREADY HAS, BY THE NAME IT ANSWERS TO."""
    try:
        with urllib.request.urlopen(TAGS, timeout=5) as answer:
            found = json.load(answer)
    except (urllib.error.URLError, OSError, ValueError):
        return set()

    held = set()

    for each in found.get("models", []):
        name = each.get("name") or ""

        if name:
            held.add(name)
            held.add(name.split(":")[0])  # SO qwen3-vl MATCHES qwen3-vl:latest.

    return held


def pull(model):
    """FETCH ONE MODEL, LETTING OLLAMA DRAW ITS OWN PROGRESS ON OUR TERMINAL."""
    where = systems.found("ollama")

    if not where:
        return False

    print()

    return systems.run([where, "pull", model], quiet=False)


def linux_ollama():
    """OLLAMA'S OWN SCRIPT, WHICH IS THE ONLY WAY ONTO A LINUX BOX."""
    saying.note(f"Running {OLLAMA_SCRIPT}")

    return systems.run(["/bin/sh", "-c", OLLAMA_SCRIPT], quiet=False)
