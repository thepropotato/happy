"""The controls for whichever operating system Happy is running on."""

import sys

if sys.platform == "darwin":
    from happy.platforms import mac as system
elif sys.platform == "win32":
    from happy.platforms import windows as system
else:
    system = None

Failed = system.Failed if system else RuntimeError
