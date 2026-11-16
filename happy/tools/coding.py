"""Coding work goes to a real coding agent, opened in a window the person can watch."""

import json
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
from happy import tools
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


def applescript_text(text):
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"') + '"'


def open_terminal(folder, command):
    """Runs the command in a new Terminal window; on macOS returns the tab's tty, which names it later."""
    if sys.platform == "darwin":
        line = applescript_text(f"cd {shell_quote(folder)} && {command}")
        return native.osascript(f'tell application "Terminal"\nset opened to do script {line}\nactivate\nreturn tty of opened\nend tell')
    if sys.platform == "win32":
        subprocess.Popen(["cmd", "/c", "start", "Happy hand-off", "cmd", "/k", f'cd /d "{folder}" && {command}'])
    else:
        subprocess.Popen(["x-terminal-emulator", "-e", "bash", "-lc", f"cd {shell_quote(folder)} && {command}; exec bash"])
    return ""


def session_file():
    return paths.HOME / "handoffs" / "session.json"


def bring_forward(tty):
    """Brings the Terminal tab on this tty to the front: "ok", "idle" when the agent in it has exited, or "gone"."""
    return native.osascript(f'''tell application "Terminal"
repeat with w in windows
repeat with t in tabs of w
if tty of t is {applescript_text(tty)} then
if not busy of t then return "idle"
set selected of t to true
set index of w to 1
activate
return "ok"
end if
end repeat
end repeat
return "gone"
end tell''')


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
    """Give any software task to a coding agent opened on screen: writing, fixing or running code and tests, building, debugging, new or in an existing project, installing or setting up software and servers, terminal commands. Asking Claude or Codex to do something means this, and so does any job no other tool can do: hand it off rather than telling the person to do it. Pass the project's name as said; this finds the folder itself. More on a job already handed off goes to tell_coding_agent."""
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
    tty = open_terminal(where, how.format(cli=cli, file=shell_quote(brief)))
    if tty:
        session_file().write_text(json.dumps({"tty": tty, "agent": name, "folder": str(where), "task": task, "at": time.time(),
                                              "asked": tools.asked.get()}))
    return f"Opened {name} in a Terminal window in {where} with the task."


@tool(say="Telling the coding agent.", label="Telling the coding agent: {message}")
def tell_coding_agent(
    message: Annotated[str, "what to type to the agent, in the person's words plus any detail they gave"],
):
    """Type a message into the coding agent session hand_off_coding opened, in its window on screen: follow-ups, corrections, answers to its questions, anything the person wants to tell or ask Claude about that job. Choose this or a new hand-off by whether it is the same job, unless they say which."""
    if sys.platform != "darwin":
        return "I can only type into the coding agent's window on a Mac."
    try:
        session = json.loads(session_file().read_text())
    except (OSError, ValueError):
        return "No coding agent session is open. hand_off_coding starts one."
    # THE TURN THAT HANDED THE JOB OFF ALREADY GAVE THE AGENT EVERYTHING IT SAID.
    if session.get("asked") and session["asked"] == tools.asked.get():
        return f"{session['agent']} already has the whole task from this request and is working on it; there is nothing to add."
    where = bring_forward(session["tty"])
    if where != "ok":
        return f"The {session['agent']} session for \"{session['task'][:80]}\" has ended. hand_off_coding starts a new one; say what it was working on."
    time.sleep(0.5)
    native.paste(message)
    time.sleep(0.3)
    native.press("return")
    return f"Typed it into the {session['agent']} window in {session['folder']}."
