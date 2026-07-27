"""EVERY KNOB HAPPY HAS, IN THE ORDER A PERSON WOULD LOOK FOR THEM.

THE DEFAULTS LIVE HERE AND NOWHERE ELSE. A MODULE THAT WANTS ONE ASKS
memory.settings FOR IT, SO CHANGING A NUMBER IS NEVER EDITING CODE.
"""

from memory.knobs import choice, group, number, text, toggle

EFFORTS = [("off", "Off"), ("low", "Low"), ("medium", "Medium"), ("high", "High")]

SIZES = ["tiny", "base", "small", "medium", "large-v2", "large-v3", "turbo"]

DEVICES = [("cpu", "CPU"), ("cuda", "CUDA")]

PROVIDERS = [("ollama", "Ollama"), ("openai", "OpenAI shape")]

# EVERY ONE OF THESE IS A MODIFIER, SO HOLDING IT NEVER TYPES ANYTHING.
TALK_KEYS = [
    ("alt_r", "Right Option / Alt"),
    ("alt_l", "Left Option / Alt"),
    ("cmd_r", "Right Command / Win"),
    ("cmd_l", "Left Command / Win"),
    ("ctrl_r", "Right Control"),
    ("ctrl_l", "Left Control"),
    ("shift_r", "Right Shift"),
    ("caps_lock", "Caps Lock"),
    ("f13", "F13"),
]

FOREVER = "0 keeps everything."

BRAIN = [
    choice("brain.effort", "Thinking effort", EFFORTS, "low", "Low keeps answers conversational."),
    choice("brain.model", "Model", [], "gpt-oss:20b", "What does the talking.", source="models"),
    choice("brain.provider", "Backend", PROVIDERS, "ollama", "Who runs the model."),
    text("brain.url", "Address", "", "Empty uses the backend's own.", "http://localhost:11434"),
    number("brain.context", "Context window", 4096, 262144, 4096, 131072, "Sent every request.",
           "tokens", whole=True),
    number("brain.temperature", "Temperature", 0, 2, 0.05, 0.7, "Higher wanders further."),
    number("brain.history", "History carried", 2, 64, 2, 24, "Messages of backchat.", "msgs",
           whole=True),
    number("brain.calls", "Tool rounds", 1, 12, 1, 6, "Before it has to answer.", "max",
           whole=True),
    number("brain.timeout", "Timeout", 30, 900, 10, 300, "A cold load is not a dead server.",
           "sec", whole=True),
]

EARS = [
    choice("ears.model", "Speech model", SIZES, "medium", "Bigger hears better and slower."),
    choice("ears.device", "Runs on", DEVICES, "cpu"),
    text("ears.language", "Language", "en", "Pinned, detecting costs a pass.", "en"),
    choice("ears.key", "Hold to talk", TALK_KEYS, "alt_r", "Held down while you speak."),
    number("ears.hold", "Shortest take", 0.05, 2, 0.05, 0.25, "Briefer was a brush.", "sec"),
    number("ears.preroll", "Lead in", 0, 1.5, 0.05, 0.3, "Kept from before the key.", "sec"),
    number("ears.tail", "Lead out", 0, 1.5, 0.05, 0.2, "Kept after you let go.", "sec"),
]

VOICE = [
    choice("voice.name", "Voice", [], "", "Whichever is installed.", source="voices"),
    number("voice.pace", "Pace", 0.6, 1.6, 0.05, 0.95, "Below one is faster speech."),
    toggle("voice.muted", "Mute", False, "Happy still answers, in writing."),
]

EYES = [
    choice("eyes.model", "Looking model", [], "qwen3-vl", "Only for looking.", source="models"),
    number("eyes.context", "Context window", 4096, 131072, 4096, 32768, None, "tokens",
           whole=True),
    choice("eyes.effort", "Thinking effort", EFFORTS, "off", "Off. It is asked what it sees."),
    number("eyes.width", "Picture width", 512, 3024, 8, 1512, "Every byte is time.", "px",
           whole=True),
]

REMEMBERING = [
    number("memory.messages", "Keep messages", 0, 730, 1, 0, FOREVER, "days", whole=True),
    number("memory.recordings", "Keep recordings", 0, 730, 1, 0, FOREVER, "days", whole=True),
]

GROUPS = [
    group("brain", "Brain", "What does the thinking.", BRAIN),
    group("ears", "Ears", "Hearing you, and when.", EARS),
    group("voice", "Voice", "How Happy sounds.", VOICE),
    group("eyes", "Eyes", "Looking at the screen.", EYES),
    group("memory", "Memory", "What is kept, and how long.", REMEMBERING),
]

EVERY = {entry["key"]: entry for each in GROUPS for entry in each["settings"]}


def entry(key):
    return EVERY.get(key)


def default(key):
    found = EVERY.get(key)

    return found["default"] if found else None


def keys():
    return list(EVERY)


def naming(key, value):
    """WHAT ONE CHOICE IS CALLED WHERE A PERSON CAN SEE IT."""
    for each in (EVERY.get(key) or {}).get("options", []):
        if each["value"] == value:
            return each["label"]

    return str(value)
