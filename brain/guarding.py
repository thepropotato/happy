"""THE GUARDS THAT SIT BETWEEN THE MODEL AND ITS ANSWER, KEPT NOW THE LOOP IS A DSPy ONE.

EVERY RULE IN brain/wrapping.py WAS LEARNED OFF AN EVENING THAT WENT WRONG: A TURN THAT SAID
IT SENT SOMETHING WHEN NOTHING RAN, ONE THAT ANSWERED ABOUT THE SCREEN OUT OF ITS OWN MEMORY,
ONE THAT GAVE UP WHILE A TOOL WAS STILL HOLDING THE DOOR OPEN. LANGCHAIN HUNG THOSE ON
wrap_model_call. DSPy'S CALLBACKS ONLY WATCH AND CANNOT CHANGE AN ANSWER, SO THE PLACE THAT
CORRESPONDS IS THE MODEL ITSELF: LM.forward IS THE ONE NARROW POINT EVERY ROUND GOES THROUGH.

THE WORD LISTS AND THE JUDGEMENTS ARE NOT WRITTEN TWICE. WHAT IS HERE READS THE PLAIN DICTS
DSPy SENDS INSTEAD OF THE MESSAGE OBJECTS LANGCHAIN PASSED, AND THEN ASKS THE SAME QUESTION
OF THEM BY CALLING STRAIGHT INTO brain.wrapping."""

import time

import dspy

import memory
from brain import mending, sourcing, wrapping
from hands import reasons
from memory import conversation

# THE REPLY GUARDS, IN THE ORDER LANGCHAIN RAN THEM: EACH IS A REASON TO SEND ONE ROUND BACK
# WITH ONE MORE THING SAID TO IT, AND EACH SENDS IT BACK ONCE AND ONLY ONCE.
def disowned(words):
    """A TURN SAYING IT CANNOT DO A THING IT HAS A TOOL FOR. keep_able."""
    found = wrapping.disowning(words) if words.strip() else None

    if not found:
        return None

    name, kind = found

    return wrapping.DISOWNED_TOLD.format(name=name, kind=kind)


def gave_up(words):
    """A TURN APOLOGISING WHILE A TOOL IS STILL HOLDING THE DOOR OPEN. keep_at_it."""
    waiting = [said for said in wrapping.refused.values() if wrapping.CARRY_ON in said]

    if not waiting or not any(each in words for each in wrapping.GIVES_UP):
        return None

    return wrapping.GAVE_UP.format(undone="\n\n".join(waiting))


def handed_back(words):
    """A TURN TELLING THEM WHICH LINK TO CLICK, ABOUT A LIST THEY CANNOT SEE. keep_opening."""
    if not any(each in words for each in wrapping.HANDBACK):
        return None

    return wrapping.HANDED_BACK


def announced(words):
    """A TURN ENDING ON WHAT IT IS ABOUT TO DO, WITH THE DOING LEFT UNDONE. keep_finishing.

    THE JUDGEMENT IS wrapping.announced AND IS NOT WRITTEN TWICE."""
    return wrapping.ANNOUNCED if wrapping.announced(words) else None


def unlooked(words):
    """A TURN ANSWERING ABOUT WHAT IS IN FRONT OF THEM OUT OF ITS OWN MEMORY. keep_looking."""
    if not any(each in words for each in wrapping.CLAIMED):
        return None

    said = (conversation.asking() or "").lower()

    if not any(each in said for each in wrapping.POINTED):
        return None

    return wrapping.UNLOOKED_ALOUD


def unchecked(words):
    """A QUESTION ABOUT SOMETHING THAT MOVES, ANSWERED WITH NOTHING CALLED THIS TURN.

    THE ANSWER TO "any unread messages" IS DIFFERENT AT TEN AND AT THREE, BUT THE MORNING'S
    ANSWER SITS IN THE BACKCHAT IN THE SAME SHAPE A FRESH ONE HAS, AND THE MODEL READ IT AS
    ITS OWN WORK AND SAID IT AGAIN WITHOUT CALLING ANYTHING."""
    if wrapping.ran:
        return None

    said = (conversation.asking() or "").lower()

    if not said or not wrapping.asked_fresh(said):
        return None

    return wrapping.ASKED_TOLD.format(said=said)


def dishonest(words):
    """A REPLY SAYING A THING HAPPENED WHEN NO TOOL THIS TURN DID IT. keep_honest."""
    if not any(each in words for each in wrapping.CLAIMS):
        return None

    if not wrapping.ran:
        return wrapping.NOTHING_RAN

    # SOMETHING RAN, BUT NOT NECESSARILY ANYTHING THAT COULD HAVE DONE WHAT WAS CLAIMED.
    missing = wrapping.unbacked(words, wrapping.ran)

    if missing:
        return wrapping.UNBACKED.format(
            claim=" and ".join(missing), ran=", ".join(dict.fromkeys(wrapping.ran))
        )

    if not wrapping.refused:
        return None

    return wrapping.DENIED.format(undone="\n".join(wrapping.unfinished()))


