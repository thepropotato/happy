"""GET THIS MACHINE READY FOR HAPPY: python -m bones [--no-models] [--check]"""

import sys

import bones
from bones import saying

if "--check" in sys.argv:
    from bones import packages, programs

    for name, ready in (
        ("Python", packages.enough()),
        ("Node", programs.have("node")),
        ("Tesseract", programs.have("tesseract")),
        ("Model server", programs.serving()),
        ("Environment", packages.built()),
        ("The window", packages.window_ready()),
    ):
        saying.step(name)
        saying.already() if ready else saying.failed("missing")

    raise SystemExit(0)

try:
    raise SystemExit(0 if bones.setup(models="--no-models" not in sys.argv) else 1)
except KeyboardInterrupt:
    saying.trouble("Stopped. Run it again whenever, nothing already done is lost.")
    raise SystemExit(130)
