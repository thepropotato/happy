"""Everyday commands handled instantly without a model, so they work the same on any brain or none."""

import re

from happy.tools import call

UNITS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
         "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
         "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
        "ninety": 90, "hundred": 100}
WORDS = {"max": 100, "maximum": 100, "full": 100, "min": 0, "minimum": 0, "half": 50, "off": 0, "zero": 0}

FILLER = re.compile(r"^(?:(?:hey|hi|hello|yo|ok|okay|so|um|uh|please|can you|could you|would you|will you|just|now|go ahead and|i want you to|i'd like you to)\s+)+")
POLITE = re.compile(r"\s+(?:please|for me|thanks|thank you|right now|now)$")


def number(text):
    """A spoken or written number from 0 to 100, or None."""
    text = text.strip().rstrip("%").replace(" percent", "").replace("-", " ").strip()
    if text.isdigit():
        return int(text)
    if text in WORDS:
        return WORDS[text]
    total = 0
    for word in text.split():
        if word in TENS:
            total += TENS[word]
        elif word in UNITS:
            total += UNITS[word]
        else:
            return None
    return total if text else None


def clean(text):
    text = text.lower().strip()
    text = re.sub(r"[.!?,]+$", "", text)
    text = re.sub(r"[,]", "", text)
    previous = None
    while previous != text:
        previous = text
        text = FILLER.sub("", text)
        text = POLITE.sub("", text)
    return text.strip()


LEVEL = r"(?:to |at )?(?P<n>[\w -]+?)(?: ?%| percent)?"
SET = r"(?:set |change |turn |make |put |bring )?(?:the |my )?"
UP = {"up", "higher", "brighter", "louder", "more", "increase", "raise", "brighten", "bump up"}
DOWN = {"down", "lower", "dimmer", "quieter", "softer", "less", "decrease", "reduce", "dim", "drop"}
CONTROLS = [("set_brightness", r"(?:(?:the )?screen(?:'s)? |display )?brightness(?: of (?:the |my )?(?:screen|display|laptop))?"),
            ("set_volume", r"(?:volume|sound)(?: of (?:the |my )?(?:laptop|mac|computer|speakers))?"),
            ("set_keyboard_light", r"keyboard (?:light|lights|backlight|brightness|back light)")]

# THE LAST CONTROL CHANGED, SO "MAKE IT FORTY" OR "A BIT MORE" RIGHT AFTER KNOWS WHAT "IT" IS.
last = {"tool": None}


def nudge(word, by=10):
    return {"change": "up" if word in UP else "down", "by": by}


def amount(text):
    """'by twenty' or 'a little' or 'a lot' inside a request, as a number."""
    match = re.search(r"\bby (?P<n>[\w -]+?)(?: ?%| percent)?$", text)
    if match and number(match.group("n")) is not None:
        return number(match.group("n"))
    if re.search(r"\b(?:a (?:little|bit|touch)|slightly|a little bit)\b", text):
        return 5
    if re.search(r"\b(?:a lot|much|way)\b", text):
        return 25
    return 10


