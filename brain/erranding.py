"""THE WHOLE ERRAND AS ONE SIGNATURE: WHAT WAS SAID, WHAT CAME BACK, AND THE TOOLS BETWEEN.

THE SMALL SIGNATURES EACH ASK ONE QUESTION AND TAKE ONE ANSWER. THIS ONE IS THE TURN ITSELF,
WHICH IS NOT ONE QUESTION BUT A LOOP: THE MODEL REACHES FOR A TOOL, READS WHAT IT SAID, AND
REACHES AGAIN UNTIL IT HAS ENOUGH TO ANSWER. DSPy CALLS THAT ReAct, AND IT IS HANDED THE SAME
38 TOOLS THE LANGCHAIN AGENT HOLDS.

WHAT IS NOT HERE IS THE MIDDLEWARE. keep_honest, keep_looking, keep_able AND THE REST SIT
BETWEEN THE MODEL AND ITS ANSWER IN THE LANGCHAIN LOOP, AND EVERY ONE OF THEM IS A RULE
LEARNED OFF A REAL EVENING THAT WENT WRONG. THEY DO NOT COME ACROSS FOR FREE, WHICH IS WHY
THIS IS BUILT BESIDE THE OLD LOOP AND NOT IN PLACE OF IT."""

import dspy

from brain.prompt import system_prompt

# WHAT ONE TOOL CALL TAKES UP IN A TRAJECTORY: THE THOUGHT, THE NAME, THE ARGUMENTS AND WHAT
# CAME BACK.
STEP = 4


class Errand(dspy.Signature):
    """THE STANDING PROMPT IS PUT ON THIS AT BUILD TIME, BECAUSE IT IS READ OFF prompt.md AND
    NOT WRITTEN HERE. WHAT A SIGNATURE CALLS ITS INSTRUCTIONS IS WHAT A PROMPT ALWAYS WAS."""

    said: str = dspy.InputField(desc="what the person said, as it was heard")
    reply: str = dspy.OutputField(desc="one or two spoken sentences, as they would be said out loud")


def tooled(tools):
    """THE LANGCHAIN TOOLS AS DSPy ONES, EACH WITH ITS CALL WRITTEN DOWN AROUND IT.

    dspy.Tool.from_langchain WRAPS EVERY TOOL AS A COROUTINE, AND THE SYNCHRONOUS ReAct NEVER
    AWAITS ONE: EVERY CALL COMES BACK "Execution error" WITH THE COROUTINE THROWN AWAY. SO
    THE CROSSING IS DONE IN guarding.recorded, WHICH ALSO CARRIES keep_record AND keep_named:
    THE EXCHANGE, THE PANEL, THE TIMING, AND A REPEAT TURNED BACK WITH WHAT IT ALREADY HAS."""
    from brain import guarding  # LATE: guarding READS wrapping, WHICH READS memory.

    known = [each.name for each in tools]

    return [guarding.recorded(each, known) for each in tools]


class Errands(dspy.ReAct):
    """THE ERRAND LOOP, WITH THE OLDEST CALLS DROPPED THE WAY THE PREFIX WANTS THEM DROPPED."""

    def truncate_trajectory(self, trajectory):
        """THE OLDEST HALF OF THE CALLS DROPPED AT ONCE, RATHER THAN ONE AT A TIME.

        keep_recent, WHOSE WHOLE POINT IS THE PREFIX: THE BACKEND RE-READS EVERYTHING FROM
        THE FIRST CHANGED BYTE ON, AT A FEW HUNDRED TOKENS A SECOND. DROPPING ONE CALL MOVES
        THAT BYTE AND COSTS THE WHOLE CONTEXT, AND DOING IT AGAIN NEXT ROUND COSTS IT AGAIN.
        DROPPING HALF COSTS THE SAME ONCE AND THEN BUYS MANY ROUNDS OF QUIET."""
        keys = list(trajectory.keys())

        # EVERY CALL IS FOUR KEYS: THE THOUGHT, THE NAME, THE ARGUMENTS AND WHAT CAME BACK.
        calls = len(keys) // STEP

        if calls <= 1:
            return super().truncate_trajectory(trajectory)

        for key in keys[:(calls // 2) * STEP]:
            trajectory.pop(key)

        return trajectory


def built(tools, wording=None, most=None):
    """THE ERRAND LOOP, READY TO BE ASKED.

    THE PROMPT IS PUT ON THE SIGNATURE RATHER THAN PASSED IN, SO WHAT THE MODEL IS TOLD IS
    THE SAME TEXT prompt.md HOLDS AND NOT A REPHRASING OF IT."""
    signature = Errand.with_instructions(wording or system_prompt())

    return Errands(signature, tools=tooled(tools), max_iters=most or 14)
