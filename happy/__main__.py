"""The `happy` command."""

import argparse
import logging
import os
import signal
import subprocess
import sys
import threading
import time

from happy import paths
from happy.config import Config


def logging_to(level=logging.INFO, console=True):
    paths.HOME.mkdir(parents=True, exist_ok=True)
    handlers = [logging.FileHandler(paths.LOG)]
    if console:
        handlers.append(logging.StreamHandler(sys.stderr))
    logging.basicConfig(level=level, format="%(asctime)s %(name)s %(message)s", datefmt="%H:%M:%S", handlers=handlers)
    for noisy in ("httpx", "httpcore", "mcp", "claude_agent_sdk", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def running_pid():
    try:
        pid = int(paths.LOCK.read_text())
        os.kill(pid, 0)
        return pid
    except (OSError, ValueError):
        return None


def run(args):
    other = running_pid()
    if other and other != os.getpid():
        print(f"Happy is already running (pid {other}). Stop it with: happy stop")
        return 1
    paths.LOCK.parent.mkdir(parents=True, exist_ok=True)
    paths.LOCK.write_text(str(os.getpid()))
    os.environ.pop("ELECTRON_RUN_AS_NODE", None)
    logging_to(console=not args.quiet)
    try:
        from happy.face.window import launch

        return launch(Config())
    finally:
        if running_pid() == os.getpid():
            paths.LOCK.unlink(missing_ok=True)


def start(args):
    if running_pid():
        print("Happy is already running.")
        return 0
    log = open(paths.HOME / "happy.out", "a")
    subprocess.Popen([sys.executable, "-m", "happy", "run", "--quiet"], stdout=log, stderr=subprocess.STDOUT,
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
    from happy.core import Happy
    from happy.face.console import ConsoleFace

    logging_to(logging.INFO if args.verbose else logging.WARNING)
    face = ConsoleFace()
    happy = Happy(Config(), face, voice=args.voice, ears=False)
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
    from happy.face.setup_window import show_setup

    return show_setup()


def doctor(args):
    from happy import setup as wizard

    return wizard.doctor()


def say(args):
    from happy.voice.speaker import Speaker

    speaker = Speaker(Config().get("voice") or "alba")
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
    from happy import setup as wizard

    return wizard.persona(args.file)


def connect(args):
    if args.what == "whatsapp":
        return setup(args)
    from happy import setup as wizard

    return wizard.connect_mail()


def main():
    parser = argparse.ArgumentParser(prog="happy", description="A voice agent that lives on your computer.")
    sub = parser.add_subparsers(dest="command")
    p = sub.add_parser("run", help="run in this terminal, with the mascot on screen")
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(go=run)
    sub.add_parser("start", help="run in the background").set_defaults(go=start)
    sub.add_parser("stop", help="stop the background Happy").set_defaults(go=stop)
    for name, once in (("ask", True), ("chat", False)):
        p = sub.add_parser(name, help="type a request instead of speaking" if once else "type requests one after another")
        if once:
            p.add_argument("text", nargs="+")
        p.add_argument("--voice", action="store_true", help="speak the answers too")
        p.add_argument("--verbose", action="store_true")
        p.set_defaults(go=lambda a, once=once: text_mode(a, once))
    sub.add_parser("setup", help="open the setup window").set_defaults(go=setup)
    sub.add_parser("doctor", help="check that everything is in place").set_defaults(go=doctor)
    p = sub.add_parser("say", help="hear the voice")
    p.add_argument("text", nargs="+")
    p.set_defaults(go=say)
    p = sub.add_parser("name", help="change what it is called")
    p.add_argument("name")
    p.set_defaults(go=rename)
    p = sub.add_parser("persona", help="copy the way of talking from a text file, like subtitles")
    p.add_argument("file")
    p.set_defaults(go=persona)
    p = sub.add_parser("connect", help="connect mail or WhatsApp")
    p.add_argument("what", choices=["mail", "whatsapp"])
    p.set_defaults(go=connect)
    args = parser.parse_args()
    if not args.command:
        args = parser.parse_args(["run"])
    sys.exit(args.go(args) or 0)


if __name__ == "__main__":
    main()
