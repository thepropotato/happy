"""A face for the terminal, used by `happy ask` and `happy chat`."""

import sys
import threading


class ConsoleFace:
    def __init__(self, quiet=False):
        self.quiet = quiet
        self.lock = threading.Lock()
        self.streaming = False
        self.finished = threading.Event()

    def out(self, text, end="\n"):
        with self.lock:
            sys.stdout.write(text + end)
            sys.stdout.flush()

    def state(self, name):
        pass

    def user(self, text):
        self.finished.clear()
        self.out(f"\033[2myou ›\033[0m {text}")

    def reply(self, text):
        if text:
            self.close_line()
            self.out(f"\033[1mhappy ›\033[0m {text}")

    def reply_add(self, delta):
        if not self.streaming:
            self.out("\033[1mhappy ›\033[0m ", end="")
            self.streaming = True
        self.out(delta, end="")

    def close_line(self):
        if self.streaming:
            self.out("")
            self.streaming = False

    def step(self, label):
        self.close_line()
        self.out(f"\033[2m  · {label}\033[0m")

    def step_done(self, ok):
        if not ok:
            self.out("\033[2m    (that step failed)\033[0m")

    def note(self, text):
        if not self.quiet:
            self.out(f"\033[2m({text})\033[0m")

    def done(self):
        self.close_line()
        self.finished.set()

    def mouth(self, level):
        pass

    def ear(self, level):
        pass
