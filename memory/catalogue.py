"""EVERY KNOB HAPPY HAS, IN THE ORDER A PERSON WOULD LOOK FOR THEM."""

from memory.kinds import action, choice, group, number, text, toggle

EFFORTS = [("off", "Off"), ("low", "Low"), ("medium", "Medium"), ("high", "High")]

DEVICES = [("cpu", "CPU"), ("auto", "Anything faster")]

EARS_ENGINES = [("parakeet", "Parakeet"), ("whisper", "Whisper")]

EARS_LANGUAGES = [
    ("auto", "Auto detect"),
    ("en", "English (en)"),
    ("hi", "Hindi (hi)"),
    ("te", "Telugu (te)"),
]

PROVIDERS = [("ollama", "Ollama"), ("openai", "OpenAI shape")]

PERSONAS = [("neutral", "Neutral"), ("serious", "Serious"), ("witty", "Witty")]

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

RESIDENT = "0 keeps it loaded. Answers come back faster while it is."

# WHAT WAKES HIM IS READ BY THE SAME SPEECH MODEL THAT READS EVERYTHING ELSE, SO IT CAN BE
# ANY WORDS AT ALL.
WAKE = "Separate several with commas. A name of one word only counts said first."

MORE = "When you stop on a word like and or the, how long he waits for the rest."

# HEADSETS TAKE THIS OVER THE MOMENT THEY CONNECT, AND SOME OF THEM HAND OVER NOTHING AT ALL.
MICROPHONE = "Which device does the hearing."

LOGS = "Everything Happy did, as he did it, the way it would have gone past in a terminal."

# WHAT IS SET ONCE AND NEVER AGAIN IS MARKED rare AND SITS BEHIND ONE MORE TAP.
BRAIN = [
    choice("brain.model", "Model", [], "gpt-oss:20b", "What does the talking.", source="models"),
    choice("brain.effort", "Thinking effort", EFFORTS, "low", "Low keeps answers conversational."),
    choice("brain.persona", "Personality", PERSONAS, "neutral",
           "Same facts, different tone. Witty lets a little dry sarcasm through."),
    choice("brain.provider", "Backend", PROVIDERS, "ollama", "Who runs the model.", rare=True),
    text("brain.url", "Address", "", "Empty uses the backend's own.", "http://localhost:11434",
         rare=True),
    number("brain.context", "Context window", 4096, 262144, 4096, 131072, "Sent every request.",
           "tokens", whole=True, rare=True),
    number("brain.temperature", "Temperature", 0, 2, 0.05, 0, "Higher wanders further.",
           rare=True),
    number("brain.history", "History carried", 2, 64, 2, 24, "Messages of backchat.", "msgs",
           whole=True, rare=True),
    # A BACKSTOP NOW, NOT THE BRAKE.
    number("brain.calls", "Tool rounds", 1, 60, 1, 40, "Before it has to answer.", "max",
           whole=True, rare=True),
    number("brain.timeout", "Timeout", 30, 900, 10, 300, "A cold load is not a dead server.",
           "sec", whole=True, rare=True),
    # WHAT THE BACKEND WORKED OUT ABOUT THE STANDING PROMPT AND THE TOOLS IS THROWN OUT WITH
    # THE MODEL, AND THAT IS THE FRONT OF EVERY REQUEST.
    number("brain.resident", "Stays loaded", 0, 240, 5, 0, RESIDENT, "min", whole=True,
           rare=True),
]

EARS = [
    text("ears.wake", "Wakes to", "hey happy, happy", WAKE, "hey happy, happy"),
    choice("ears.key", "Hold to talk", TALK_KEYS, "alt_r",
           "Held from any window, not just this. Nothing has to be said to him first."),
    choice("ears.microphone", "Microphone", [], "", MICROPHONE, source="microphones"),
    choice("ears.device", "Runs on", DEVICES, "cpu", "CPU is the sure one."),
    choice("ears.engine", "Engine", EARS_ENGINES, "whisper",
        "Parakeet is English only and fast. Whisper is multilingual and slower."),
    choice("ears.language", "Language", EARS_LANGUAGES, "auto",
            "Set one code like hi to skip detection when your language never changes.",
            rare=True),
    number("ears.after", "Waits for you", 2, 20, 1, 6, "After his name on its own.", "sec",
           whole=True),
    number("ears.more", "Waits mid sentence", 0.5, 10, 0.5, 2.5, MORE, "sec"),
    number("ears.level", "Hears you over", 0.002, 0.08, 0.002, 0.015,
           "Quieter than this is the room, not somebody talking.", rare=True),
    number("ears.gap", "Ends a take", 0.2, 3, 0.1, 0.8, "Silence that means you have paused.",
           "sec"),
    number("ears.hold", "Shortest take", 0.05, 2, 0.05, 0.25, "Briefer was a noise.", "sec",
           rare=True),
    number("ears.preroll", "Lead in", 0, 1.5, 0.05, 0.3, "Kept from before you were noticed.",
           "sec", rare=True),
    number("ears.tail", "Lead out", 0, 1.5, 0.05, 0.2, "Kept after you stop.", "sec", rare=True),
]

VOICE = [
    choice("voice.name", "Voice", [], "", "Whichever is installed.", source="voices"),
    toggle("voice.muted", "Mute", False, "Happy still answers, in writing."),
    number("voice.pace", "Pace", 0.6, 1.6, 0.05, 0.95, "Below one is faster speech."),
]

EYES = [
    choice("eyes.model", "Looking model", [], "qwen3-vl", "Only for looking.", source="models"),
    number("eyes.width", "Picture width", 512, 3024, 8, 1512, "Every byte is time.", "px",
           whole=True),
    number("eyes.context", "Context window", 4096, 131072, 4096, 32768, None, "tokens",
           whole=True, rare=True),
    choice("eyes.effort", "Thinking effort", EFFORTS, "off", "Off. It is asked what it sees.",
           rare=True),
]

CONNECTIONS = [
    toggle("mcps.answering", "Answer in chats", False,
           "Everything in a group named Happy. Anywhere else, say @happy yourself."),
    number("mcps.timeout", "Give up after", 5, 120, 5, 20, "A service is not this computer.",
           "sec", whole=True),
]

REMEMBERING = [
    number("memory.messages", "Keep messages", 0, 730, 1, 0, FOREVER, "days", whole=True),
    number("memory.recordings", "Keep recordings", 0, 730, 1, 0, FOREVER, "days", whole=True),
    action("memory.logs", "Full logs", "logs", "Open", LOGS, instant=True),
]

# EVERY ROW IN HERE IS FILLED IN BY THE RUNNING MACHINE, BECAUSE WHAT THE SYSTEM IS
# WITHHOLDING TODAY IS NOT SOMETHING A CATALOGUE CAN BE WRITTEN DOWN KNOWING.
ALLOWING = []

GROUPS = [
    group("brain", "Brain", "What does the thinking.", BRAIN,
          ["brain.model", "brain.effort", "brain.persona"]),
    group("ears", "Ears", "Hearing you, and when.", EARS, ["ears.wake", "ears.key"]),
    group("voice", "Voice", "How Happy sounds.", VOICE, ["voice.name", "voice.muted"]),
    group("eyes", "Eyes", "Looking at the screen.", EYES, ["eyes.model"]),
    group("mcps", "Connections", "Services that are not this computer.", CONNECTIONS),
    group("allowing", "Permissions", "What this computer lets Happy do.", ALLOWING),
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