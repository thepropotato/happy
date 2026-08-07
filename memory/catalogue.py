"""EVERY KNOB HAPPY HAS, IN THE ORDER A PERSON WOULD LOOK FOR THEM.

THE DEFAULTS LIVE HERE AND NOWHERE ELSE. A MODULE THAT WANTS ONE ASKS
memory.settings FOR IT, SO CHANGING A NUMBER IS NEVER EDITING CODE.
"""

from memory.knobs import action, choice, group, number, text, toggle

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

FOREVER = "0 keeps everything."

# WHAT WAKES HIM IS READ BY THE SAME SPEECH MODEL THAT READS EVERYTHING ELSE, SO
# IT CAN BE ANY WORDS AT ALL. TWO OR THREE OF THEM: ONE IS SAID BY ACCIDENT ALL
# DAY, AND A SENTENCE IS SOMETHING NOBODY WILL SAY THE SAME WAY TWICE.
WAKE = "Two or three words. Happy answers anything said after them."

LOGS = "Every turn in a browser, with what each tool was given and what came back."

# WHAT IS SET ONCE AND NEVER AGAIN IS MARKED rare AND SITS BEHIND ONE MORE TAP.
BRAIN = [
    choice("brain.model", "Model", [], "gpt-oss:20b", "What does the talking.", source="models"),
    choice("brain.effort", "Thinking effort", EFFORTS, "low", "Low keeps answers conversational."),
    choice("brain.provider", "Backend", PROVIDERS, "ollama", "Who runs the model.", rare=True),
    text("brain.url", "Address", "", "Empty uses the backend's own.", "http://localhost:11434",
         rare=True),
    number("brain.context", "Context window", 4096, 262144, 4096, 131072, "Sent every request.",
           "tokens", whole=True, rare=True),
    number("brain.temperature", "Temperature", 0, 2, 0.05, 0.7, "Higher wanders further.",
           rare=True),
    number("brain.history", "History carried", 2, 64, 2, 24, "Messages of backchat.", "msgs",
           whole=True, rare=True),
    # A BACKSTOP NOW, NOT THE BRAKE. GETTING NOWHERE IS CAUGHT BY THREE NOS IN A
    # ROW, WHICH IS THE SHAPE THAT ACTUALLY WENT WRONG; THIS ONLY CATCHES A LOOP
    # WHERE EVERY CALL WORKS AND NONE OF THEM HELP. FOURTEEN WAS SIZED FOR AN
    # ERRAND GOING PERFECTLY AND CUT OFF EVERY ONE THAT NEEDED A SECOND GO.
    number("brain.calls", "Tool rounds", 1, 60, 1, 40, "Before it has to answer.", "max",
           whole=True, rare=True),
    number("brain.timeout", "Timeout", 30, 900, 10, 300, "A cold load is not a dead server.",
           "sec", whole=True, rare=True),
]

EARS = [
    text("ears.wake", "Wakes to", "hey happy", WAKE, "hey happy"),
    choice("ears.device", "Runs on", DEVICES, "cpu", "CPU is the sure one."),
    choice("ears.engine", "Engine", EARS_ENGINES, "whisper",
        "Parakeet is English only and fast. Whisper is multilingual and slower."),
    choice("ears.language", "Language", EARS_LANGUAGES, "auto",
            "Set one code like hi to skip detection when your language never changes.",
            rare=True),
    number("ears.after", "Waits for you", 2, 20, 1, 6, "After his name on its own.", "sec",
           whole=True),
    number("ears.level", "Hears you over", 0.002, 0.08, 0.002, 0.015,
           "Quieter than this is the room, not somebody talking.", rare=True),
    number("ears.gap", "Ends a take", 0.2, 3, 0.1, 0.7, "Silence that means you have finished.",
           "sec", rare=True),
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
    toggle("mcps.confirm", "Ask before changing", True, "Anything that is not just looking."),
    toggle("mcps.answering", "Answer your own chat", False,
           "Say @happy in a message, or hey happy in a voice note."),
    number("mcps.timeout", "Give up after", 5, 120, 5, 20, "A service is not this computer.",
           "sec", whole=True),
]

REMEMBERING = [
    number("memory.messages", "Keep messages", 0, 730, 1, 0, FOREVER, "days", whole=True),
    number("memory.recordings", "Keep recordings", 0, 730, 1, 0, FOREVER, "days", whole=True),
    action("memory.logs", "Full logs", "logs", "Open", LOGS, instant=True),
]

GROUPS = [
    group("brain", "Brain", "What does the thinking.", BRAIN, ["brain.model", "brain.effort"]),
    group("ears", "Ears", "Hearing you, and when.", EARS, ["ears.wake"]),
    group("voice", "Voice", "How Happy sounds.", VOICE, ["voice.name", "voice.muted"]),
    group("eyes", "Eyes", "Looking at the screen.", EYES, ["eyes.model"]),
    group("mcps", "Connections", "Services that are not this computer.", CONNECTIONS),
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