def levels(text):
    """Brightness, volume and keyboard light, set or nudged, however it is said."""
    for name, noun in CONTROLS:
        match = re.fullmatch(SET + noun + " " + LEVEL, text)
        if match:
            word = match.group("n").strip()
            if word in UP or word in DOWN:
                return name, nudge(word)
            if word == "on" and name == "set_keyboard_light":
                return name, {"level": 60}
            value = number(word)
            if value is not None and 0 <= value <= 100:
                return name, {"level": value}
        match = re.fullmatch(r"(?:turn |push |bring )?(?:the |my )?" + noun + r" (?P<d>all the way )?(?P<w>up|down)(?: .*)?", text)
        if match:
            if match.group("d"):
                return name, {"level": 100 if match.group("w") == "up" else 0}
            return name, nudge(match.group("w"), amount(text))
        match = re.fullmatch(r"(?:turn |make )?(?P<w>up|down|increase|decrease|raise|lower|reduce|dim|brighten|drop|bump up) (?:the |my )?" + noun + r"(?: .*)?", text)
        if match and not re.search(r"\bto \w", text):
            return name, nudge(match.group("w"), amount(text))
        match = re.fullmatch(r"(?:turn |switch )(?P<w>on|off) (?:the |my )?" + noun, text) \
            or re.fullmatch(r"(?:turn |switch )?(?:the |my )?" + noun + r" (?P<w>on|off)", text)
        if match and name == "set_keyboard_light":
            return name, {"level": 60 if match.group("w") == "on" else 0}
        match = re.fullmatch(r"(?:max|maximum|full|min|minimum) " + noun, text)
        if match:
            return name, {"level": 100 if text.startswith(("max", "full")) else 0}
    match = re.fullmatch(r"(?:what(?:'s| is)|how (?:loud|bright) is) (?:the |my )?(?P<what>volume|sound|brightness|screen brightness|keyboard light|keyboard backlight)(?: at| level| set to)?(?: right now)?", text)
    if match:
        what = match.group("what")
        return ("set_volume" if what in ("volume", "sound") else "set_keyboard_light" if "keyboard" in what else "set_brightness"), {}
    simple = {
        "brighter": ("set_brightness", nudge("up", 15)), "dimmer": ("set_brightness", nudge("down", 15)),
        "dim the screen": ("set_brightness", nudge("down", 20)), "brighten the screen": ("set_brightness", nudge("up", 20)),
        "louder": ("set_volume", nudge("up")), "quieter": ("set_volume", nudge("down")), "softer": ("set_volume", nudge("down")),
        "mute": ("set_volume", {"muted": True}), "mute the sound": ("set_volume", {"muted": True}),
        "mute the volume": ("set_volume", {"muted": True}), "mute it": ("set_volume", {"muted": True}),
        "unmute": ("set_volume", {"muted": False}), "unmute the sound": ("set_volume", {"muted": False}),
        "unmute it": ("set_volume", {"muted": False}),
    }
    if text in simple:
        return simple[text]
    return again(text)


def again(text):
    """A follow-on about the control just changed: 'make it forty', 'a bit more', 'lower', 'turn it down'."""
    tool = last["tool"] or ("set_volume" if re.fullmatch(r"turn it (?:up|down)", text) else None)
    if not tool:
        return None
    match = re.fullmatch(r"(?:make it|set it to|put it (?:at|to)|change it to|take it to|bring it to|to|at) (?P<n>[\w -]+?)(?: ?%| percent)?", text)
    if match and number(match.group("n")) is not None and 0 <= number(match.group("n")) <= 100:
        return tool, {"level": number(match.group("n"))}
    if len(text.split()) > 6:
        return None
    if re.fullmatch(r"(?:turn it |make it |a (?:little |bit |touch )?|slightly |even |a lot |much |way )*(?:more|up|higher|brighter|louder)(?: (?:please|again|still))?", text):
        return tool, nudge("up", amount(text))
    if re.fullmatch(r"(?:turn it |make it |a (?:little |bit |touch )?|slightly |even |a lot |much |way )*(?:less|down|lower|dimmer|quieter|softer)(?: (?:please|again|still))?", text):
        return tool, nudge("down", amount(text))
    if text in ("lower it", "reduce it", "decrease it", "dim it", "drop it"):
        return tool, nudge("down")
    if text in ("raise it", "increase it", "brighten it", "bump it up"):
        return tool, nudge("up")
    return None


MEDIA = re.compile(r"(?P<verb>pause|play|resume|stop|unpause|continue) ?(?:the |this |my )?(?P<thing>video|music|song|track|movie|playback|audio|it|youtube|spotify|podcast)?(?: playing)?")