def unfinished_file(words):
    """A TURN ANSWERING ABOUT A FILE IT ONLY READ THE FIRST CHUNK OF. keep_reading.

    read_file SAYS IN ITS OWN RESULT WHAT TO CALL IT WITH TO READ ON, AND THE MODEL OFTEN
    ANSWERS OUT OF THE FIRST CHUNK ALONE. A SUMMARY MADE FROM THE FRONT OF A DOCUMENT IS NOT
    A SUMMARY OF THE DOCUMENT."""
    if not wrapping.file_was_cut or wrapping.file_cut_resume is None:
        return None

    return wrapping.UNREAD_FILE.format(start=wrapping.file_cut_resume)


def stale(words, messages=None):
    """A QUESTION ABOUT SOMETHING THAT MOVES, ANSWERED OUT OF A DEAD SITTING'S TOOL. keep_fresh.

    unchecked CATCHES THE WORDINGS SOMEBODY THOUGHT OF; THIS CATCHES THE REST BY ASKING WHAT
    THE RESUMED RESULTS WERE ABOUT AGAINST WHAT THIS QUESTION IS ABOUT. A RESUMED TURN
    CARRIES NO AGE: THE MORNING'S ANSWER READS AS FRESH AT THREE IN THE AFTERNOON."""
    if wrapping.ran:
        return None

    said = (conversation.asking() or "").lower()

    if not said or not wrapping.stale_moving(messages):
        return None

    return wrapping.ASKED_TOLD.format(said=said)


# EVERY ONE OF THEM, IN THE ORDER THEY RAN.
REPLY_GUARDS = (disowned, gave_up, handed_back, announced, unlooked, unchecked,
                stale, unfinished_file, dishonest)


class Guarded(dspy.LM):
    """THE MODEL WITH THE GUARDS AROUND IT. forward IS WHERE wrap_model_call WENT."""

    def forward(self, prompt=None, messages=None, **kwargs):
        # ENOUGH TOOLS IN A ROW SAID NO: THE TURN ENDS BEFORE THE MODEL IS ASKED AGAIN, AND
        # ENDS HERE RATHER THAN PART WAY THROUGH A TOOL. keep_going.
        if wrapping.missed >= wrapping.ENOUGH:
            raise wrapping.Stuck(wrapping.NOWHERE)

        answered = self.trying(prompt, messages, kwargs)

        return self.honest(prompt, messages, kwargs, answered)

    def plain(self, prompt, messages, kwargs):
        """THE ROUND ITSELF, WITH WHAT IT COST TAKEN OFF IT. keep_count."""
        answered = super().forward(prompt=prompt, messages=messages, **kwargs)

        spent = costing(answered)

        if spent:
            wrapping.spend = spent
            wrapping.tell(wrapping.SPENT, None, None, dict(spent))

        return answered

    def trying(self, prompt, messages, kwargs):
        """A TOOL CALL THE BACKEND COULD NOT READ IS MENDED, OR NAMED. keep_trying.

        THE MEND IS THE ONE IN brain/mending.py AND IS NOT WRITTEN TWICE."""
        for left in range(wrapping.TRIES - 1, -1, -1):
            try:
                return self.plain(prompt, messages, kwargs)
            except Exception as error:
                said = str(error)

                if not wrapping.unparsed(said) or not left:
                    raise

                wrapping.amiss(said)

                messages = list(messages or []) + [
                    {"role": "user", "content": wrapping.telling(said)}
                ]

    def honest(self, prompt, messages, kwargs, answered):
        """THE REPLY GUARDS, EACH GIVEN ONE GO AT SENDING THE ROUND BACK.

        A ROUND THAT ASKED FOR A TOOL IS ON ITS WAY TO LOOK AND IS NEVER TURNED BACK: THAT IS
        THE VERY BEHAVIOUR THESE EXIST TO GET."""
        words = spoken(answered)

        if not words.strip() or reaching(answered):
            return answered

        for guard in REPLY_GUARDS:
            # ONE OF THEM ASKS WHAT THE RESUMED RESULTS WERE ABOUT, WHICH ONLY THE MESSAGES
            # THEMSELVES CAN SAY. THE REST JUDGE THE WORDS ALONE.
            telling = guard(words, messages) if guard is stale else guard(words)

            if not telling:
                continue

            told = list(messages or []) + [{"role": "user", "content": telling}]

            return self.plain(prompt, told, kwargs)

        return answered


