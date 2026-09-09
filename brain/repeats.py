"""THE SAME QUESTION ASKED TWICE, AND THE SAME QUESTION ASKED IN NEW WORDS.

LIFTED OUT OF brain/wrapping.py UNCHANGED, WITH THE TWO DICTS IT KEEPS. EVERY STUCK RUN
TAKES ONE OF THESE TWO SHAPES: THE IDENTICAL CALL AGAIN, WHICH GETS POINTED AT THE ANSWER IT
ALREADY HAS, OR THE SAME SEARCH REWORDED UNTIL THE TURN GIVES UP ANYWAY — ONE TURN PUT ONE
SEARCH THROUGH FOURTEEN REWORDINGS.

asked AND tried LIVE HERE RATHER THAN WITH THE REST OF THE TURN'S RUNNING TOTAL BECAUSE
NOTHING ELSE READS THEM: THEY ARE THIS JUDGEMENT'S OWN MEMORY OF THE TURN. fresh() IN
brain/wrapping.py CLEARS THEM THROUGH forget()."""

import collections
import difflib
import json
import re



# EVERY CALL MADE THIS TURN, BY TOOL AND ARGUMENTS, WITH WHAT IT GOT BACK.
asked = {}

# THE TOOLS THAT GO AND LOOK SOMETHING UP, WHERE ASKING AGAIN IN OTHER WORDS IS THE THING A
# MODEL DOES INSTEAD OF ADMITTING IT CANNOT FIND IT.
SEARCHING = {"search_web", "read_page", "find_files"}

# WHAT EACH OF THOSE HAS BEEN ASKED THIS TURN, AS THE GIST RATHER THAN THE WORDING.
tried = collections.defaultdict(list)

REPEATED = (
    "You already called this with exactly these arguments this turn, and the answer is above. "
    "Use it, or change the arguments or the tool."
)

# THE SAME CALL AGAIN AFTER THE LAST ONE WAS TURNED BACK WITH INSTRUCTIONS. "THE ANSWER IS
# ABOVE, USE IT" IS THE WRONG THING TO SAY HERE — THERE IS NO ANSWER ABOVE, THERE IS A
# REFUSAL, AND A TURN TOLD TO USE IT WENT ON TO ANNOUNCE A DECK THAT HAD NEVER BEEN WRITTEN.
# SO THE REFUSAL IS SAID AGAIN, WHOLE, RATHER THAN POINTED AT.
UNCHANGED = (
    "Nothing was written, and sending the very same arguments a second time will not write it "
    "either — they are the ones that were turned back. This is what you were told, and it has "
    "not been done yet:\n\n{undone}\n\n"
    "Do that now, and then call this again with what came back in it. Nothing has been created "
    "or saved, so do not tell them it has."
)

# A TOOL THAT READS A CHANGING THING MAY HONESTLY BE ASKED TWICE: THE SCREEN MOVES, A BUILD
# FINISHES. EVERYTHING ELSE ANSWERS THE SAME WAY TO THE SAME QUESTION WITHIN ONE TURN.
CHANGING = {"current_activity", "screen", "list_open_windows",
            "already_open", "build", "play_pause", "list_controls", "file_in_front",
            "reminder", "system_control"}


def signature(name, args):
    return name, json.dumps(args, sort_keys=True, default=str)


UNMOVED = (
    "You have looked at this twice this turn and it has not changed, so looking again will not "
    "either. Use what it said, or ask a different tool."
)


def repeated(name, args):
    """WHY THIS EXACT CALL SHOULD NOT RUN AGAIN THIS TURN, OR None. A TOOL THAT READS SOMETHING
    THAT MOVES MAY BE ASKED TWICE, BUT TWICE THE SAME ANSWER MEANS IT IS NOT MOVING."""
    got = asked.get(signature(name, args)) or []

    if not got:
        return None

    if name not in CHANGING:
        # A CALL THAT WAS TURNED INTO A DIFFERENT ONE WAS NOT ANSWERED, AND "the answer is
        # above, use it" IS A LIE ABOUT IT. open_url("1", "show") CAME BACK AS A PAGE READ
        # RATHER THAN OPENED; THE ONE MOVE LEFT WAS TO ASK AGAIN AND MEAN IT, AND THIS SHUT
        # THAT DOOR AND SPENT THE TURN'S LAST GO ON A REFUSAL.
        if any(TURNED_BACK in each for each in got):
            return None

        # A REFUSAL THAT WAS REALLY AN INSTRUCTION IS REPEATED IN FULL, BECAUSE POINTING BACK
        # AT IT IS WHAT LET A TURN READ "use it" AS LEAVE TO CARRY ON AND CLAIM IT WAS DONE.
        return UNCHANGED.format(undone=got[-1]) if CARRY_ON in got[-1] else REPEATED

    return UNMOVED if len(got) >= 2 and got[-1] == got[-2] else None


