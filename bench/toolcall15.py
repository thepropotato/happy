"""TOOLCALL-15: FIFTEEN SPOKEN INSTRUCTIONS, FIVE CATEGORIES, ONE EXPECTED TOOL EACH."""

# EACH SCENARIO NAMES THE TOOLS THAT COUNT AS RIGHT AND THE ONES THAT COUNT AS WRONG.
SCENARIOS = [
    # --- SIMPLE: ONE OBVIOUS TOOL ---
    dict(id="S1", category="simple", said="turn the volume down a bit",
         expect=["system_control"], forbid=[]),
    dict(id="S2", category="simple", said="what's playing? skip to the next track",
         expect=["system_control"], forbid=[]),
    dict(id="S3", category="simple", said="make the screen brighter",
         expect=["system_control"], forbid=[]),

    # --- GROUNDED: MUST GO AND LOOK RATHER THAN ANSWER FROM THE PROMPT ---
    dict(id="G1", category="grounded", said="what am I looking at right now?",
         expect=["current_activity", "screen", "list_open_windows"], forbid=[]),
    dict(id="G2", category="grounded", said="how many r's are in strawberry?",
         expect=["letters"], forbid=[]),
    dict(id="G3", category="grounded", said="what kind of computer is this?",
         expect=["system_info"], forbid=[]),

    # --- LOOK-FIRST: THE already_open DISCIPLINE BEFORE OPENING ANYTHING ---
    dict(id="L1", category="look-first", said="put on some music",
         expect=["already_open"], forbid=[]),
    dict(id="L2", category="look-first", said="open youtube",
         expect=["already_open"], forbid=[]),
    dict(id="L3", category="look-first", said="search the web for the weather in Hyderabad",
         expect=["already_open", "search_web"], forbid=[]),

    # --- MULTI-STEP: MORE THAN ONE CALL, IN ORDER ---
    dict(id="M1", category="multi-step",
         said="find my resume and tell me what's in it",
         expect=["find_files"], then=["read_file"], forbid=[]),
    dict(id="M2", category="multi-step",
         said="copy what's on my screen to the clipboard",
         expect=["screen"], then=["system_control"], forbid=[]),
    dict(id="M3", category="multi-step",
         said="remind me to call mum in an hour",
         expect=["reminder"], forbid=[]),

    # --- RESTRAINT: THE RIGHT ANSWER IS TO SAY SOMETHING, NOT TO CALL ANYTHING ---
    dict(id="R1", category="restraint", said="thanks, that's all for now",
         expect=[], forbid=["*"]),
    dict(id="R2", category="restraint", said="what's the capital of France?",
         expect=[], forbid=["run_command", "system_control", "move_to_trash"]),
    dict(id="R3", category="restraint",
         said="actually never mind, don't do that",
         expect=[], forbid=["*"]),
]


def score(scenario, called):
    """PASS, PARTIAL OR FAIL, FROM THE TOOL NAMES THE MODEL ACTUALLY CALLED."""
    names = [c["name"] for c in called]
    expect, forbid = scenario["expect"], scenario.get("forbid", [])
    following = scenario.get("then", [])

    if "*" in forbid and names:
        return "fail", f"called {names} when it should have just answered"

    for bad in forbid:
        if bad != "*" and bad in names:
            return "fail", f"called forbidden {bad}"

    if not expect:
        return ("pass", "answered without calling anything") if not names else \
               ("partial", f"answered but also called {names}")

    if not any(good in names for good in expect):
        return "fail", f"called {names or 'nothing'}, wanted one of {expect}"

    if following and not any(nxt in names for nxt in following):
        return "partial", f"got {expect} but never followed with {following}"

    return "pass", f"called {names}"
