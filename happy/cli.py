"""The `happy` command."""

import argparse
import asyncio
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime

from happy import paths
from happy.config import Config


def logging_to(level=logging.INFO, console=True):
    paths.HOME.mkdir(parents=True, exist_ok=True)
    handlers = [logging.FileHandler(paths.LOG)]
    if console:
        handlers.append(logging.StreamHandler(sys.stderr))
    for handler in handlers:
        handler.addFilter(lambda record: record.name != "root")
    logging.basicConfig(level=level, format="%(asctime)s %(name)s %(message)s", datefmt="%H:%M:%S", handlers=handlers, force=True)
    for noisy in ("httpx", "httpx2", "httpcore", "mcp", "claude_agent_sdk", "openai", "pocket_tts"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def alive(pid):
    """Whether a process is running. On Windows os.kill(pid, 0) is no check: it ends that process."""
    if os.name == "nt":
        import ctypes

        kernel = ctypes.windll.kernel32
        handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        try:
            return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259  # STILL_ACTIVE
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def running_pid():
    try:
        pid = int(paths.LOCK.read_text())
    except (OSError, ValueError):
        return None
    return pid if alive(pid) else None


def tell_failure(text):
    """Puts a startup failure on screen: opened from Finder or the Start menu, Happy has no terminal to print it in."""
    try:
        if sys.platform == "win32":
            import ctypes

            ctypes.windll.user32.MessageBoxW(None, text, "Happy could not start", 0x10)
        elif sys.platform == "darwin":
            quoted = text.replace("\\", "\\\\").replace('"', '\\"')
            subprocess.run(["/usr/bin/osascript", "-e", f'display alert "Happy could not start" message "{quoted}" as critical'],
                           timeout=600, capture_output=True)
    except Exception:
        pass


def run(args):
    other = running_pid()
    if other and other != os.getpid():
        print(f"Happy is already running (pid {other}). Stop it with: happy stop")
        return 0
    paths.LOCK.parent.mkdir(parents=True, exist_ok=True)
    paths.LOCK.write_text(str(os.getpid()))
    os.environ.pop("ELECTRON_RUN_AS_NODE", None)
    logging_to(console=not args.quiet)
    if not args.quiet:
        print(f"Starting Happy. It shows up in the corner of your screen; Ctrl+C here stops it. Log: {paths.LOG}", flush=True)
    try:
        from happy.ui.overlay import launch

        return launch(Config(), settings_first=getattr(args, "settings", False))
    except Exception as error:
        logging.getLogger("happy").exception("Happy could not start")
        if not args.quiet:
            raise
        tell_failure(f"{type(error).__name__}: {error}\n\nThe details are in {paths.LOG}.")
        # THE WINDOWS LAUNCHER READS 3 AS "ALREADY TOLD THE PERSON", SO NO SECOND DIALOG FOLLOWS.
        return 3
    finally:
        if running_pid() == os.getpid():
            paths.LOCK.unlink(missing_ok=True)


def start(args):
    if running_pid():
        print("Happy is already running.")
        return 0
    log = open(paths.HOME / "happy.out", "a")
    subprocess.Popen([sys.executable, "-m", "happy", "run", "--quiet"] + (["--settings"] if args.settings else []),
                     stdout=log, stderr=subprocess.STDOUT,
                     stdin=subprocess.DEVNULL, start_new_session=True)
    for _ in range(40):
        time.sleep(0.25)
        if running_pid():
            print("Happy is up. It lives in the corner of your screen.")
            return 0
    print(f"Happy did not start. See {paths.LOG}")
    return 1


def stop(args):
    pid = running_pid()
    if not pid:
        print("Happy is not running.")
        return 0
    os.kill(pid, signal.SIGTERM)
    print("Stopped Happy.")
    return 0


def text_mode(args, once):
    from happy.app import Happy
    from happy.ui.console import ConsoleFace

    logging_to(logging.INFO if args.verbose else logging.WARNING)
    face = ConsoleFace()
    happy = Happy(Config(), face, voice=args.voice, listening=False)
    thread = threading.Thread(target=happy.run, daemon=True)
    thread.start()
    happy.ready.wait()
    try:
        requests = [" ".join(args.text)] if once else iter(lambda: input("\n› "), None)
        for request in requests:
            if not request.strip():
                continue
            face.finished.clear()
            happy.typed(request.strip())
            face.finished.wait()
    except (EOFError, KeyboardInterrupt):
        pass
    happy.stop()
    thread.join(timeout=5)
    return 0


def setup(args):
    """Opens Happy on its settings; started in the background if it is not running yet."""
    if running_pid():
        print("Happy is running; its settings are in the panel (click the smile, then the settings button).")
        return 0
    args.quiet = False
    args.settings = True
    return run(args)


def prepare(args):
    from happy.prepare import main as fetch_everything

    return fetch_everything()


def doctor(args):
    from happy.integrations import status
    from happy.integrations.mcp import hub
    from happy.integrations import discovered
    from happy.speech import models
    from happy.tools.coding import installed

    cfg = Config()
    print("\033[1mHappy doctor\033[0m")
    missing = models.missing()
    print(f"  Speech models: {'ready' if not missing else 'missing ' + ', '.join(missing)}")
    try:
        from happy.speech.listener import pick_mic

        print(f"  Microphone: {pick_mic(cfg.get('input.device') or '')[1]}")
    except Exception as error:
        print(f"  Microphone: {error}")
    for name, (spec, source) in discovered.everything().items():
        hub.add(name, spec, source)
    model = f"{cfg.get('brain.kind')} {cfg.get('brain.model') or ''}".strip()
    for line in asyncio.run(status.everything(model)).splitlines():
        print(f"  {line}")
    agents = installed()
    print(f"  Coding agents: {', '.join(name for _, name, _ in agents) or 'none installed'}")
    return 0


def history(args):
    from happy import history as store

    for turn in reversed(store.recent(limit=args.count, search=args.search or "")):
        when = datetime.fromtimestamp(turn["at"]).strftime("%a %d %b %H:%M")
        print(f"\n\033[2m{when} · {turn['how']}{' · ' + turn['model'] if turn['model'] else ''}\033[0m")
        print(f"\033[1myou ›\033[0m {turn['request']}")
        for step in turn["steps"]:
            print(f"\033[2m  · {step.get('label') or step.get('tool')}{'' if step.get('ok', True) else ' (failed)'}\033[0m")
        if turn["reply"]:
            print(f"\033[1mhappy ›\033[0m {turn['reply']}")
    return 0


def say(args):
    from happy.speech.speaker import Speaker

    cfg = Config()
    speaker = Speaker(cfg.get("voice") or "alba", speed=cfg.get("speech_speed"))
    speaker.start()
    speaker.say(" ".join(args.text))
    time.sleep(0.2)
    speaker.wait()
    time.sleep(0.4)
    return 0


def rename(args):
    cfg = Config()
    cfg.set("name", args.name.strip().title())
    cfg.save()
    print(f"Happy is now called {args.name.strip().title()}. Restart it to wake to the new name.")
    return 0


def persona(args):
    from happy.persona import learn

    return learn(args.file)


def main():
    parser = argparse.ArgumentParser(prog="happy", description="A voice agent that lives on your computer.")
    sub = parser.add_subparsers(dest="command")
    p = sub.add_parser("run", help="run in this terminal, with the mascot on screen")
    p.add_argument("--quiet", action="store_true")
    p.add_argument("--settings", action="store_true", help="open on the settings")
    p.set_defaults(go=run)
    p = sub.add_parser("start", help="run in the background")
    p.add_argument("--settings", action="store_true", help="open on the settings")
    p.set_defaults(go=start)
    sub.add_parser("stop", help="stop the background Happy").set_defaults(go=stop)
    for name, once in (("ask", True), ("chat", False)):
        p = sub.add_parser(name, help="type a request instead of speaking" if once else "type requests one after another")
        if once:
            p.add_argument("text", nargs="+")
        p.add_argument("--voice", action="store_true", help="speak the answers too")
        p.add_argument("--verbose", action="store_true")
        p.set_defaults(go=lambda a, once=once: text_mode(a, once))
    sub.add_parser("setup", help="open the setup window").set_defaults(go=setup)
    sub.add_parser("prepare", help="download the speech models and the voice now").set_defaults(go=prepare)
    sub.add_parser("doctor", help="check every connection").set_defaults(go=doctor)
    p = sub.add_parser("history", help="show past conversations")
    p.add_argument("search", nargs="?", default="")
    p.add_argument("-n", "--count", type=int, default=20)
    p.set_defaults(go=history)
    p = sub.add_parser("say", help="hear the voice")
    p.add_argument("text", nargs="+")
    p.set_defaults(go=say)
    p = sub.add_parser("name", help="change what it is called")
    p.add_argument("name")
    p.set_defaults(go=rename)
    p = sub.add_parser("persona", help="copy the way of talking from a text file, like subtitles")
    p.add_argument("file")
    p.set_defaults(go=persona)
    args = parser.parse_args()
    if not args.command:
        args = parser.parse_args(["run"])
    # WINDOWS READS FILES AS CP1252 UNLESS TOLD OTHERWISE; EVERY PROCESS HAPPY STARTS FROM HERE GETS UTF-8.
    os.environ.setdefault("PYTHONUTF8", "1")
    paths.keep_private()
    sys.exit(args.go(args) or 0)
