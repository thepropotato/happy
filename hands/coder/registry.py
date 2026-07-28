"""CODER REGISTRY. COMMANDS IN, NOTHING RUNS HERE."""

import shutil


def claude_code(task):
    return ["claude", "-p", task]


def codex(task):
    return ["codex", "exec", task]


CODERS = {
    "Claude Code": claude_code,
    "Codex": codex,
}

BINARIES = {
    "Claude Code": "claude",
    "Codex": "codex",
}


def available():
    return [name for name, binary in BINARIES.items() if shutil.which(binary)]
