"""EVERYTHING THAT HAS TO BE ON THIS MACHINE BEFORE HAPPY WILL START."""

from bones import packages, programs, saying, systems, weights

# EVERY STEP THAT FAILED, SO THE END CAN SAY WHAT IS STILL MISSING.
amiss = []


def setup(models=True):
    """CHECK, INSTALL, FETCH. SAFE TO RUN AGAIN: NOTHING ALREADY HERE IS TOUCHED."""
    amiss.clear()

    saying.title("Happy needs a few things.")

    interpreter()
    program("Node", "node")
    program("Tesseract", "tesseract")
    server()

    environment()
    dependencies()
    window()

    if models:
        thinking()
        speaking()

    clickable()

    return report()


def wrong(name, why):
    amiss.append((name, why))
    saying.failed(why)


def interpreter():
    """THE PYTHON RUNNING THIS IS THE ONE THE ENVIRONMENT WILL BE MADE FROM."""
    import sys

    saying.step(f"Python {'.'.join(str(part) for part in sys.version_info[:3])}")

    if packages.enough():
        saying.already()
    else:
        wrong("Python", f"too old, Happy needs {packages.wanted()} or newer")


def program(name, called):
    """ONE OUTSIDE PROGRAM: FOUND, OR INSTALLED, OR EXPLAINED."""
    saying.step(name)

    if programs.have(called):
        return saying.already()

    saying.doing("installing")

    got, why = programs.get(called)

    if got and programs.have(called):
        saying.done()
    else:
        wrong(name, why or "would not install")


def server():
    """THE THING THAT RUNS THE MODEL, WHICH ALSO HAS TO BE AWAKE."""
    saying.step("Model server")

    if not programs.have("ollama"):
        saying.doing("installing")

        got = programs.linux_ollama() if not (systems.on_mac() or systems.on_windows()) \
            else programs.get("ollama")[0]

        if not (got and programs.have("ollama")):
            return wrong("Model server", "would not install")

    if programs.serving():
        return saying.already()

    saying.doing("starting")

    if programs.serve():
        saying.done()
    else:
        wrong("Model server", "installed, but it would not start")


def environment():
    saying.step("Environment")

    if packages.built():
        return saying.already()

    saying.doing("making")

    saying.done() if packages.build() else wrong("Environment", "could not be made")


def dependencies():
    saying.step("Dependencies")

    if not packages.built():
        return wrong("Dependencies", "no environment to put them in")

    if packages.installed():
        return saying.already()

    saying.doing("installing")
    print()

    saying.done() if packages.install() else wrong("Dependencies", "pip would not finish")


def window():
    saying.step("The window")

    if packages.window_ready():
        return saying.already()

    if not programs.have("npm"):
        return wrong("The window", "npm is not here, so Electron cannot be fetched")

    saying.doing("installing")
    print()

    saying.done() if packages.window() else wrong("The window", "npm would not finish")


def thinking():
    """THE TWO MODELS THE SETTINGS ASK FOR OUT OF THE BOX."""
    if not programs.serving():
        return

    held = programs.models()

    for model, size in (weights.THINKING, weights.LOOKING):
        saying.step(f"{model} ({size})")

        if model in held:
            saying.already()
        elif not saying.ask(f"pull {model}?"):
            saying.note("skipped")
        else:
            saying.done() if programs.pull(model) else wrong(model, "would not pull")


def speaking():
    """HEARING, SPEAKING, AND THE TWO SMALL MODELS BEHIND THEM."""
    if not packages.built():
        return

    for name, module, size in weights.FETCHES:
        saying.step(f"{name} ({size})")

        if weights.held(module):
            saying.already()
            continue

        saying.doing("getting")

        saying.done() if weights.fetch(module) else wrong(name, "would not download")

    saying.step("Memory model (90 MB)")

    if weights.held("memory"):
        saying.already()
    else:
        saying.doing("getting")
        saying.done() if weights.memory() else wrong("Memory model", "would not download")


def clickable():
    """THE APP, THE SHORTCUT, OR THE MENU ENTRY: HAPPY WITHOUT A TERMINAL."""
    from bones import bundling

    saying.step(started())

    if not packages.window_ready():
        return wrong(started(), "the window has no Electron to build one from")

    saying.doing("building")

    try:
        where, why = bundling.build()
    except Exception as error:
        where, why = None, str(error)

    if where is None:
        return wrong(started(), why or "could not be built")

    saying.done()
    saying.note(str(where))


def started():
    if systems.on_mac():
        return "Happy.app"

    return "Shortcut" if systems.on_windows() else "Menu entry"


def opening():
    """HOW SOMEBODY STARTS HIM NOW, IN THE WORDS OF WHATEVER THIS SYSTEM MADE."""
    if systems.on_mac():
        return "Open him from Spotlight, or from Applications."

    if systems.on_windows():
        return "He is in the Start menu."

    return "He is in your applications."


def report():
    """WHAT IS STILL WRONG, OR HOW TO START HIM."""
    if not amiss:
        saying.title(f"Happy is ready. {opening()}")

        return True

    saying.title("Happy is not ready yet:")

    for name, why in amiss:
        saying.note(f"{name}: {why}")

    print()

    return False