# HOW MANY TIMES ONE TOOL MAY BE ASKED THE SAME QUESTION IN DIFFERENT WORDS BEFORE IT IS
# CLEAR THE WORDING IS NOT THE PROBLEM. THREE IS ENOUGH TO TRY A REPHRASE AND A NARROWING.
ENOUGH_TRIES = 3

CIRCLING = (
    "You have asked {name} {count} times this turn and it keeps coming back with the same "
    "thing. Rewording the question is not going to change the answer — what is being looked "
    "for is not there. Use the best of what you already have and answer them now, or say "
    "plainly that it could not be found. Do not search again."
)

# THE LITTLE WORDS THAT MAKE TWO SEARCHES LOOK DIFFERENT WITHOUT ASKING ANYTHING DIFFERENT.
NOISE = {"the", "a", "an", "of", "in", "on", "for", "to", "and", "latest", "new", "newest",
         "recent", "video", "videos", "channel", "id", "list", "page", "official", "full"}


def gist(args):
    """WHAT A CALL IS REALLY ASKING, WITH THE WORDING TAKEN OFF. "Barbell latest video" AND
    "Barbell newest video 2026" ARE ONE QUESTION ASKED TWICE, AND COUNTING THEM AS TWO IS HOW
    A TURN GOT TO FOURTEEN SEARCHES."""
    words = " ".join(str(each) for each in args.values()).lower()
    kept = {each for each in re.findall(r"[a-z0-9]+", words) if each not in NOISE and not each.isdigit()}

    return frozenset(kept)


# TWO QUESTIONS SHARING THIS MUCH OF THEIR MEANING ARE THE SAME QUESTION. AN EXACT MATCH WAS
# NO USE: ONE EXTRA WORD MADE "Romanchakam Barbell review" AND "Romanchakam Barbell review
# youtube" COUNT AS TWO, AND A TURN GOT NINE GOES OUT OF THAT.
MOSTLY_SAME = 0.7


def alike(one, other):
    """WHETHER TWO GISTS ARE ASKING THE SAME THING, ALLOWING A WORD EITHER WAY."""
    if not one or not other:
        return one == other

    return len(one & other) / max(len(one), len(other)) >= MOSTLY_SAME


def circling(name, args):
    """WHY THIS TOOL SHOULD NOT BE ASKED THE SAME THING AGAIN, OR None."""
    if name not in SEARCHING:
        return None

    asking = gist(args)
    same = [each for each in tried[name] if alike(each, asking)]

    return CIRCLING.format(name=name, count=len(same) + 1) if len(same) >= ENOUGH_TRIES else None


def remember(name, args, said):
    asked.setdefault(signature(name, args), []).append(said)

    if name in SEARCHING:
        tried[name].append(gist(args))


def learned():
    """EVERYTHING EVERY TOOL HANDED BACK THIS TURN, AS ONE BLOCK OF TEXT.

    THIS IS THE WHOLE OF WHAT HAPPY HAS ACTUALLY BEEN TOLD SINCE THE PERSON SPOKE. ANYTHING
    IN AN ANSWER OR A FILE THAT IS NOT SOMEWHERE IN HERE CAME OUT OF THE MODEL RATHER THAN
    OUT OF THE WORLD."""
    return "\n".join(said for got in asked.values() for said in got)



def forget():
    """A NEW TURN ASKS ITS OWN QUESTIONS. CALLED BY fresh() IN brain/wrapping.py."""
    asked.clear()
    tried.clear()
