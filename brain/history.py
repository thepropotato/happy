"""THE BACKCHAT BEHIND A TURN: FINISHED TURNS MADE SMALL, AND ONLY SO MANY OF THEM KEPT."""

from langchain_core.messages import ToolMessage

from memory import settings

# HOW MUCH OF A SETTLED TOOL RESULT STAYS. WHAT WAS CALLED AND WITH WHAT IS KEPT WHOLE; THE
# PAGE IT READ IS NOT, BECAUSE THE ANSWER MADE OUT OF IT IS ALREADY THE NEXT MESSAGE.
BRIEF = 240

ELLIPSIS = "..."

# WHAT A CALL IS TOLD WHEN THE RUN THAT ASKED FOR IT STOPPED BEFORE IT CAME BACK.
UNFINISHED = "That call was never finished."


def recent(messages):
    """THE BACKCHAT BEHIND THIS TURN, CUT DOWN, AND THIS TURN WHOLE."""
    began = opened(messages)

    return answered(settled(messages[:began]) + messages[began:])


def settled(messages):
    """THE TURNS ALREADY FINISHED: EACH ONE COMPACTED, AND THE OLDEST DROPPED IN BLOCKS.

    THE BACKEND RE-READS EVERYTHING FROM THE FIRST CHANGED BYTE ON, AT A FEW HUNDRED TOKENS
    A SECOND. COMPACTING ONLY THE TURN JUST FINISHED CHANGES A FEW HUNDRED TOKENS AT THE
    END; DROPPING THE OLDEST TURN WOULD CHANGE EVERYTHING, SO IT IS DONE BY HALVES AND
    RARELY INSTEAD OF BY ONE AND EVERY TURN."""
    turns = kept(split(messages))

    return [compacted(each) for turn in turns for each in turn]


def split(messages):
    """MESSAGES GROUPED INTO TURNS, EACH STARTING WHERE A PERSON SPOKE."""
    turns = []

    for message in messages:
        if getattr(message, "type", "") == "human" or not turns:
            turns.append([])

        turns[-1].append(message)

    return turns


def kept(turns):
    most = max(2, int(settings.get("brain.history") or 2))

    if len(turns) <= most:
        return turns

    return turns[-(most // 2):]


def compacted(message):
    """A TOOL RESULT CUT TO ITS FIRST LINE OR TWO. EVERYTHING ELSE UNTOUCHED."""
    if not isinstance(message, ToolMessage):
        return message

    said = message.content if isinstance(message.content, str) else str(message.content)

    if len(said) <= BRIEF:
        return message

    return message.model_copy(update={"content": said[:BRIEF].rstrip() + ELLIPSIS})


def answered(messages):
    """EVERY TOOL CALL WITH A REPLY BEHIND IT. A RUN THAT STOPPED BETWEEN ASKING FOR A TOOL
    AND HEARING BACK LEAVES ONE WITHOUT, AND A BACKEND REFUSES THE WHOLE CONVERSATION OVER
    IT, NOT JUST THAT TURN BUT EVERY TURN AFTER IT."""
    whole = []

    for index, message in enumerate(messages):
        whole.append(message)

        whole += [
            ToolMessage(content=UNFINISHED, tool_call_id=each)
            for each in unreplied(message, messages[index + 1:])
        ]

    return whole


def unreplied(message, after):
    """THE CALLS THIS MESSAGE ASKED FOR THAT NOTHING AFTER IT ANSWERS."""
    wanted = [each.get("id") for each in getattr(message, "tool_calls", None) or []]

    if not wanted:
        return []

    replied = {getattr(each, "tool_call_id", None) for each in after}

    return [each for each in wanted if each and each not in replied]


def opened(messages):
    """WHERE THE TURN IN PROGRESS STARTS: THE LAST THING A PERSON SAID."""
    for index in range(len(messages) - 1, -1, -1):
        if getattr(messages[index], "type", "") == "human":
            return index

    return 0
