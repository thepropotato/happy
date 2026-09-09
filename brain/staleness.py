"""WHETHER AN ANSWER IS THIS MOMENT'S OR AN OLD SITTING'S, AND WHAT THE QUESTION IS ABOUT.

LIFTED OUT OF brain/wrapping.py UNCHANGED. A RESUMED TURN CARRIES NO AGE: THE MORNING'S TOOL
RESULT IS STILL SITTING IN THE THREAD AT THREE IN THE AFTERNOON AND READS AS FRESH, SO WHAT
A QUESTION IS ABOUT IS MATCHED AGAINST WHAT THOSE RESULTS WERE ABOUT, IN A PERSON'S OWN
WORDS, RATHER THAN AGAINST A LIST OF THE SENTENCES THAT HAPPENED TO GO WRONG.

EVERYTHING HERE IS A JUDGEMENT OVER ONE REQUEST OR ONE STRING. THE GUARD THAT ACTS ON IT,
keep_fresh, STAYS IN brain/wrapping.py WITH THE REST OF THE TURN'S RUNNING TOTAL."""

from brain.repeats import CHANGING


def stale_answer(messages, said):
    """WHETHER THIS QUESTION IS ABOUT THE VERY THING A DEAD SITTING'S TOOL WENT AND FOUND.

    THE PHRASE LIST CATCHES THE WORDINGS SOMEBODY THOUGHT OF. THIS CATCHES THE REST BY GOING
    THE OTHER WAY ROUND: NOT "DOES THE QUESTION SOUND LIKE ONE OF OURS" BUT "IS THE ONLY
    THING THAT COULD ANSWER IT A RESULT FROM A SITTING THAT IS OVER". A QUESTION NEEDING NO
    TOOL AT ALL IS UNTOUCHED, HOWEVER OLD THE CONVERSATION BEHIND IT."""
    # AN ERRAND IS NOT A QUESTION. "send jane a message" IS ABOUT MESSAGES AND IS A JOB TO DO,
    # AND TURNING ONE BACK TO GO AND CHECK SOMETHING WOULD BE THE GUARD BREAKING THE ERRAND.
    if instructing(said):
        return False

    return bool(stale_moving(messages) & about(said))


# HOW AN INSTRUCTION OPENS. MATCHED ONLY AT THE START, SO "did anyone send me anything" IS
# STILL THE QUESTION IT IS.
DOING = ("send", "message ", "text ", "tell ", "call ", "write", "reply", "forward",
         "ask ", "remind ", "play ", "open ", "turn ", "make ", "delete", "search",
         "book ", "buy ", "email ", "put ", "add ", "set ", "close ", "download")


def instructing(said):
    """WHETHER THIS IS A JOB TO GO AND DO RATHER THAN A QUESTION TO ANSWER."""
    return said.strip().startswith(DOING)


def stale_moving(messages):
    """WHAT THE MOVING TOOLS OF A DEAD SITTING WENT AND FOUND, AS THE THINGS THEY WERE ABOUT.

    NOTHING RAN THIS TURN — keep_fresh HAS ALREADY ESTABLISHED THAT — SO A TOOL RESULT STILL
    IN THE MESSAGES CAME BACK WITH THE CONVERSATION WHEN HAPPY STARTED, AND resuming STAMPS
    EVERY ONE OF THOSE. A STAMP SURVIVES REWORDING, WHICH IS WHAT THE PHRASE LIST CANNOT DO.

    TAKES THE MESSAGES THEMSELVES, NOT A REQUEST: LANGCHAIN HANDS OVER OBJECTS AND DSPy HANDS
    OVER PLAIN DICTS, AND BOTH LOOPS ASK THIS SAME QUESTION."""
    from brain.resuming import STALE

    mark = STALE.split("{", 1)[0]
    found = set()

    for each in messages or []:
        if kind(each) != "tool" or mark not in (content(each) or ""):
            continue

        found |= subjects(title(each).lower())

    return found


def kind(message):
    """WHAT SORT OF MESSAGE THIS IS, WHICHEVER LOOP HANDED IT OVER."""
    if isinstance(message, dict):
        return message.get("role") or message.get("type") or ""

    return getattr(message, "type", "") or ""


def content(message):
    if isinstance(message, dict):
        return message.get("content") or ""

    return getattr(message, "content", "") or ""


def title(message):
    if isinstance(message, dict):
        return message.get("name") or ""

    return getattr(message, "name", "") or ""


def subjects(name):
    """WHICH MOVING THINGS A TOOL NAME IS ABOUT."""
    found = {each for each in MOVING if each in name}

    return found | ({"screen"} if name in CHANGING else set())


def about(said):
    """WHICH MOVING THINGS A QUESTION IS ABOUT, IN THE SAME WORDS."""
    found = {each for each in MOVING if each in said}

    # THE WORDS A PERSON USES FOR THESE ARE NOT THE WORDS A TOOL IS NAMED WITH.
    for word, means in SAME.items():
        if word in said:
            found.add(means)

    return found


# WHAT A PERSON CALLS THE THING, AGAINST WHAT THE TOOL THAT FINDS IT IS CALLED.
SAME = {
    "chat": "message", "text": "message", "whatsapp": "message", "wrote": "message",
    "hear from": "message", "get hold of": "message", "reach me": "message",
    "inbox": "mail", "gmail": "mail",
    "miss anything": "message", "word from": "message", "heard from": "message",
    "middle of": "screen", "up to": "screen",
    "watching": "screen", "playing": "screen", "show": "screen", "episode": "screen",
    "movie": "screen", "song": "screen", "front of me": "screen", "doing": "screen",
    "calendar": "event", "agenda": "event", "diary": "event",
}


# WHAT A TOOL'S ANSWER IS ABOUT WHEN IT GOES OFF AS SOON AS IT IS WRITTEN DOWN. MATCHED ON
# THE NAME SO A NEWLY CONNECTED SERVICE IS COVERED THE DAY IT ARRIVES, RATHER THAN THE DAY
# SOMEBODY REMEMBERS TO ADD IT HERE.
MOVING = ("unread", "message", "mail", "email", "inbox", "notification", "event", "calendar",
          "schedule", "meeting", "screen", "activity", "window", "open", "play", "weather",
          "battery", "reminder", "status", "latest", "recent")


def moving(name):
    """WHETHER THIS TOOL'S ANSWER HAS A SHELF LIFE."""
    low = name.lower()

    return low in CHANGING or any(each in low for each in MOVING)

