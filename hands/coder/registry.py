"""CODER REGISTRY. COMMANDS IN, NOTHING RUNS HERE."""

import shutil


def claude_code(task):
    return ["claude", "-p", "--output-format", "json", "--permission-mode", "acceptEdits", task]


def claude_code_resume(session_id, response):
    return ["claude", "-p", "--output-format", "json", "--permission-mode", "acceptEdits", "--resume", session_id, response]


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