def media(text):
    match = MEDIA.fullmatch(text)
    if match:
        verb = match.group("verb")
        if verb == "play" and not match.group("thing"):
            return "media", {"action": "play"}
        if verb == "play" and match.group("thing") not in ("it", "video", "music", "audio"):
            return None
        return "media", {"action": "pause" if verb in ("pause", "stop") else "play"}
    loose = media_loose(text)
    if loose:
        return loose
    if re.fullmatch(r"(?:next|skip)(?: (?:this |the )?(?:song|track|video|one))?|skip it|play the next (?:song|track)", text):
        return "media", {"action": "next"}
    if re.fullmatch(r"(?:previous|last|go back a|play the previous) (?:song|track)|previous", text):
        return "media", {"action": "previous"}
    return None


ON_SCREEN = r"\b(?:this|that|the|it|my)\b"
THINGS = r"\b(?:video|videos|music|song|track|movie|film|episode|playback|audio|podcast|it|this|that)\b"
ELSEWHERE = r"\b(?:on youtube|on spotify|search|some|by|playlist|album|new|another|next|previous|open|find|called)\b"


def media_loose(text):
    """A short request to play or pause whatever is already on screen, said any of the usual ways."""
    words = text.split()
    if len(words) > 10 or re.search(ELSEWHERE, text) or not re.search(THINGS, text):
        return None
    if re.search(r"\b(?:pause|stop|hold)\b", text) and not re.search(r"\b(?:play|resume|continue|unpause)\b", text):
        return "media", {"action": "pause"}
    if re.search(r"\b(?:resume|continue|unpause|keep playing|carry on)\b", text) or re.search(r"\bplay\b", text) and re.search(ON_SCREEN, text):
        return "media", {"action": "play"}
    return None


def browser(text):
    if re.fullmatch(r"close (?:this |the |that |current |the current )?tab", text):
        return "browser_tabs", {"action": "close"}
    if re.fullmatch(r"(?:open )?(?:a )?new tab", text):
        return "browser_tabs", {"action": "new"}
    if re.fullmatch(r"(?:reopen|restore|bring back) (?:the |that )?(?:last )?(?:closed )?tab", text):
        return "browser_tabs", {"action": "reopen"}
    if re.fullmatch(r"(?:reload|refresh)(?: (?:the |this )?(?:page|tab))?", text):
        return "browser_tabs", {"action": "reload"}
    if re.fullmatch(r"close (?:this |the )?window", text):
        return "press_keys", {"keys": "cmd+w"}
    return None


SPOKEN_KEYS = {"command": "cmd", "control": "ctrl", "option": "alt", "alt": "alt", "shift": "shift", "cmd": "cmd",
               "ctrl": "ctrl", "enter": "return", "return": "return", "escape": "escape", "space": "space",
               "tab": "tab", "delete": "delete", "backspace": "backspace", "up": "up", "down": "down",
               "left": "left", "right": "right"}


def keys(text):
    match = re.fullmatch(r"(?:press|hit|type the shortcut) (?P<keys>[\w +-]+)", text)
    if not match:
        return None
    parts = [p for p in re.split(r"[\s+-]+", match.group("keys")) if p and p not in ("and", "the", "key", "plus")]
    combo = []
    for part in parts:
        if part in SPOKEN_KEYS:
            combo.append(SPOKEN_KEYS[part])
        elif len(part) == 1 or re.fullmatch(r"f\d{1,2}", part):
            combo.append(part)
        else:
            return None
    return ("press_keys", {"keys": "+".join(combo)}) if combo else None


SERVICES = r"(?P<what>e-?mail|mail|gmail|outlook|whatsapp|the internet|internet|wi-?fi|[\w.-]+ mcp(?: server)?|mcp(?: servers?)?|[\w.-]+ server|everything|anything|claude|the model)"


