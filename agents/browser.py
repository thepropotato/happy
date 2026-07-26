"""
THE BROWSER. THE ONE MODULE HERE THAT REALLY IS AN AGENT.

THE OTHERS ANSWER IN ONE CALL: A COMMAND RUNS, AN APP OPENS, A FACT COMES BACK.
A BROWSER DOES NOT. "SEND A MESSAGE TO MUM" IS A DOZEN LOOKS AND CLICKS, EACH
DECIDED BY WHAT THE LAST ONE PUT ON THE SCREEN. SO IT HAS ITS OWN LOOP, ITS OWN
MODEL AND ITS OWN CONTEXT, AND THE MAIN GRAPH ONLY EVER SEES A SENTENCE COME
BACK. IT NEVER SEES THE CLICKS.

IT IS ALSO SLOW. MEASURED HERE, READING ONE HEADLINE OFF A PAGE TOOK EIGHTY FOUR
SECONDS, SO ANYTHING REAL IS MINUTES. FAR TOO LONG TO HOLD THE VOICE LOOP, SO
browse() STARTS THE WORK AND RETURNS AT ONCE. HAPPY SAYS HE IS ON IT, YOU CARRY
ON TALKING TO HIM, AND HE SPEAKS UP AGAIN WHEN IT IS DONE.

AND IT RUNS IN ANOTHER PROCESS: THIS SAME FILE, RUN AGAIN WITH --run. NOT FOR
DEPENDENCIES, THEY SHARE THE ONE VIRTUALENV. FOR TWO REASONS THAT OUTLIVE ANY
VERSION PIN: A BROWSER THAT CRASHES MUST NOT TAKE HAPPY DOWN WITH IT, AND
browser-use OWNS AN ASYNCIO LOOP THAT HAS NO BUSINESS RUNNING UNDER A VOICE
ASSISTANT.

SO THE FIRST HALF OF THIS FILE NEVER IMPORTS browser-use: EVERY IMPORT OF IT
SITS BELOW THE LINE, IN CODE ONLY THE CHILD REACHES. THE TASK GOES DOWN, ONE
MARKED LINE OF JSON COMES BACK, AND NOTHING ELSE CROSSES BETWEEN THEM. THE CHILD
READS THE BACKEND OUT OF llm.py ITSELF, THE SAME WAY THE REST OF HAPPY DOES.
"""

import asyncio
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

from langchain_core.tools import tool

SELF = Path(__file__).resolve()
ROOT = SELF.parent.parent

# THIS FILE IS A MODULE AND ALSO A SCRIPT, SEE THE BOTTOM. RUN AS A SCRIPT,
# PYTHON PUTS agents/ ON THE PATH AND NOT THE ROOT, AND THE THREE IMPORTS BELOW
# WOULD NOT RESOLVE. HENCE THIS, BEFORE THEM RATHER THAN AT THE TOP.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import llm  # THE MODULE, NOT ITS NAMES: llm REACHES BACK INTO agents FOR THE APPS.
import providers
from agents import system as machine

# HOW THE CHILD IS TOLD IT IS THE CHILD, AND HOW ITS ONE ANSWER IS FOUND AGAIN
# AMONG EVERYTHING browser-use SEES FIT TO LOG BESIDE IT.
RUN = "--run"
MARK = "HAPPY-RESULT "

# THE PAGE, THE HISTORY AND A SIX THOUSAND TOKEN SYSTEM PROMPT ALL HAVE TO FIT.
# OLLAMA HANDS OUT 4096 UNLESS TOLD OTHERWISE, WHICH DOES NOT HOLD THE PROMPT
# ALONE, AND IT FAILS BY QUIETLY FORGETTING RATHER THAN BY COMPLAINING.
NUM_CTX = 32768

# NO IMAGINATION WANTED. IT IS FILLING IN A FORM, NOT WRITING ONE.
TEMPERATURE = 0

# HOW MANY LOOKS AND CLICKS BEFORE IT HAS TO GIVE UP AND SAY SO.
MAX_STEPS = 25

# SEEN, NOT HIDDEN. THE FIRST VISIT TO ANYTHING WORTH AUTOMATING WANTS A LOGIN,
# AND A QR CODE NOBODY CAN SEE IS A TASK THAT HANGS FOREVER FOR NO STATED REASON.
HEADLESS = False

# LOGINS LIVE HERE BETWEEN RUNS, SO WHATSAPP WEB IS SCANNED ONCE AND NOT DAILY.
# ITS OWN PROFILE, NEVER THE REAL ONE, AND NOT BY CHOICE: CHROMIUM SINCE 136
# REFUSES A DEBUGGING PORT ON THE PROFILE YOU BROWSE WITH, AND WILL NOT OPEN ONE
# A RUNNING BROWSER ALREADY HOLDS. SO AN ERRAND GETS THE BROWSER YOU CHOSE AND A
# PROFILE YOU SIGN IN TO ONCE. A PAGE THAT ONLY NEEDS OPENING SHOULD GO THROUGH
# system.open_url INSTEAD, WHICH LANDS IN THE REAL ONE, ALREADY SIGNED IN.
PROFILE = Path.home() / ".happy" / "browser"

