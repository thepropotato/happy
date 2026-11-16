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


def keep_private():
    """Makes Happy's folder readable by this account alone, since it holds the history, the linked WhatsApp and the keys."""
    HOME.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        try:
            os.chmod(HOME, 0o700)
        except OSError:
            pass
