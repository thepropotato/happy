"""The key Happy and its WhatsApp bridge share, read from Happy's secrets so it never sits in an environment or a command line."""

import os
import tomllib
from pathlib import Path

NAME = "whatsapp_bridge_key"


def read():
    """The key, or "" when Happy has not made one yet."""
    file = Path(os.environ.get("HAPPY_SECRETS") or Path.home() / ".happy" / "secrets.toml")
    try:
        with open(file, "rb") as held:
            return str(tomllib.load(held).get(NAME) or "")
    except (OSError, tomllib.TOMLDecodeError):
        return ""
