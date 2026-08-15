"""EVERY CODER THERE IS, AND THE COMMAND EACH ONE IS RUN BY. NOTHING RUNS HERE."""

import shutil

# ONE JSON OBJECT PER LINE AS THE WORK HAPPENS, NOT ONE BLOCK AT THE END.
# --verbose IS WHAT MAKES EVERY EVENT COME OUT AND NOT ONLY THE LAST ONE.
CLAUDE = [
    "claude",
    "-p",
    "--output-format",
    "stream-json",
    "--verbose",
    "--permission-mode",
    "acceptEdits",
]


def claude_code(task):
    return CLAUDE + [task]


def claude_code_resume(session_id, response):
    return CLAUDE + ["--resume", session_id, response]


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

# WHO SAYS WHAT IT IS DOING WHILE IT DOES IT. THE REST ARE READ AT THE END.
STREAMING = {"Claude Code"}


def available():
    return [name for name, binary in BINARIES.items() if shutil.which(binary)]
