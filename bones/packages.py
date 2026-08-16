"""THE VIRTUAL ENVIRONMENT, WHAT GOES IN IT, AND THE WINDOW'S OWN DEPENDENCIES."""

import os
import sys
from pathlib import Path

from bones import systems

HAPPY = Path(__file__).resolve().parent.parent

VENV = HAPPY / ".venv"
REQUIREMENTS = HAPPY / "requirements.txt"
WINDOW = HAPPY / "face" / "window"

# THE OLDEST PYTHON THE PINNED WHEELS ARE BUILT FOR.
LEAST = (3, 11)


def enough(version=None):
    return (version or sys.version_info[:2]) >= LEAST


def wanted():
    return ".".join(str(part) for part in LEAST)


def python():
    """THE INTERPRETER INSIDE THE ENVIRONMENT, WHEREVER THIS SYSTEM PUTS IT."""
    inside = VENV / ("Scripts" if systems.on_windows() else "bin")

    return inside / ("python.exe" if systems.on_windows() else "python")


def built():
    return python().exists()


def build():
    """MAKE THE ENVIRONMENT WITH THE PYTHON THAT IS RUNNING THIS."""
    import venv

    try:
        venv.EnvBuilder(with_pip=True, clear=False, symlinks=not systems.on_windows()).create(VENV)

        return built()
    except Exception:
        return False


# pip install --dry-run COMES BACK HAPPY WHETHER OR NOT IT WOULD INSTALL ANYTHING, SO THE
# PINS ARE READ AND COMPARED HERE INSTEAD.
COUNT = '''
import sys
from importlib.metadata import PackageNotFoundError, version


def wanted(line):
    """THE NAME AND THE PIN, OR None WHERE THIS LINE IS NOT FOR THIS MACHINE."""
    try:
        from packaging.requirements import Requirement
    except ImportError:
        return roughly(line)

    asked = Requirement(line)

    # A MARKER IS HOW THE FILE SAYS "MAC ONLY", AND THOSE PINS ARE NOT MISSING ELSEWHERE.
    if asked.marker and not asked.marker.evaluate():
        return None

    pinned = [str(each.version) for each in asked.specifier if each.operator == "=="]

    return (asked.name, pinned[0]) if pinned else None


def roughly(line):
    """THE SAME, WITHOUT packaging, WHICH IS NOT SOMETHING WE PIN OURSELVES."""
    body, _, marker = line.partition(";")

    if marker.strip() and f'"{sys.platform}"' not in marker:
        return None

    name, _, pin = body.partition("==")

    return (name.strip(), pin.strip()) if pin.strip() else None


short = 0

for line in open(sys.argv[1], encoding="utf-8"):
    line = line.strip()

    if not line or line.startswith("#"):
        continue

    asked = wanted(line)

    if not asked:
        continue

    try:
        short += version(asked[0]) != asked[1]
    except PackageNotFoundError:
        short += 1

print(short)
'''


def missing():
    """HOW MANY PINS THE ENVIRONMENT IS SHORT, OR None WHERE THAT CANNOT BE ASKED."""
    if not built() or not REQUIREMENTS.exists():
        return None

    said = systems.output([str(python()), "-c", COUNT, str(REQUIREMENTS)])

    return int(said) if said.isdigit() else None


def installed():
    """TRUE WHERE EVERY PIN IN THE FILE IS ALREADY IN THE ENVIRONMENT."""
    return missing() == 0


def install():
    """EVERY PIN, INTO THE ENVIRONMENT. THE LONGEST STEP THERE IS."""
    systems.run([str(python()), "-m", "pip", "install", "--quiet", "--upgrade", "pip"])

    return systems.run(
        [str(python()), "-m", "pip", "install", "--requirement", str(REQUIREMENTS)],
        quiet=False,
    )


ELECTRON = WINDOW / "node_modules" / "electron"


def electron():
    """THE ELECTRON THE WINDOW ACTUALLY STARTS, WHICH IS NOT THE SAME AS THE PACKAGE."""
    binary = "electron.exe" if systems.on_windows() else "Electron.app"

    return ELECTRON / "dist" / binary


def window_ready():
    # NOT node_modules, AND NOT THE PACKAGE EITHER: npm HAPPILY LEAVES BOTH OF THOSE
    # BEHIND WITH AN EMPTY dist, AND AN EMPTY dist IS NO WINDOW AT ALL.
    return electron().exists()


def window():
    """npm install, IN THE FOLDER THE WINDOW LIVES IN, AND THE BINARY IT FORGETS."""
    npm = systems.found("npm")

    if not npm:
        return False

    # VS CODE EXPORTS THIS AND IT WOULD START ELECTRON AS PLAIN NODE, WITH NO WINDOW.
    clean = {name: value for name, value in os.environ.items() if name != "ELECTRON_RUN_AS_NODE"}

    import subprocess

    try:
        finished = subprocess.run([npm, "install"], cwd=WINDOW, env=clean, check=False)
    except (OSError, subprocess.SubprocessError):
        return False

    if finished.returncode != 0:
        return False

    return window_ready() or fetch_electron(clean)


def fetch_electron(clean):
    """THE HUNDRED MEGABYTES OF ELECTRON, WHICH npm SOMETIMES DECIDES NOT TO GO AND GET.

    Its postinstall is what downloads the binary, and a run that skips it still reports
    success and still leaves node_modules looking finished, with dist empty inside.
    """
    node = systems.found("node")
    getting = ELECTRON / "install.js"

    if not node or not getting.exists():
        return False

    return systems.run([node, str(getting)], quiet=False) and window_ready()
