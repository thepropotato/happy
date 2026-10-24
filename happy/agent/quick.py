"""Everyday commands handled instantly without a model, so they work the same on any brain or none."""

import re

from happy.tools import call

UNITS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
         "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
         "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
        "ninety": 90, "hundred": 100}
WORDS = {"max": 100, "maximum": 100, "full": 100, "min": 0, "minimum": 0, "half": 50, "off": 0, "zero": 0}

FILLER = re.compile(r"^(?:(?:hey|ok|okay|so|um|uh|please|can you|could you|would you|will you|just|now|go ahead and|i want you to|i'd like you to)\s+)+")
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
UP = {"up", "higher", "brighter", "louder", "more", "increase", "raise"}
DOWN = {"down", "lower", "dimmer", "quieter", "softer", "less", "decrease", "reduce"}


def levels(text):
    """Brightness, volume and keyboard light, set or nudged."""
    targets = [("set_brightness", r"(?:screen |display )?brightness", "Brightness"),
               ("set_volume", r"(?:volume|sound)", "Volume"),
               ("set_keyboard_light", r"keyboard (?:light|lights|backlight|brightness|back light)", "Keyboard light")]
    for name, noun, spoken in targets:
        match = re.fullmatch(SET + noun + " " + LEVEL, text)
        if match:
            word = match.group("n").strip()
            if word in UP or word in DOWN:
                return name, {"percent": 10 if word in UP else -10, "relative": True}
            if word == "on" and name == "set_keyboard_light":
                return name, {"percent": 60}
            value = number(word)
            if value is not None and 0 <= value <= 100:
                return name, {"percent": value}
        match = re.fullmatch(r"(?:turn |push |bring )?(?:the |my )?" + noun + r" (?P<d>all the way )?(?P<w>up|down)", text) \
            or re.fullmatch(r"(?:turn )?(?P<w>up|down|increase|decrease|raise|lower|reduce) (?:the |my )?" + noun, text)
        if match:
            up = match.group("w") in UP
            if "d" in match.groupdict() and match.group("d"):
                return name, {"percent": 100 if up else 0}
            return name, {"percent": 10 if up else -10, "relative": True}
        match = re.fullmatch(r"(?:turn |switch )(?P<w>on|off) (?:the |my )?" + noun, text) \
            or re.fullmatch(r"(?:turn |switch )?(?:the |my )?" + noun + r" (?P<w>on|off)", text)
        if match and name == "set_keyboard_light":
            return name, {"percent": 60 if match.group("w") == "on" else 0}
        match = re.fullmatch(r"(?:max|maximum|full|min|minimum) " + noun, text)
        if match:
            return name, {"percent": 100 if text.startswith(("max", "full")) else 0}
    match = re.fullmatch(r"(?:what(?:'s| is)|how (?:loud|bright) is) (?:the |my )?(?P<what>volume|sound|brightness|screen brightness|keyboard light|keyboard backlight)(?: at| level| set to)?(?: right now)?", text)
    if match:
        what = match.group("what")
        return ("set_volume" if what in ("volume", "sound") else "set_keyboard_light" if "keyboard" in what else "set_brightness"), {}
    simple = {
        "brighter": ("set_brightness", {"percent": 15, "relative": True}),
        "dimmer": ("set_brightness", {"percent": -15, "relative": True}),
        "dim the screen": ("set_brightness", {"percent": -20, "relative": True}),
        "brighten the screen": ("set_brightness", {"percent": 20, "relative": True}),
        "louder": ("set_volume", {"percent": 10, "relative": True}),
        "quieter": ("set_volume", {"percent": -10, "relative": True}),
        "softer": ("set_volume", {"percent": -10, "relative": True}),
        "turn it up": ("set_volume", {"percent": 10, "relative": True}),
        "turn it down": ("set_volume", {"percent": -10, "relative": True}),
        "mute": ("set_volume", {"muted": True}),
        "mute the sound": ("set_volume", {"muted": True}),
        "mute the volume": ("set_volume", {"muted": True}),
        "mute it": ("set_volume", {"muted": True}),
        "unmute": ("set_volume", {"muted": False}),
        "unmute the sound": ("set_volume", {"muted": False}),
        "unmute it": ("set_volume", {"muted": False}),
    }
    return simple.get(text)


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


SPOKEN = {
    "connections": spoken_connections,
    "set_brightness": lambda r: r.replace("Brightness is now ", "Brightness at ").replace("%.", "."),
    "set_volume": lambda r: r.replace("Volume is now ", "Volume at ").replace("%.", "."),
    "set_keyboard_light": lambda r: r.replace("Keyboard light is now ", "Keyboard light at ").replace("%.", "."),
}


def match(text):
    """The tool call an everyday command means, 'stop' for stop, or None for the brain."""
    said = clean(text)
    if said in STOP:
        return "stop", {}
    for rule in (levels, media, browser, keys, connected, computer, apps):
        try:
            found = rule(said)
        except Exception:
            found = None
        if found:
            return found
    return None


async def run(name, args):
    result = await call(name, args)
    if isinstance(result, str) and name in SPOKEN and not result.startswith("Error"):
        return SPOKEN[name](result)
    return result if isinstance(result, str) else "Done."
