"""WHAT IS INSTALLED, AND WHICH BROWSER THE LINKS GO TO: python -m hands.apps"""

from hands.apps import browsers, installed

chosen = browsers.default_browser()

print(f"default browser: {chosen or 'never chosen, the system default'}")
print(f"drivable: {browsers.drivable_browser() or 'no'}\n")

for name in installed.apps():
    print(name)
