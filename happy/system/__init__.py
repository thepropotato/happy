"""The controls for whichever operating system Happy is running on."""

import sys

if sys.platform == "darwin":
    from happy.system import macos as native, macos_controls as controls
elif sys.platform == "win32":
    from happy.system import windows as native, windows_controls as controls
else:
    native = controls = None

Failed = native.Failed if native else RuntimeError
