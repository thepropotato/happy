"""ONE LINE PER THING HAPPY NEEDS, AND WHAT BECAME OF IT."""

import sys

WIDTH = 34

# NOTHING HERE IS COLOURED ON A TERMINAL THAT WOULD PRINT THE CODES INSTEAD.
COLOUR = sys.stdout.isatty() and sys.platform != "win32"

DIM = "\033[2m"
GREEN = "\033[32m"
RED = "\033[31m"
OFF = "\033[0m"

started = None


def shade(text, colour):
    return f"{colour}{text}{OFF}" if COLOUR else text


def title(text):
    print(f"\n{shade(text, DIM)}\n")


def step(name):
    """OPEN A LINE AND LEAVE THE CURSOR ON IT, SO THE OUTCOME LANDS BESIDE THE NAME."""
    global started

    started = name

    print(f"  {name:<{WIDTH}}", end="", flush=True)


def already():
    close(shade("already here", DIM))


def doing(what):
    """SAID WHILE IT HAPPENS, WITH THE OUTCOME LANDING AFTER IT ON THE SAME LINE."""
    print(shade(f"{what}... ", DIM), end="", flush=True)


def done(what="done"):
    close(shade(what, GREEN))


def failed(why):
    close(shade(why, RED))


def close(outcome):
    global started

    started = None

    print(outcome, flush=True)


def note(text):
    print(f"    {shade(text, DIM)}")


def trouble(text):
    print(f"\n{shade(text, RED)}\n")


def ask(question):
    """yes OR no FROM SOMEBODY WATCHING, AND yes FROM A PIPE THAT CANNOT ANSWER."""
    if not sys.stdin.isatty():
        return True

    try:
        return (input(f"  {question} [Y/n] ").strip().lower() or "y").startswith("y")
    except EOFError:
        return True