# AND ONE OF THEM PER BROWSER. A CHROMIUM PROFILE BELONGS TO THE BRAND THAT MADE
# IT: HAND CHROME'S TO OPERA AND YOU GET A BROWSER THAT STARTS, LOSES ITS
# DEBUGGING CONNECTION HALF A MINUTE LATER, AND FAILS AS "browser not connected"
# WITH NOTHING SAYING WHY. browser-use GUARDS ITS OWN DEFAULT DIRECTORY THE SAME
# WAY. IT ALSO MEANS CHANGING DEFAULT BROWSER LEAVES THE OLD LOGINS WHERE THEY
# ARE, RATHER THAN DROPPING A NEW ENGINE ONTO THEM.
BRAND = "browser-{name}"

# LONG, BECAUSE THE WHOLE POINT IS THAT THESE TAKE MINUTES. BUT NOT FOREVER, OR A
# PAGE WAITING ON A LOGIN NOBODY WILL GIVE IT WOULD SIT THERE ALL DAY.
TIMEOUT_SECONDS = 900

STARTED = "Started. Carry on, I will say when it is done."
BUSY = "Already working on something in the browser: "
NOTHING = "Nothing running, and nothing finished since you last asked."
MISSING = "browser-use is not installed. Run: pip install -r requirements.txt"

announce = None  # SET BY WHOEVER OWNS THE VOICE. SEE announces().

job = None
lock = threading.Lock()


class Job:
    """ONE BROWSER ERRAND, RUNNING IN ITS OWN PROCESS, WATCHED BY ITS OWN THREAD."""

    def __init__(self, task):
        self.task = task
        self.answer = None
        self.failed = None
        self.thread = threading.Thread(target=self.work, daemon=True)
        self.thread.start()

    def running(self):
        return self.thread.is_alive()

    def work(self):
        try:
            result = run(self.task)
        except Exception as error:  # A DEAD BROWSER MUST NOT TAKE HAPPY WITH IT.
            result = {"failed": f"{error.__class__.__name__}: {error}"}

        self.failed = result.get("failed")
        self.answer = result.get("answer")

        if announce:
            announce(self.report())

    def report(self):
        if self.failed:
            return f"That browser job did not work out. {self.failed}"

        if not self.answer:
            return f"Finished {self.task}, but it came back with nothing to tell you."

        return f"About {self.task}. {self.answer}"


def run(task):
    """DRIVE THE BROWSER UNTIL THE TASK IS ANSWERED. BLOCKS FOR MINUTES."""
    try:
        done = subprocess.run(
            [sys.executable, str(SELF), RUN, task],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            cwd=str(ROOT),
        )
    except subprocess.TimeoutExpired:
        return {"failed": f"It gave up after {TIMEOUT_SECONDS // 60} minutes."}

    return read(done)


def read(done):
    """THE MARKED LINE OUT OF EVERYTHING browser-use SAW FIT TO PRINT."""
    for line in reversed((done.stdout or "").splitlines()):
        if line.startswith(MARK):
            return json.loads(line[len(MARK) :])

    complaint = (done.stderr or "").strip().splitlines()

    return {"failed": complaint[-1][:200] if complaint else "It said nothing at all."}


def announces(handler):
    """WIRE UP HOW HAPPY SPEAKS UP WHEN A BROWSER JOB FINISHES.

    handler(words) -> None, CALLED FROM THE JOB'S OWN THREAD.
    """
    global announce

    announce = handler


def busy():
    return job is not None and job.running()


# TOOLS. THE DESCRIPTIONS BELOW ARE READ BY THE MODEL, NOT BY US, SO THEY ARE
# WRITTEN AS PLAIN PROSE RATHER THAN AS COMMENTS.


@tool
def browse(task: str) -> str:
    """Do something on the web that takes more than one step: look something up
    across pages, fill in a form, or use a web app like WhatsApp Web, Gmail or a
    calendar. Describe the whole errand in one sentence, the way you would ask a
    person, for example "on WhatsApp Web send mum a message saying I am running
    late" or "find the cheapest direct flight to Delhi on Friday".

    Only for errands that take several steps. If an address on its own would do
    it, opening a site or playing a video or running a search, use open_url: it
    is instant and it uses the browser the user is already signed in to.

    This takes minutes, so it runs in the background and returns straight away.
    Tell the user you have started and carry on talking to them. You will be told
    when it finishes, so do not promise to check on it yourself, and do not call
    this again with the same task to find out whether it is done."""
    global job

    with lock:
        if busy():
            return BUSY + job.task  # ONE BROWSER, ONE ERRAND AT A TIME.

        job = Job(task)

    return STARTED


