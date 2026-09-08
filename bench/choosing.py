"""ONE UTTERANCE, ONE TURN, ONE QUESTION: DID IT REACH FOR THE RIGHT TOOL.

NOT AN EVENING. A REPLAY SUITE TESTS WHAT SURVIVES ACROSS TURNS AND IS THE ONLY THING THAT
CAN; IT ALSO ONLY EVER COVERS THE PATHS SOMEBODY HAPPENED TO WALK ON THE DAY IT WAS RECORDED.
THESE COVER EVERY TOOL AND EVERY BOUNDARY BETWEEN TWO TOOLS THAT ARE EASY TO CONFUSE, AND
CARRY NOTHING ABOUT ANYBODY: NO PROJECT, NO CHANNEL, NO HANDLE, NO PATH.

A CASE IS SAID, expect (ANY ONE OF THESE IS RIGHT), forbid ("*" MEANS SAY SOMETHING AND CALL
NOTHING) AND OPTIONAL then (A CALL THAT MUST FOLLOW, OR IT IS PARTIAL)."""

# --- ONE OBVIOUS TOOL, NOTHING TO WEIGH UP ---
PLAIN = [
    dict(id="P1", said="turn the volume down a bit", expect=["system_control"]),
    dict(id="P2", said="make the screen brighter", expect=["system_control"]),
    dict(id="P3", said="turn the wifi off", expect=["system_control"]),
    dict(id="P4", said="what kind of computer is this?", expect=["system_info"]),
    dict(id="P5", said="what time is it and where am I?", expect=["where_we_are"]),
    dict(id="P6", said="what apps do I have installed?", expect=["list_installed_apps"]),
    dict(id="P7", said="how many r's are in strawberry?", expect=["letters"]),
    dict(id="P8", said="what's my name?", expect=["who_i_work_for"]),
    dict(id="P9", said="which services are connected?", expect=["connections"]),
    dict(id="P10", said="what windows do I have open?", expect=["list_open_windows"]),
    # THIS ONE FAILED THE 2026-08-31 RUN: HAPPY SAID IT COULD NOT SKIP A TRACK WHILE
    # system_control MAPS next ON MACOS. IT IS HERE BECAUSE IT ONCE WENT WRONG.
    dict(id="P11", said="what's playing? skip to the next track", expect=["system_control"]),
]

# --- GO AND LOOK, RATHER THAN ANSWER OUT OF THE PROMPT OR OUT OF MEMORY ---
GROUNDED = [
    dict(id="G1", said="what am I looking at right now?",
         expect=["current_activity", "screen", "list_open_windows"]),
    dict(id="G2", said="what does it say on my screen?", expect=["screen"]),
    dict(id="G3", said="what file am I working on?", expect=["file_in_front", "current_activity"]),
    dict(id="G4", said="what's in this picture on my desktop?",
         expect=["read_image", "find_files"]),
    dict(id="G5", said="what buttons are in this window?", expect=["list_controls"]),
]

# --- LOOK BEFORE STARTING ANYTHING: THE already_open DISCIPLINE ---
LOOK_FIRST = [
    dict(id="L1", said="put on some music", expect=["already_open"]),
    dict(id="L2", said="open youtube", expect=["already_open"]),
    dict(id="L3", said="play that video", expect=["already_open", "play_pause"]),
    dict(id="L4", said="open my downloads folder", expect=["already_open", "open_path"]),
    dict(id="L5", said="search the web for the weather", expect=["already_open", "search_web"]),
]

