"""Settings in ~/.happy/config.toml, with defaults for anything left out."""

import copy
import math
import os
import sys

import tomlkit

from happy import paths

MAC = sys.platform == "darwin"
WINDOWS = sys.platform == "win32"
SPEECH_SPEEDS = (0.75, 1.0, 1.25, 1.5, 1.75)


def speech_speed(value):
    """The nearest supported speaking speed."""
    if isinstance(value, bool):
        raise ValueError("Speech speed must be a finite number.")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("Speech speed must be a finite number.")
    return min(SPEECH_SPEEDS, key=lambda step: abs(step - value))

DEFAULTS = {
    "name": "Happy",
    "call_me": "",
    "wake_word": True,
    "start_at_login": True,
    "share_usage": False,
    "auto_update": True,
    "push_to_talk": "right_option" if MAC else "right_ctrl",
    "voice": "alba",
    "speech_speed": 1.0,
    "colour": "#658761",
    "persona": "",
    "projects": "",
    "brain": {"kind": "auto", "model": "", "base_url": ""},
    "input": {"device": ""},
    "whatsapp": {"path": ""},
}

COMMENTS = {
    "name": "What you call it. Saying this name wakes it up.",
    "call_me": "What Happy calls you, like 'my lord'. Empty means your first name from this computer.",
    "push_to_talk": "Hold this key to talk: right_option, right_command, right_ctrl or right_shift.",
    "voice": "A Pocket TTS voice: alba, marius, javert, jean, cosette, anna, vera, charles, paul, george, mary, jane, michael, eve.",
    "speech_speed": "Speaking speed, keeping the pitch: 0.75, 1.0, 1.25, 1.5 or 1.75.",
    "persona": "Path to a text file whose way of talking Happy should copy.",
    "start_at_login": "Start Happy when you log in, so reminders go off even after a restart.",
    "share_usage": "Send anonymous counts of how each turn went, never your words, to help make Happy better.",
    "projects": "Folder where new coding projects are created. Empty means it is worked out.",
}


def merged(base, extra):
    out = copy.deepcopy(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = merged(out[key], value)
        else:
            out[key] = value
    return out


class Config:
    def __init__(self, path=paths.CONFIG):
        self.path = path
        self.doc = tomlkit.parse(path.read_text(encoding="utf-8")) if path.exists() else tomlkit.document()
        self.data = merged(DEFAULTS, self.doc.unwrap())
        self.data["speech_speed"] = speech_speed(self.data["speech_speed"])

    def get(self, dotted, default=None):
        node = self.data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, dotted, value):
        if dotted == "speech_speed":
            value = speech_speed(value)
        parts = dotted.split(".")
        node, doc = self.data, self.doc
        for part in parts[:-1]:
            node = node.setdefault(part, {})
            if part not in doc:
                doc[part] = tomlkit.table()
            doc = doc[part]
        node[parts[-1]] = value
        doc[parts[-1]] = value
        if len(parts) == 1 and parts[0] in COMMENTS and hasattr(doc[parts[0]], "comment"):
            doc[parts[0]].comment(COMMENTS[parts[0]])

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(tomlkit.dumps(self.doc), encoding="utf-8")


def secrets():
    if not paths.SECRETS.exists():
        return {}
    return tomlkit.parse(paths.SECRETS.read_text(encoding="utf-8")).unwrap()


def save_secret(key, value):
    data = secrets()
    data[key] = value
    paths.SECRETS.parent.mkdir(parents=True, exist_ok=True)
    paths.SECRETS.write_text(tomlkit.dumps(data), encoding="utf-8")
    if not WINDOWS:
        os.chmod(paths.SECRETS, 0o600)
