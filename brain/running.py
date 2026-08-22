"""ONE ROUTINE, RUN ON ITS OWN: ITS OWN CONTEXT, AND ONLY THE TOOLS IT NAMED."""

from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware
from langchain_core.messages import HumanMessage

import hands
import mcps
from brain import model as brain, persona
from brain.prompt import STANDING
from brain.wording import written
from brain.wrapping import (
    LIMIT, Stuck, doing, keep_count, keep_going, keep_record, keep_trying,
)
from hands.routines import picking
from memory import routines, settings

# A ROUTINE IS A KNOWN JOB OF A KNOWN LENGTH, SO IT IS BUDGETED BY ITS STEPS AND NOT BY THE
# OPEN ENDED NUMBER AN ERRAND GETS. SPARE IS ROOM TO TRY A FAILED TOOL ANOTHER WAY, FLOOR
# KEEPS A ONE STEP ROUTINE FROM HAVING NO ROOM AT ALL, AND brain.calls IS STILL THE CEILING
# OVER EVERYTHING BECAUSE NOTHING HERE MAY OUTRUN WHAT THE PERSON SET.
SPARE = 3
FLOOR = 8
CEILING = 30

RAN_OUT = 'I got partway through "{name}" and ran out of steps before it was finished.'

NOTHING = 'I ran "{name}" but never got an answer out of it.'

# SHOWN OVER THE TOOLS A ROUTINE IS ABOUT TO USE, SO WHICH ROUTINE PICKED THEM UP IS NOT
# SOMETHING TO WORK OUT FROM THE CALLS THEMSELVES. SHOWN AND NEVER SAID.
STARTING = 'Running "{name}"'

# A ROUTINE THAT NAMED TOOLS AND THEN TOUCHED NONE OF THEM DID NOT RUN, WHATEVER IT WROTE.
# USUALLY IT WAS SAVED OFF PART OF A JOB AND SO STARTS FROM SOMETHING IT HAS NOT GOT.
NEVER = '"{name}" did not actually run — it never used any of its own tools. It said: {said}'

# A TOOL NAME IS NEVER READ OUT LOUD, SO WHAT IS MISSING IS NAMED AS THE SERVICE BEHIND IT,
# AND NEVER AS A BARE NO: THE ROW THAT FIXES IT IS SAID IN THE SAME BREATH.
GONE = '"{name}" needs {which}, which {is_} not connected. That is in Happy\'s settings, under Connections.'

# NOTHING KNOWS WHAT THIS ONE WANTS, WHICH MEANS A TOOL THAT WAS RENAMED OR TAKEN AWAY.
BROKEN = '"{name}" was built on something that is not part of me any more, so it will not run.'

kept = None
made = None


def plainly(said):
    """THE ANSWER TO A ROUTINE ASKED FOR BY NAME, OR None IF THAT IS NOT WHAT WAS SAID.

    "RUN MY MORNING BRIEF" IS AN INSTRUCTION AND NOT A QUESTION, AND LEFT TO THE MODEL IT IS
    ONLY MOSTLY OBEYED: IT READS THE LINE SAYING WHAT THE ROUTINE DOES, DECIDES IT COULD DO
    THAT ITSELF, AND DOES, WHICH IS THE ONE THING A SAVED ROUTINE EXISTS TO STOP. SO THE
    PLAIN FORM IS ANSWERED HERE, BEFORE THE MODEL IS ASKED ANYTHING. ANYTHING VAGUER THAN A
    NAME STILL GOES TO IT, WHICH IS WHERE JUDGEMENT BELONGS."""
    found = picking.spoken(said)

    if found is None:
        return None

    routines.ran(found["name"])

    return run(found, said)


def run(found, said):
    """THE ROUTINE'S ANSWER, IN ONE STRING, WHATEVER HAPPENED TO IT."""
    bound, missing = bind(found)

    if missing:
        return unavailable(found, missing)

    doing(STARTING.format(name=found["name"]))

    graph = create_agent(
        model=talker(),
        tools=bound,
        system_prompt=told(found),
        middleware=[
            keep_count,
            keep_record,
            keep_going,
            ModelCallLimitMiddleware(run_limit=rounds(found)),
            keep_trying,
        ],
    )

    try:
        done = graph.invoke({"messages": [HumanMessage(said)]})
    except Stuck as stuck:
        return str(stuck)

    return answered(done["messages"][-1].text.strip(), found, done["messages"])


def bind(found):
    """ONLY THE TOOLS THIS ROUTINE NAMED, AND WHICHEVER OF THEM HAVE SINCE GONE.

    CUTTING SIXTY TOOLS DOWN TO FOUR IS THE LARGEST SINGLE THING THAT CAN BE DONE FOR A
    SMALL MODEL PICKING THE RIGHT ONE, SO A ROUTINE THAT NAMED ITS TOOLS RUNS AGAINST
    THOSE AND NOTHING ELSE. ONE THAT NAMED NONE GETS EVERYTHING AND IS THE WEAKER FOR IT."""
    offered = hands.tools()
    wanted = set(found.get("tools") or ())

    if not wanted:
        return offered, []

    here = {each.name for each in offered}

    return [each for each in offered if each.name in wanted], sorted(wanted - here)


def unavailable(found, missing):
    """WHY A ROUTINE CANNOT RUN, SAID IN THINGS A PERSON HAS HEARD OF."""
    services = sorted({each for each in (mcps.whose(name) for name in missing) if each})

    if not services:
        return BROKEN.format(name=found["name"])

    return GONE.format(
        name=found["name"],
        which=" and ".join(services),
        is_="is" if len(services) == 1 else "are",
    )


def told(found):
    """THE STANDING RULES, THEN THE ROUTINE, WHICH GOES LAST AND SO WEIGHS MOST."""
    tone = persona.nudge(settings.get("brain.persona"))

    return "\n\n".join(each for each in (STANDING, tone, written(found)) if each)


def rounds(found):
    """ENOUGH GOES FOR EVERY STEP AND A LITTLE OVER, AND NOT ONE MORE.

    A ROUTINE THAT HAS GONE WRONG IS WORTH STOPPING QUICKLY: ITS STEPS ARE WRITTEN DOWN, SO
    SPENDING AN ERRAND'S WHOLE BUDGET ON FOUR OF THEM IS MINUTES OF NOTHING HAPPENING."""
    steps = len([each for each in (found.get("steps") or "").splitlines() if each.strip()])

    return min(settings.get("brain.calls"), CEILING, max(steps + SPARE, FLOOR))


def answered(said, found, messages):
    """WHAT CAME BACK, OR PLAIN WORDS FOR THE WAYS A RUN ENDS WITHOUT REALLY HAPPENING."""
    if LIMIT in said:
        return RAN_OUT.format(name=found["name"])

    if not said:
        return NOTHING.format(name=found["name"])

    # AN ANSWER WRITTEN WITHOUT TOUCHING A TOOL IS A ROUTINE SAYING WHY IT COULD NOT, AND
    # HANDING THAT BACK AS THOUGH IT HAD RUN IS THE ONE THING THAT MUST NOT HAPPEN.
    if found.get("tools") and not reached(messages):
        return NEVER.format(name=found["name"], said=said)

    return said


def reached(messages):
    """WHETHER ANY TOOL AT ALL WAS ACTUALLY CALLED."""
    return any(getattr(each, "tool_calls", None) for each in messages)


def talker():
    """THE MODEL, REMADE ONLY WHEN A SETTING IT IS BUILT OUT OF HAS MOVED."""
    global kept, made

    if kept is None or made != settings.version("brain"):
        kept, made = brain.create(), settings.version("brain")

    return kept
