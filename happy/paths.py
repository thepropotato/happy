"""Where Happy keeps its things on this computer."""

import os
from pathlib import Path

HOME = Path(os.environ.get("HAPPY_HOME") or Path.home() / ".happy").expanduser()
MODELS = HOME / "models"
CONFIG = HOME / "config.toml"
SECRETS = HOME / "secrets.toml"
LOG = HOME / "happy.log"
LOCK = HOME / "happy.pid"
REPO = Path(__file__).resolve().parents[1]