@tool
def browsing_status() -> str:
    """Say whether the background browser job is still going, and what came back
    if it has finished. Use this only when the user asks, for example "is that
    done yet" or "what did it say"."""
    if job is None:
        return NOTHING

    return f"Still working on: {job.task}" if job.running() else job.report()


TOOLS = [browse, browsing_status]


# THE CHILD. NOTHING PAST THIS POINT RUNS IN HAPPY'S OWN PROCESS, AND NOTHING
# ABOVE IT TOUCHES browser-use.


# browser-use WILL NOT TAKE A LANGCHAIN MODEL, SO IT GETS ITS OWN CLIENT FOR
# WHICHEVER BACKEND providers.py WAS POINTED AT. THE NAME IS SHARED, THE CLIENT
# IS NOT, AND THESE TWO DISAGREE ON MORE THAN THE LANGCHAIN ONES DO: OLLAMA'S
# TAKES A host AND A BAG OF OPTIONS, THE OPENAI ONE TAKES A base_url AND A KEY.
# THE DIFFERENCE IS SPELLED OUT BELOW RATHER THAN ABSTRACTED, BECAUSE THERE ARE
# TWO OF THEM.
CLIENTS = {providers.OLLAMA: "ChatOllama", providers.OPENAI: "ChatOpenAI"}

UNKNOWN = "no browser client for the {provider} provider"


def quarters(binary):
    """WHERE THIS PARTICULAR BROWSER'S LOGINS LIVE. SEE BRAND ABOVE FOR WHY EACH
    ONE GETS ITS OWN, AND NOT ONE SHARED BETWEEN THEM."""
    if binary is None:  # browser-use PICKED IT, SO THE PLAIN ONE IS RIGHT.
        return PROFILE

    name = Path(binary).stem.lower().replace(" ", "-")

    return PROFILE.parent / BRAND.format(name=name)


def thinker():
    """THE MODEL, BUILT THE WAY browser-use'S OWN CLIENT WANTS IT."""
    import browser_use

    if llm.PROVIDER not in CLIENTS:
        raise ValueError(UNKNOWN.format(provider=llm.PROVIDER))

    chat = getattr(browser_use, CLIENTS[llm.PROVIDER])

    if llm.PROVIDER == providers.OLLAMA:
        return chat(
            model=llm.MODEL,
            host=llm.url(),
            ollama_options={"num_ctx": NUM_CTX, "temperature": TEMPERATURE},
        )

    return chat(
        model=llm.MODEL,
        base_url=llm.url(),
        api_key=llm.credential(),
        temperature=TEMPERATURE,
    )


async def drive(task):
    """THE LOOP ITSELF. LOOKS, CLICKS, AND EVENTUALLY AN ANSWER."""
    from browser_use import Agent
    from browser_use.browser import BrowserProfile

    # THE BROWSER THE PERSON ACTUALLY CHOSE, WHEN IT IS ONE THAT CAN BE DRIVEN.
    # None LEAVES THE CHOICE TO browser-use, WHICH GOES LOOKING FOR A CHROMIUM OF
    # ITS OWN. ASKED EVERY RUN RATHER THAN AT IMPORT, BECAUSE A DEFAULT BROWSER
    # IS A THING PEOPLE CHANGE.
    chosen = machine.drivable_browser()
    home = quarters(chosen)

    home.mkdir(parents=True, exist_ok=True)

    profile = BrowserProfile(
        user_data_dir=str(home),
        headless=HEADLESS,
        **({"executable_path": str(chosen)} if chosen else {}),
    )

    agent = Agent(task=task, llm=thinker(), browser_profile=profile, use_vision=False)
    history = await agent.run(max_steps=MAX_STEPS)

    return {
        "answer": history.final_result(),
        "steps": len(history.history),
        "done": history.is_done(),
    }


def worker(task):
    """THE CHILD'S WHOLE LIFE: DRIVE THE BROWSER, PRINT ONE LINE, EXIT."""
    # BOTH BEFORE browser-use IS IMPORTED. IT PHONES HOME UNLESS TOLD NOT TO,
    # WHICH IS NOT WHAT "COMPLETELY LOCAL" MEANS.
    os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")
    os.environ.setdefault("BROWSER_USE_CLOUD_SYNC", "false")

    try:
        import browser_use  # NOT USED HERE. IMPORTED TO SAY SO PLAINLY IF ABSENT.
    except ImportError:
        return say({"failed": MISSING})

    try:
        return say(asyncio.run(drive(task)))
    except Exception as error:
        return say({"failed": f"{error.__class__.__name__}: {error}"})


def say(result):
    print(MARK + json.dumps(result), flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == RUN:
        worker(sys.argv[2])
    else:  # BY HAND: ONE ERRAND, STRAIGHT THROUGH, NOTHING ELSE RUNNING.
        errand = " ".join(sys.argv[1:]) or "go to example.com and read me the heading"
        print(f"task: {errand}\n")
        print(json.dumps(run(errand), indent=2))