def connected(text):
    """Questions about whether a service is connected, answered from the connections themselves."""
    match = re.fullmatch(r"(?:is|are|check (?:if|whether)|do i have|have i) (?:my |the )?" + SERVICES +
                         r"(?: is| are)? (?:connected|set up|setup|linked|working|on|available|online)(?: right now| yet)?", text)
    if match:
        return "connections", {"about": match.group("what")}
    match = re.fullmatch(r"(?:do|can) you (?:have )?(?:access|connect(?:ion)?)(?: to)? (?:my |the )?(?P<what>[\w .-]+?)(?: account| mcp| server)?", text)
    if match:
        return "connections", {"about": match.group("what")}
    from happy.integrations import discovered

    names = "|".join(re.escape(n.lower()) for n in discovered.everything()) or "mcp"
    if (re.match(r"(?:is|are|which|what|do|does|check|tell me|can you check)\b", text)
            and re.search(r"\b(?:connected|working|linked|set up|hooked up|online|available)\b", text)
            and re.search(rf"\b(?:mcps?|servers?|e-?mail|mail|gmail|whatsapp|connectors?|internet|services?|{names})\b", text)):
        return "connections", {"about": text}
    if re.fullmatch(r"(?:what(?:'s| is| are)|which (?:services|mcps?|mcp servers|things) are) (?:connected|set up|linked)(?: right now)?|"
                    r"(?:show|list|check) (?:my |the )?(?:connections|mcp servers|mcps|services)", text):
        return "connections", {}
    return None


def computer(text):
    if re.fullmatch(r"lock (?:the |my )?(?:screen|computer|mac|laptop|pc)", text):
        return "computer", {"action": "lock"}
    if re.fullmatch(r"(?:turn on |switch to |enable |turn )?dark mode(?: on)?", text):
        return "computer", {"action": "dark_mode"}
    if re.fullmatch(r"(?:turn off dark mode|turn dark mode off|dark mode off|(?:turn on |switch to |enable )?light mode)", text):
        return "computer", {"action": "light_mode"}
    if re.fullmatch(r"(?:turn off|sleep) (?:the )?(?:screen|display)", text):
        return "computer", {"action": "sleep_display"}
    return None


def machine(text):
    """Battery, Wi-Fi and power, said the plain ways."""
    if re.fullmatch(r"(?:how much |what(?:'s| is) (?:the |my )?|check (?:the |my )?)?battery(?: level| percentage| left| life| status)?(?: is (?:left|there))?|"
                    r"how much (?:charge|battery) (?:is left|do i have)(?: left)?|is (?:the |my )?(?:laptop|mac|battery) charging", text):
        return "battery", {}
    match = re.fullmatch(r"(?:turn |switch )?(?:the )?wi-?fi (?P<w>on|off)|(?:turn |switch )(?P<v>on|off) (?:the )?wi-?fi", text)
    if match:
        return "wifi", {"action": match.group("w") or match.group("v")}
    if re.fullmatch(r"is (?:the |my )?wi-?fi (?:on|off)|(?:which|what) wi-?fi (?:network )?am i on|what(?:'s| is) (?:the |my )?wi-?fi", text):
        return "wifi", {}
    if re.fullmatch(r"(?:restart|reboot) (?:the |my )?(?:computer|mac|laptop|pc|system)", text):
        return "power", {"action": "restart"}
    if re.fullmatch(r"(?:shut down|shutdown|turn off|power off|switch off) (?:the |my )?(?:computer|mac|laptop|pc|system)", text):
        return "power", {"action": "shut_down"}
    if re.fullmatch(r"(?:put (?:the |my )?(?:computer|mac|laptop|pc) to sleep|(?:sleep|go to sleep) (?:the |my )?(?:computer|mac|laptop|pc))", text):
        return "power", {"action": "sleep"}
    if re.fullmatch(r"(?:cancel|stop|don't) (?:the )?(?:restart|shut ?down|reboot)", text):
        return "power", {"action": "cancel"}
    return None


def reminded(text):
    """Asking what reminders are set, which needs no model to answer."""
    if re.fullmatch(r"(?:what|which) reminders (?:do i have|have i (?:got|set)|are (?:set|there|coming up))(?: (?:today|now|right now))?|"
                    r"(?:list|show|read|tell me) (?:all )?(?:my |the )?reminders|(?:my |any )?reminders\??|do i have any reminders(?: set)?", text):
        return "reminder", {"action": "list"}
    match = re.fullmatch(r"(?:stop|don't|do not|no more) remind(?:ing)? me (?:to |about )?(?P<what>.+?)(?: anymore| any more)?", text)
    if match:
        return "reminder", {"action": "forget", "what": match.group("what")}
    return None


