"""THE MACHINE ITSELF: WHAT IS INSTALLED, WHAT IT IS, AND OPENING THINGS."""

from hands.apps.browsers import default_browser, drivable_browser
from hands.apps.installed import apps, listing, resolve
from hands.apps.tools import TOOLS

__all__ = ["TOOLS", "apps", "default_browser", "drivable_browser", "listing", "resolve"]