def spoken(answered):
    """WHAT THE MODEL ACTUALLY SAID, OUT OF WHATEVER SHAPE THE BACKEND HANDED BACK."""
    for each in listed(answered):
        if isinstance(each, str):
            return each.lower()

        content = each.get("content") if isinstance(each, dict) else None

        if isinstance(content, str):
            return content.lower()

    return ""


def reaching(answered):
    """WHETHER THIS ROUND ASKED FOR A TOOL RATHER THAN ANSWERING."""
    for each in listed(answered):
        if isinstance(each, dict) and each.get("tool_calls"):
            return True

    return False


def listed(answered):
    """THE PARTS OF AN ANSWER, WHATEVER IT CAME BACK AS."""
    if answered is None:
        return []

    if isinstance(answered, (str, dict)):
        return [answered]

    return list(answered) if isinstance(answered, (list, tuple)) else [answered]


def costing(answered):
    """WHAT ONE ROUND READ AND WROTE, OR None IF THE BACKEND WILL NOT SAY. keep_count.

    DSPy HANDS BACK ITS OWN RESPONSE OBJECT RATHER THAN A LANGCHAIN MESSAGE, SO THE USAGE IS
    READ OFF THAT; THE FIGURES AND THE NAMES THEY GO OUT UNDER ARE THE ONES wrapping USES."""
    usage = getattr(answered, "usage", None) or {}

    if not isinstance(usage, dict):
        usage = getattr(usage, "__dict__", {}) or {}

    read = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
    wrote = usage.get("completion_tokens") or usage.get("output_tokens") or 0

    if not read and not wrote:
        return None

    return {"read": read, "wrote": wrote, "prefill": None}


def named(name, known):
    """THE REAL TOOL A NEARLY-RIGHT NAME MEANS, OR THE NAME ITSELF. keep_named.

    THE JUDGEMENT IS wrapping.nearest AND IS NOT WRITTEN TWICE."""
    fixed = wrapping.nearest(name or "", list(known))

    if fixed and fixed != name:
        wrapping.amiss(f"tool {name} taken as {fixed}")

        return fixed

    return name


def recorded(tool, known):
    """ONE TOOL WITH ITS CALL WRITTEN DOWN AROUND IT. keep_record.

    EVERY CALL GOES ON THE EXCHANGE WITH ITS REASON, ARGUMENTS AND TIME, THE PANEL IS TOLD
    BEFORE AND AFTER, AND A REPEAT OR A CIRCLE IS TURNED BACK WITH THE ANSWER IT ALREADY HAS.
    THE COUNTING OF WHAT SAID NO IS WHAT keep_going READS TO END A STUCK TURN."""
    def run(**kwargs):
        name = named(tool.name, known)
        args, why = reasons.without(dict(kwargs))
        which = f"{name}-{id(kwargs)}"

        # THE SAME TOOL WITH THE SAME ARGUMENTS GIVES THE SAME ANSWER, AND ASKING TWICE IN ONE
        # TURN IS THE SHAPE EVERY STUCK RUN TAKES.
        refusal = (wrapping.repeated(name, args) or wrapping.circling(name, args)
                   or sourcing.checked(name, args))

        if refusal:
            wrapping.remember(name, args, refusal)

            return refusal

        wrapping.ran.append(name)
        wrapping.tell(wrapping.STARTED, name, None, {"id": which, "args": args})

        started = time.perf_counter()

        try:
            result = tool.invoke(kwargs)
        except Exception as error:
            taken = time.perf_counter() - started

            memory.used(name, args, str(error), taken, why, failed=True, spent=wrapping.claim())
            wrapping.tell(wrapping.TOOL, name, taken, {
                "id": which, "why": why, "args": args, "result": str(error),
                "failed": True, "spent": None,
            })
            wrapping.noting(name, str(error), True)
            wrapping.missed += 1

            # A TOOL THAT THREW SAID NO; IT IS NOT THE END OF THE TURN AND THE CALL STILL
            # GETS ITS REPLY.
            return wrapping.BROKEN.format(trouble=str(error))

        taken = time.perf_counter() - started
        said, nope = reasons.went(str(result))

        memory.used(name, args, said, taken, why, failed=bool(nope), spent=wrapping.claim())
        wrapping.tell(wrapping.TOOL, name, taken, {
            "id": which, "why": why, "args": args, "result": said, "failed": bool(nope),
        })
        wrapping.noting(name, said, nope)
        wrapping.remember(name, args, said)

        return said

    return dspy.Tool(run, name=tool.name, desc=tool.description, args=schema(tool))


def schema(tool):
    """WHAT ONE TOOL TAKES, AS THE PROPERTIES OF ITS SCHEMA."""
    wanted = getattr(tool, "args_schema", None)

    if wanted is not None and hasattr(wanted, "model_json_schema"):
        return (wanted.model_json_schema() or {}).get("properties") or {}

    return getattr(tool, "args", None) or {}