# --- THE PAIRS THAT ARE EASY TO CONFUSE. EACH ONE NAMES THE OTHER AS FORBIDDEN, BECAUSE
#     THE FAILURE IS NEVER "CALLED NOTHING", IT IS "CALLED THE NEIGHBOUR". ---
BOUNDARIES = [
    # SHOW IT TO THEM VERSUS READ IT FOR YOURSELF. ONE PUTS A PAGE ON THE SCREEN, THE OTHER
    # NEVER DOES, AND THE WORD THAT DECIDES IT IS "SHOW" AGAINST "WHAT DOES IT SAY".
    dict(id="B1", said="show me the wikipedia page for saturn",
         expect=["open_url", "already_open", "search_web"], forbid=["read_page"]),
    dict(id="B2", said="what does wikipedia say saturn's diameter is?",
         expect=["search_web", "read_page"], forbid=["open_url"]),

    # DELETING IS move_to_trash AND IS NEVER A COMMAND, WHATEVER THE SHAPE OF THE ASK.
    dict(id="B3", said="delete that file off my desktop",
         expect=["move_to_trash", "find_files", "file_in_front"], forbid=["run_command"]),
    dict(id="B4", said="get rid of the old screenshots in downloads",
         expect=["move_to_trash", "find_files", "list_folder"], forbid=["run_command"]),

    # WRITING A FILE IS write_file, AND A REDIRECT IN A COMMAND WIPES ONE UNREAD.
    dict(id="B5", said="make a text file on my desktop that says hello",
         expect=["write_file"], forbid=["run_command"]),
    dict(id="B6", said="make me a spreadsheet of the planets and their moons",
         expect=["write_document"], forbid=["write_file", "run_command"]),

    # SETTINGS ARE system_control, NEVER A COMMAND AND NEVER AN APP.
    dict(id="B7", said="mute everything", expect=["system_control"],
         forbid=["run_command", "open_app"]),

    # OPENING AN APP VERSUS OPENING A THING IN ONE.
    dict(id="B8", said="open the calculator", expect=["already_open", "open_app"],
         forbid=["open_path", "run_command"]),

    # A FOLDER FULL OF CODE IS READ BEFORE IT IS DESCRIBED, NOT GUESSED AT.
    dict(id="B9", said="what does this project do?",
         expect=["describe_project", "file_in_front"], forbid=["run_command"]),

    # A LIST OF WHAT IS IN A FOLDER IS list_folder, NOT A SEARCH AND NOT A COMMAND.
    dict(id="B10", said="what's in my documents folder?", expect=["list_folder"],
         forbid=["run_command", "find_files"]),

    # SAVING SOMETHING OFF THE WEB IS download, NOT A COMMAND AND NOT A BROWSER.
    dict(id="B11", said="save that pdf onto my computer",
         expect=["download", "already_open", "current_activity"], forbid=["run_command"]),
]

# --- MORE THAN ONE CALL, IN ORDER ---
SEQUENCES = [
    dict(id="Q1", said="find my resume and tell me what's in it",
         expect=["find_files"], then=["read_file"]),
    dict(id="Q2", said="remind me to call the dentist in an hour", expect=["reminder"]),
    dict(id="Q3", said="what reminders do I have?", expect=["reminder"]),
    dict(id="Q4", said="do the thing I taught you called wind down", expect=["routine"]),
    dict(id="Q5", said="remember that I prefer tea over coffee", expect=["remember"]),
    dict(id="Q6", said="what did I tell you I prefer to drink?", expect=["remember"]),
    dict(id="Q7", said="find me some pictures of red pandas and save them",
         expect=["download_images"]),
    dict(id="Q8", said="copy what's on my screen to the clipboard",
         expect=["screen"], then=["system_control"]),
]

# --- THE RIGHT ANSWER IS TO SAY SOMETHING AND CALL NOTHING ---
RESTRAINT = [
    dict(id="R1", said="thanks, that's all for now", expect=[], forbid=["*"]),
    dict(id="R2", said="actually never mind, don't do that", expect=[], forbid=["*"]),
    dict(id="R3", said="hi", expect=[], forbid=["*"]),
    dict(id="R4", said="what's the capital of France?", expect=[],
         forbid=["run_command", "system_control", "move_to_trash", "build"]),
    dict(id="R5", said="tell me a joke", expect=[], forbid=["*"]),
]

GROUPS = [
    ("plain", PLAIN),
    ("grounded", GROUNDED),
    ("look-first", LOOK_FIRST),
    ("boundary", BOUNDARIES),
    ("sequence", SEQUENCES),
    ("restraint", RESTRAINT),
]

CASES = [dict(each, category=name) for name, group in GROUPS for each in group]

# HALF OF EACH GROUP IS NEVER TUNED AGAINST, ONLY CHECKED. A CHANGE THAT LIFTS THE TUNING
# CASES AND DROPS THESE IS A CHANGE FITTED TO THE TEST RATHER THAN TO HAPPY, AND WITHOUT A
# SET NOBODY TUNES ON THERE IS NO WAY TO SEE THAT HAPPENING AT ALL.
HELD_OUT = {each["id"] for name, group in GROUPS for each in group[1::2]}


def held(case):
    return case["id"] in HELD_OUT


def score(case, called):
    """PASS, PARTIAL OR FAIL, FROM THE TOOL NAMES THE MODEL ACTUALLY CALLED.

    A CALL A GUARD TURNED BACK IS NOT A CALL THE MODEL GOT TO MAKE: THE SANDBOX RUNS THE REAL
    ARGUMENT CHECKS, AND SCORING A REFUSAL AS A CHOICE MARKS THE GUARD WORKING AS A FAULT."""
    names = [each["name"] for each in called if not each.get("refused")]
    expect = case.get("expect", [])
    forbid = case.get("forbid", [])
    then = case.get("then", [])

    if "*" in forbid and names:
        return "fail", f"called {names} when it should have just answered"

    for bad in forbid:
        if bad != "*" and bad in names:
            return "fail", f"called forbidden {bad}"

    if expect and not any(good in names for good in expect):
        return "fail", f"called {names or 'nothing'}, wanted one of {expect}"

    if then and not any(each in names for each in then):
        return "partial", f"never followed with one of {then}"

    return "pass", f"called {names}" if names else "answered without calling anything"