def forecast(text):
    """The weather right now, asked plainly; another day goes to the model, which answers only that day."""
    match = re.fullmatch(r"(?:what(?:'s| is) the |how(?:'s| is) the |check the |tell me the )?(?:weather|temperature)(?: like)?"
                         r"(?: (?:in|at|for) (?P<where>[a-z .,'-]+?))?(?: (?:today|now|right now|currently|at the moment|outside))?(?: like)?", text)
    if not match or re.search(r"\b(?:tomorrow|tonight|week|weekend|later|evening|morning|afternoon|day|days|\w+day)\b", match.group("where") or ""):
        return None
    return "weather", {"where": (match.group("where") or "").strip()}


def spoken_weather(result):
    """'Springfield, now: clear, 29°C (feels like 27°C), ...' said as a sentence without the symbols."""
    match = re.match(r"(?P<place>[^,]+)[^:]*, now: (?P<sky>[^,]+), (?P<t>-?\d+)°C \(feels like (?P<f>-?\d+)°C\).*"
                     r"high (?P<hi>-?\d+)°C, low (?P<lo>-?\d+)°C, (?P<rain>\d+)% chance", result)
    if not match:
        missing = re.match(r"Could not get the weather: found no place called (?P<place>.+?), by sound", result)
        return f"I couldn't find a place called {missing['place']}." if missing else result
    feels = f", feels like {match['f']}" if match["f"] != match["t"] else ""
    rain = "no rain expected" if int(match["rain"]) < 10 else f"{match['rain']} percent chance of rain"
    return f"{match['place']}: {match['sky']}, {match['t']} degrees{feels}. High of {match['hi']}, low of {match['lo']}, {rain}."


def apps(text):
    from happy.tools.apps import find_app

    match = re.fullmatch(r"(?:open|launch|start) (?:the |my )?(?P<app>[\w .+-]+?)(?: app)?", text)
    if match and match.group("app") not in ("it", "that", "this", "link", "file", "folder"):
        found, _ = find_app(match.group("app"))
        if found and (found.lower() == match.group("app") or found.lower().startswith(match.group("app"))
                      or match.group("app") in ("vs code", "vscode", "chrome", "settings", "terminal")):
            return "open_app", {"name": match.group("app")}
    match = re.fullmatch(r"(?:quit|close) (?:the |my )?(?P<app>[\w .+-]+?)(?: app)?", text)
    if match:
        from happy.system import native

        found, _ = find_app(match.group("app"))
        if found and found in native.running_apps():
            return "quit_app", {"name": match.group("app")}
    return None


GREETINGS = {
    "hi": "Hi! What can I do for you?", "hello": "Hello! What do you need?", "hey": "Hey! What can I do?",
    "hey there": "Hey! What can I do?", "hi there": "Hi! What can I do for you?", "yo": "Hey! What's up?",
    "good morning": "Good morning! What can I do?", "good afternoon": "Good afternoon! What do you need?",
    "good evening": "Good evening! What can I do?", "thanks": "Anytime.", "thank you": "You're welcome.",
    "thanks a lot": "Happy to help.", "thank you so much": "Anytime.", "cool": "Great.", "ok": "Okay.",
    "okay": "Okay.", "nice": "Glad that worked.", "are you there": "I'm here. What do you need?",
    "you there": "I'm here. What do you need?",
}

STOP = {"stop", "cancel", "never mind", "nevermind", "shut up", "be quiet", "quiet", "that's all", "nothing",
        "forget it", "stop talking", "ok stop", "okay stop", "enough"}

