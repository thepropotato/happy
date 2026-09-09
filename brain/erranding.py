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


class Errand(dspy.Signature):
    """THE STANDING PROMPT IS PUT ON THIS AT BUILD TIME, BECAUSE IT IS READ OFF prompt.md AND
    NOT WRITTEN HERE. WHAT A SIGNATURE CALLS ITS INSTRUCTIONS IS WHAT A PROMPT ALWAYS WAS."""

    said: str = dspy.InputField(desc="what the person said, as it was heard")
    reply: str = dspy.OutputField(desc="one or two spoken sentences, as they would be said out loud")


def tooled(tools):
    """THE LANGCHAIN TOOLS AS DSPy ONES. ALL 38 CROSS OVER WITHOUT A LOSS."""
    return [dspy.Tool.from_langchain(each) for each in tools]


def built(tools, wording=None, most=None):
    """THE ERRAND LOOP, READY TO BE ASKED.

    THE PROMPT IS PUT ON THE SIGNATURE RATHER THAN PASSED IN, SO WHAT THE MODEL IS TOLD IS
    THE SAME TEXT prompt.md HOLDS AND NOT A REPHRASING OF IT."""
    signature = Errand.with_instructions(wording or system_prompt())

    return dspy.ReAct(signature, tools=tooled(tools), max_iters=most or 14)
