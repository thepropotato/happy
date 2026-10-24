"""The controls for whichever operating system Happy is running on."""

import sys

if sys.platform == "darwin":
    from happy.system import macos as native
elif sys.platform == "win32":
    from happy.system import windows as native
else:
    native = None

Failed = native.Failed if native else RuntimeError