def spoken_connections(report):
    """'Email: not set up (add it in Setup)' read out as 'Email is not set up, add it in Setup.'"""
    out = []
    for line in report.splitlines():
        name, _, rest = line.partition(": ")
        state, _, detail = rest.partition(" (")
        name = re.sub(r"^MCP server (\S+) \(from ([^)]+)\)", r"The \1 server from \2", name)
        out.append(f"{name} is {state}{', ' + detail.rstrip(')') if detail else ''}.")
    return " ".join(out)


def spoken_level(result):
    """'Brightness went down from 57% to 47%.' said as 'Brightness down to 47.'"""
    match = re.match(r"(?P<name>[\w ]+) went (?P<way>up|down) from \d+% to (?P<now>\d+)%", result)
    if match:
        return f"{match.group('name')} {match.group('way')} to {match.group('now')}."
    return result.replace("%", "").replace(" is ", " is at ")


SPOKEN = {
    "connections": spoken_connections,
    "set_brightness": spoken_level,
    "set_volume": spoken_level,
    "set_keyboard_light": spoken_level,
    "weather": spoken_weather,
}


def clock(text):
    """Plain questions about the time or date, which need no model at all."""
    match = re.fullmatch(r"how (?:many|long) (?:days )?(?:are |is )?(?:there |left |is it )*(?:left )?(?:until|till|til|to|before|for) (?P<day>[\w' ]+?)(?: left)?", text)
    if match:
        from happy.tools.status import countable

        # A DAY ONLY THE PERSON KNOWS, LIKE THEIR BIRTHDAY, GOES TO THE MODEL, WHICH CAN LOOK IT UP IN WHAT IT REMEMBERS.
        return ("clock", {"until": match.group("day")}) if countable(match.group("day")) else None
    asked = r"(?:what(?:'s|s| is)?|tell me|and|what about|how about) (?:the )?(?:time|date|day)"
    after = r"(?: (?:is it|it is|is|now|right now|today|is today|of the week|please))*"
    if re.fullmatch(asked + after, text) or re.fullmatch(r"what(?:'s|s| is) today(?:'s date)?|(?:the )?(?:time|date) please", text):
        # ONLY WHAT WAS ASKED: A QUESTION ABOUT THE DATE ANSWERED WITH THE TIME TOO READS AS NOT LISTENING.
        named = [part for part in ("time", "date", "day") if re.search(rf"\b{part}\b", text)]
        return "clock", {"part": named[0] if len(named) == 1 else "date" if "today" in text and not named else "all"}
    return None


def speed(text):
    """Changes how quickly Happy speaks, not the sound volume."""
    if re.fullmatch(r"(?:talk|speak) faster", text):
        return "set_speech_speed", {"change": "up"}
    if re.fullmatch(r"(?:talk|speak) slower|slow down", text):
        return "set_speech_speed", {"change": "down"}
    if re.fullmatch(r"(?:(?:talk|speak) at )?normal speed", text):
        return "set_speech_speed", {"speed": 1.0}
    found = re.fullmatch(r"(?:set (?:the )?speed to|speed)\s+(\d+(?:\.\d+)?)\s*x?", text)
    if found:
        from happy.config import speech_speed

        return "set_speech_speed", {"speed": speech_speed(float(found.group(1)))}
    return None


def match(text):
    """The tool call an everyday command means, 'stop' for stop, or None for the brain."""
    said = clean(text)
    if said in STOP:
        return "stop", {}
    if said in GREETINGS:
        return "reply", {"text": GREETINGS[said]}
    for rule in (speed, levels, media, browser, keys, machine, connected, computer, forecast, reminded, apps, clock):
        try:
            found = rule(said)
        except Exception:
            found = None
        if found:
            return found
    return None


LEVELS = {"set_brightness", "set_volume", "set_keyboard_light"}


def remember(name):
    if name in LEVELS:
        last["tool"] = name


async def run(name, args):
    remember(name)
    result = await call(name, args)
    if isinstance(result, str) and name in SPOKEN and not result.startswith("Error"):
        return SPOKEN[name](result)
    return result if isinstance(result, str) else "Done."
