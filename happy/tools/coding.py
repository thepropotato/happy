"""Coding work goes to a real coding agent, opened in a window the person can watch."""

import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Annotated

from happy import paths
from happy.config import Config
from happy.system import native
from happy.tools import tool

AGENTS = [
    ("claude", "Claude Code", '{cli} "$(cat {file})"'),
    ("codex", "Codex", '{cli} "$(cat {file})"'),
    ("gemini", "Gemini CLI", '{cli} -i "$(cat {file})"'),
    ("cursor-agent", "Cursor Agent", '{cli} "$(cat {file})"'),
    ("opencode", "opencode", '{cli} --prompt "$(cat {file})"'),
    ("qwen", "Qwen Code", '{cli} -i "$(cat {file})"'),
    ("amp", "Amp", '{cli} "$(cat {file})"'),
]


def installed():
    return [(cli, name, how) for cli, name, how in AGENTS if shutil.which(cli)]


def projects_folder():
    """Where the person keeps their projects, judged by where their git repos live."""
    named = Config().get("projects")
    if named:
        return Path(named).expanduser()
    parents = Counter()
    for base in [Path.home() / d for d in ("Desktop", "Documents", "Developer", "Projects", "projects", "code", "src", "dev")]:
        if not base.exists():
            continue
        for git in list(base.glob("*/.git")) + list(base.glob("*/*/.git")):
            parents[git.parent.parent] += 1
    return parents.most_common(1)[0][0] if parents else Path.home() / "Projects"


def slug(text):
    words = re.findall(r"[a-z0-9]+", text.lower())[:4]
    return "-".join(words) or "new-project"


def shell_quote(text):
    return "'" + str(text).replace("'", "'\\''") + "'"


def open_terminal(folder, command):
    if sys.platform == "darwin":
        line = f"cd {shell_quote(folder)} && {command}"
        escaped = line.replace("\\", "\\\\").replace('"', '\\"')
        native.osascript(f'tell application "Terminal" to do script "{escaped}"')
        native.osascript('tell application "Terminal" to activate')
    elif sys.platform == "win32":
        subprocess.Popen(["cmd", "/c", "start", "Happy hand-off", "cmd", "/k", f'cd /d "{folder}" && {command}'])
    else:
        subprocess.Popen(["x-terminal-emulator", "-e", "bash", "-lc", f"cd {shell_quote(folder)} && {command}; exec bash"])


def claude_desktop(task):
    """Pastes the task into the Claude app when no command-line agent is installed."""
    from happy.tools.apps import find_app

    found, path = find_app("Claude")
    if not found:
        return None
    native.open_app(path)
    time.sleep(2.5)
    native.press("cmd+n")
    time.sleep(0.8)
    native.paste(task)
    native.press("return")
    return "Opened the Claude app and gave it the task."


@tool(say="Handing that to a coding agent.", label="Handing off: {task}")
def hand_off_coding(
    task: Annotated[str, "the full task for the coding agent, in the person's words plus any detail they gave"],
    folder: Annotated[str, "the project folder or its name; empty for a new project"] = "",
):
    """Give any coding, building, debugging or software task, new or in an existing project, to a coding agent opened on screen. Pass the project's name as said; this finds the folder itself."""
    from happy.tools.apps import locate

    agents = installed()
    if folder:
        hits = locate(folder, folders=True)
        if not hits:
            return f"I couldn't find a folder called {folder}."
        where = Path(hits[0])
    else:
        where = projects_folder() / slug(task)
        where.mkdir(parents=True, exist_ok=True)
    if not agents:
        pasted = claude_desktop(task)
        if pasted:
            return pasted
        return "No coding agent is installed, so I can't do that. Installing Claude Code, Codex or Gemini CLI would let me hand it off."
    cli, name, how = agents[0]
    preferred = Config().get("coding_agent")
    for agent in agents:
        if preferred and agent[0] == preferred:
            cli, name, how = agent
    briefs = paths.HOME / "handoffs"
    briefs.mkdir(parents=True, exist_ok=True)
    brief = briefs / f"{time.strftime('%Y%m%d-%H%M%S')}.md"
    brief.write_text(task)
    open_terminal(where, how.format(cli=cli, file=shell_quote(brief)))
    return f"Opened {name} in a Terminal window in {where} with the task."
