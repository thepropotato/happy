"""WHAT WRAPS EVERY CALL: WHAT GOES IN, WHAT IS KEPT, AND HOW LONG IT TOOK."""

import collections
import difflib
import json
import re
import time
import uuid

from langchain.agents.middleware import wrap_model_call, wrap_tool_call
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

import memory
from brain import mending
from brain.history import recent
from hands import reasons
from memory import conversation, settings
from sound import earcon

TOOL = "tool"

# THE SAME CALL, SAID BEFORE IT RUNS.
STARTED = "tool.started"

MODEL = "model"

# WHAT ONE ROUND COST, SAID AS SOON AS THE MODEL COMES BACK AND BEFORE ANY TOOL
# IT ASKED FOR HAS RUN.
SPENT = "spent"

# WHAT OLLAMA TIMES ITSELF IN.
NANOSECONDS = 1_000_000_000

# THREE IN A ROW GETTING NOWHERE.
ENOUGH = 3

# HOW THE CALL LIMIT SAYS SO, IN ITS OWN WORDS: "Model call limits exceeded: run
# limit (14/14)". EVERY WORD OF A REPLY IS READ OUT LOUD, AND THAT IS A COUNTER.
LIMIT = "Model call limits exceeded"

NOWHERE = (
    "That is not getting anywhere — three goes in a row came back with nothing. "
    "Tell me a bit more about what you are after and I will try it another way."
)

# HOW THE BACKEND SAYS THE MODEL WROTE SOMETHING IN A TOOL CALL THAT IS NOT JSON.
UNPARSED = ("error parsing tool call", "invalid tool call", "failed to parse tool")

# HOW MANY GOES ONE OF THOSE GETS BEFORE THE ROUND GIVES UP ON IT.
TRIES = 3

# TEMPERATURE IS USUALLY 0, SO AN UNCHANGED REQUEST WOULD COME BACK WORD FOR WORD
# THE SAME. NAMING THE MISTAKE IS WHAT MAKES THE NEXT GO DIFFERENT.
AGAIN = (
    "Your last tool call could not be read: {trouble}. Tool arguments must be "
    "finished JSON values and never expressions — write the whole string out in "
    'full instead of anything like "hello" * 100 or "a" + "b". Make the call again.'
)

# THE SAME, FOR WHEN THE BACKEND QUOTED WHAT THE MODEL WROTE. SHOWING IT ITS OWN OUTPUT IS
# WORTH MORE THAN ANY RULE, AND THE ONE MISTAKE IT KEEPS MAKING IS WORTH NAMING OUTRIGHT.
SHOWN = (
    "Your last tool call could not be read: {trouble}\n\nYou wrote: {raw}\n\nThe arguments "
    "must be one flat JSON object: a single {{ at the start, a single }} at the end, and "
    "nothing but \"key\": value pairs in between. Never open a second {{ where a key should "
    "be. Write every value out in full and finish the object. Make the call again."
)

# WHAT A CALL IS TOLD WHEN THE TOOL BEHIND IT THREW INSTEAD OF ANSWERING.
BROKEN = "That tool did not run: {trouble}"

report = None

# HOW THE FACE IS SHOWN THE RAW DETAIL OF A FAILURE HAPPY WILL ONLY SUMMARISE ALOUD.
shown = None

# AND HOW IT IS TOLD WHAT IS BEING STARTED, IN TIME TO SAY SO ABOVE IT.
noted = None

# HOW MANY TOOLS IN A ROW HAVE SAID NO.
missed = 0

# WHAT THE ROUND JUST FINISHED COST, WAITING FOR THE TOOL IT ASKED FOR TO CLAIM IT.
spend = None

# WHAT SAID NO THIS TURN AND HAS NOT BEEN PUT RIGHT SINCE: {tool name: what it said}. A TOOL
# THAT LATER WORKS TAKES ITS OWN NAME BACK OFF, SO WHAT IS LEFT AT THE END IS ONLY WHAT
# REALLY DID NOT HAPPEN.
refused = {}

# EVERY TOOL THAT HAS RUN THIS TURN, IN ORDER. A TOOL THAT MUST NOT BE THE FIRST THING A
# TURN DOES CAN ASK WHAT CAME BEFORE IT.
ran = []

# WHETHER THE LAST read_file RESULT WAS CUT SHORT AND THE POSITION TO RESUME FROM. CLEARED
# EACH TURN BY fresh(), UPDATED BY keep_record() WHEN A read_file TOOL COMES BACK.
file_was_cut = False
file_cut_resume = None

# HOW MANY CHARACTERS OF THIS TURN'S WORDS A GUARD HAS TAKEN BACK. THE STREAM SHOWS AND
# SPEAKS A ROUND AS THE MODEL TYPES IT, WHICH IS WHAT MAKES HAPPY FEEL QUICK, AND A GUARD
# ONLY SEES THAT ROUND ONCE IT IS FINISHED — SO THE ANSWER IT TURNS BACK IS ALREADY ON THE
# SCREEN. ASKED ABOUT UNREAD MESSAGES, THE PANEL SHOWED "56 unread" OFF THE MORNING'S
# BACKCHAT, THEN THE TOOL, THEN "56 unread" AGAIN: THE FIRST ONE WAS THE GUESS THE GUARD
# EXISTS TO STOP, AND IT WAS RIGHT ONLY BY LUCK. THE STREAM READS THIS AND DROPS THAT MUCH.
withdrawn = 0

# WHETHER A GUARD IN THIS TURN HAS EVER TURNED A ROUND BACK.
corrected = False


def held(said):
    """WHETHER THIS TURN'S WORDS WAIT FOR THE GUARDS BEFORE THEY ARE DRAWN.

    UNDRAWING IS STILL A FLICKER: THE WORDS WERE ON THE SCREEN, AND THAT IS WHAT WAS SEEN.
    THE ONLY WAY NOT TO SHOW A WRONG ANSWER IS NOT TO DRAW IT, AND WHETHER A TURN IS THE KIND
    THAT GETS CORRECTED IS KNOWN FROM THE QUESTION BEFORE THE MODEL HAS SAID A WORD: A
    QUESTION ABOUT SOMETHING THAT MOVES IS ONE keep_fresh WILL HOLD IF NOTHING IS CALLED.

    THESE ARE THE TURNS THAT TYPE, GET CORRECTED AND TYPE AGAIN. THEY LOSE THE WORD-BY-WORD
    DRAW AND GAIN NEVER SHOWING AN ANSWER NOBODY STANDS BEHIND. EVERY OTHER TURN — WHICH IS
    NEARLY ALL OF THEM — DRAWS AS IT ALWAYS DID."""
    return corrected or asked_fresh((said or "").lower())


@wrap_model_call
def keep_thinking(request, handler):
    """A MODEL CALL MAY TAKE A WHILE, SO A SMALL PULSE KEEPS SILENCE FROM READING AS A HANG."""
    earcon.start()

    return handler(request)


class Stuck(Exception):
    """ENOUGH TOOLS IN A ROW SAID NO THAT THE NEXT ONE WOULD TOO."""


def fresh():
    """A NEW TURN. THE STREAK IS ABOUT THIS ERRAND, NOT THE LAST ONE."""
    global missed, spend, file_was_cut, file_cut_resume, withdrawn, corrected

    missed = 0
    spend = None
    file_was_cut = False
    file_cut_resume = None
    withdrawn = 0
    corrected = False
    asked.clear()
    tried.clear()
    refused.clear()
    ran.clear()


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


def watches(handler):
    """BE TOLD HOW LONG EACH PART TOOK."""
    global report

    report = handler


def tell(kind, name, seconds, about=None):
    if report:
        report(kind, name, seconds, about)


def troubles(handler):
    """BE SHOWN WHAT WENT WRONG, IN THE BACKEND'S OWN WORDS."""
    global shown

    shown = handler


def amiss(said):
    if shown:
        shown(said)


def doings(handler):
    """BE TOLD WHAT IS BEING STARTED, FOR PUTTING A LINE OVER THE TOOLS IT IS ABOUT TO USE."""
    global noted

    noted = handler


def doing(said):
    if noted:
        noted(said)


# WHAT A REPLY IS TOLD WHEN IT WOULD HAVE CLAIMED SOMETHING THAT DID NOT HAPPEN.
DENIED = (
    "Stop. These were asked for this turn and did NOT happen:\n{undone}\n\n"
    "The answer you just wrote says one of them worked. It did not. Either do the thing now "
    "with a tool that will actually do it, or say plainly that it did not happen and why. "
    "Never tell them something is done, saved, created, opened or sent unless a tool this "
    "turn came back saying so."
)

# AND THE OTHER WAY A TURN CLAIMS SOMETHING THAT DID NOT HAPPEN: BY DOING NOTHING AT ALL.
# THE SAME WORDS ASKED TWICE PUT THE EARLIER TURN'S OWN CALLS AND THEIR SUCCESSES IN FRONT OF
# THE MODEL, IN THE SHAPE A CALL MADE THIS TURN HAS, AND IT READ THEM AS THIS TURN'S WORK
# ALREADY DONE AND SAID "just sent" WITHOUT REACHING FOR A TOOL. NOTHING WAS SENT.
NOTHING_RAN = (
    "Stop. You have not called a single tool this turn, so nothing has happened yet, and the "
    "answer you just wrote tells them it has. Work above this line is from an earlier turn — "
    "it is not this one, and it does not count for what they just asked. Do it now with the "
    "tool that does it. If they are asking for something you already did, do it again unless "
    "they said not to; if you truly cannot, say plainly that you have not done it."
)

# HOW A REPLY CLAIMS A THING HAPPENED, AND HOW IT OWNS THAT ONE DID NOT. A REPLY THAT OWNS IT
# IS ALLOWED TO ALSO SAY WHAT IT DID MANAGE, SO OWNING IT ALWAYS WINS.
# THE SECOND ROW IS THE SAME CLAIM WITHOUT THE "I": A TURN THAT CALLED NOTHING SAID "GITHUB'S
# OPEN, AND THE PROJECT PAGE IS UP AND READY TO GO" AND WALKED PAST ALL OF THE FIRST ROW,
# BECAUSE EVERY WORD THERE IS FIRST PERSON OR POSSESSIVE AND THIS NAMED THE THING INSTEAD.
CLAIMS = ("i've ", "i have ", "here's ", "here is ", "it's open", "its open", "saved", "created",
          "made ", "opened", "sent ", "written", "wrote ", "done", "all set", "ready for you",
          "'s open", "s open", "is open", " is up", "now up", "is ready", "ready to go",
          "up and running")

# A CLAIM IS ABOUT A KIND OF DOING, AND ONLY SOME TOOLS CAN HAVE DONE IT. WITHOUT THIS THE
# HONESTY CHECK ASKS ONLY WHETHER *A* TOOL RAN, SO A TURN THAT CHECKED WHATSAPP AND THEN SAID
# "the project page is up and ready to view" WAS WAVED THROUGH: SOMETHING HAD RUN, AND IT WAS
# NOT ANYTHING THAT COULD OPEN A PAGE.
BACKED = {
    "open": ("open_url", "open_app", "open_path", "bring_to_front", "already_open",
             "play_pause", "control_app"),
    "send": ("send_", "_send", "send", "draft", "post_", "reply"),
    "write": ("write_", "download", "move_", "copy_", "rename", "trash", "restore", "remember"),
    "play": ("play_pause", "open_url", "control_app"),
}

# HOW A REPLY SAYS EACH OF THOSE HAPPENED.
DOINGS = {
    "open": ("is up", "is open", "'s open", "opened", "now up", "up and ready",
             "ready to view", "ready to explore", "pulled up"),
    "send": ("sent", "message sent"),
    "write": ("saved", "created", "written", "wrote ", "made "),
    "play": ("playing", "is on now", "started"),
}

UNBACKED = (
    "Stop. You said {claim}, and nothing you called this turn could have done that. What ran "
    "was: {ran}.\n\n"
    "A tool that checked one thing has not done another, however alike they sound. Either "
    "call the tool that actually does it now, in this turn, and say what it came back with, "
    "or drop that part of your answer and say only what you really did. Never tell them a "
    "thing happened because you meant to do it."
)


def unbacked(said, ran):
    """WHICH KINDS OF DOING THIS REPLY CLAIMS THAT NOTHING THIS TURN COULD HAVE DONE.

    ran IS A LIST OF NAMES, BUT IS READ AS A PLAIN YES-OR-NO IN PLACES; WITH NO NAMES TO
    WEIGH THERE IS NOTHING TO SAY, AND THE OLDER CHECKS BELOW STILL HAVE THEIR GO."""
    if not isinstance(ran, (list, tuple, set)):
        return []

    found = []

    for kind, words in DOINGS.items():
        if not any(each in said for each in words):
            continue

        if not any(any(tool in name for tool in BACKED[kind]) for name in ran):
            found.append(kind)

    return found


OWNS = ("could not", "couldn't", "cannot", "can't", "not able", "did not", "didn't", "unable",
        "failed", "no luck", "nothing was", "wasn't able", "was not able", "not there",
        "does not exist", "doesn't exist", "already exists")


# A REFUSAL THAT WAS REALLY AN INSTRUCTION MARKS ITSELF WITH THIS, AND A TURN MAY NOT END
# ON AN APOLOGY WHILE ONE OF THEM IS STILL OUTSTANDING.
CARRY_ON = "not a refusal of it"

# AND A CALL THAT RAN AS A DIFFERENT ONE THAN IT ASKED FOR MARKS ITSELF WITH THIS, SO ASKING
# AGAIN AND MEANING IT IS STILL ALLOWED. TURNED IN hands/apps/tools.py CARRIES THE WORDS.
TURNED_BACK = 'call this again with because="show"'

# HOW A REPLY GIVES UP: IT IS SORRY, AND IT IS NOT TELLING THEM ANYTHING ELSE.
GIVES_UP = ("i'm sorry", "im sorry", "i am sorry", "sorry,", "i can't", "i cannot", "i can not",
            "unable to", "not able to", "afraid i")

GAVE_UP = (
    "Stop. That was not a refusal, it was the next step, and it told you what to do:\n\n"
    "{undone}\n\n"
    "You have not done it yet and you have just apologised instead. Do it now, in this turn, "
    "with the tools it named, and then finish the job they actually asked for. Do not say "
    "sorry and do not ask them anything."
)


# WORDS THAT POINT AT SOMETHING IN FRONT OF THEM RATHER THAN NAMING IT. WHAT THEY POINT AT IS
# ONLY KNOWABLE BY LOOKING, AND THE CONVERSATION IS NOT LOOKING — IT IS WHAT WAS TRUE EARLIER.
# THESE LIVE HERE, NOT WITH THE WRITING TOOLS, BECAUSE A SPOKEN ANSWER POINTS JUST AS OFTEN AS
# A DECK DOES AND BOTH HALVES HAVE TO BE HELD TO THE SAME LIST.
POINTED = (
    "the show i", "the show im", "the show i'm", "the video i", "the video im", "the video i'm",
    "im watching", "i'm watching", "i am watching", "this show", "this video", "this movie",
    "this page", "this song", "this article", "on my screen", "in front of me", "right now",
    "currently watching", "playing right now", "this thing", "what im", "what i'm",
    # AND THE SAME POINTING DONE AT A PROPERTY OF THE THING RATHER THAN THE THING. "copy this
    # link" NAMES NO SHOW AND NO PAGE, SO NOTHING ABOVE MATCHED IT, AND THE ADDRESS WENT INTO A
    # FILE OFF A MEET LINK SOMEBODY MENTIONED EARLIER IN THE CONVERSATION. A LINK IS ONLY EVER
    # THE LINK OF SOMETHING, AND WHICH SOMETHING IS A THING YOU LOOK AT.
    "this link", "the link", "this url", "the url", "this address", "the address",
    "its link", "it's link", "the title of this", "this title",
)

# THE TOOLS THAT ACTUALLY GO AND LOOK.
LOOKERS = ("current_activity", "already_open", "screen", "list_open_windows")

# AND THE ONES THAT GO AND FIND OUT ABOUT WHAT THE LOOKING TURNED UP.
READERS = ("read_page", "search_web", "describe_project", "read_file", "open_url",
           "recall_conversation")

# A QUESTION POINTS AT THE SCREEN, AND THE ANSWER CAME OUT OF THE MODEL WITH NOTHING LOOKED UP.
# THE DECK HALF OF THIS WAS GUARDED AND THE SPOKEN HALF WAS NOT, SO "how many episodes does
# this show have" WAS ANSWERED "ten" — OFF THE WEIGHTS, ABOUT A SHOW NAMED IN A TOOL RESULT AN
# HOUR AND A HALF OLD, WITH NO CALL MADE THIS TURN AT ALL.
UNLOOKED_ALOUD = (
    "Stop — you have not looked. They said {said!r}, which points at whatever is in front of "
    "them right now, and no tool this turn has been and found out what that is. What was said "
    "earlier in this conversation is what was true earlier, not what is on their screen now, "
    "and a title you remember is not a thing you know.\n\n"
    "Do it now, in this turn, before you answer them anything:\n"
    "1. current_activity, to see what is actually there.\n"
    "2. search_web or read_page about whatever that turns out to be.\n"
    "3. answer them out of what those two came back with, and nothing else.\n"
    "This is a step of the job, not a refusal of it. Do not apologise and do not stop."
)

# AND WHEN NOBODY ASKED AT ALL. THE ANSWER VOLUNTEERED WHAT IS ON THEIR SCREEN OFF THE BACK
# OF A CONVERSATION, WHICH IS THE SAME GUESS WITHOUT EVEN A QUESTION BEHIND IT.
UNASKED_ALOUD = (
    "Stop — you have not looked. You were about to tell them what they are watching or "
    "listening to, and no tool this turn has been and found out what that is. What was said "
    "earlier in this conversation is what was true earlier, not what is on their screen now, "
    "and a title you remember is not a thing you know.\n\n"
    "Either call current_activity and answer out of what it says, or do not say what is in "
    "front of them at all. They may simply have been talking to you. This is a step of the "
    "job, not a refusal of it."
)

# AND THE SAME QUESTION ONCE THE LOOKING IS DONE: THE TITLE IS KNOWN AND THE ANSWER STILL IS
# NOT. AN EPISODE COUNT, A YEAR, A CAST — NONE OF THOSE ARE ON THE SCREEN, AND ANSWERING THEM
# OFF A WINDOW TITLE IS THE SAME GUESS WEARING A SOURCE.
UNREAD_ALOUD = (
    "You have looked and that is all you have done. You know what it is called; you do not "
    "know the answer to {said!r}, and that is not something a window title says.\n\n"
    "Do it now, in this turn: search_web or read_page about what you saw on the screen, then "
    "answer out of what came back. Whatever you were about to say from memory is the part that "
    "turns out to be about the wrong show. This is a step of the job, not a refusal of it."
)

# A QUESTION ABOUT SOMETHING THAT MOVES ON ITS OWN WHILE HAPPY IS NOT WATCHING: A MAILBOX, A
# CHAT, A SCREEN, A CALENDAR, THE WEATHER, THE TIME. THE ANSWER TO EVERY ONE OF THESE HAS A
# SHELF LIFE OF ABOUT A MINUTE, AND NONE OF THEM IS SOMETHING A MODEL CAN KNOW BY THINKING.
# ASKED AT TEN AND AGAIN AT THREE, THE TEN O'CLOCK ANSWER WAS STILL SITTING IN THE BACKCHAT
# IN THE EXACT SHAPE A FRESH ONE HAS, AND IT WAS READ BACK OUT WITH NOTHING CALLED AT ALL.
ASKED_FRESH = (
    "unread", "new message", "new messages", "any messages", "messaged me", "messages from",
    "notification", "notifications", "any email", "my email", "my emails", "inbox",
    "on my screen", "on screen", "what am i", "what's on", "whats on", "what is on",
    "what's playing", "whats playing", "what is playing", "currently watching",
    "currently playing", "currently open", "what time", "what day", "what's the date",
    "whats the date", "weather", "temperature", "my calendar", "my schedule",
    "my meetings", "what's open", "whats open", "what is open", "how much battery",
)

# AND WHAT A TURN THAT DID LOOK IS SAYING. A QUESTION ABOVE ANSWERED WITHOUT ONE OF THESE
# HAVING RUN THIS TURN IS AN ANSWER OUT OF MEMORY, WHATEVER ELSE THE TURN DID.
ASKED_TOLD = (
    "Stop — nothing was checked. They asked {said!r}, and the answer to that changes while you "
    "are not looking: it is different in an hour and different again tomorrow. No tool has run "
    "this turn, so what you were about to tell them comes from earlier in this conversation, "
    "and earlier is a different day's answer wearing today's words.\n\n"
    "Call the tool that goes and finds out, now, in this turn, and answer out of what it comes "
    "back with. If it says the same thing the old one did, say it — but say it because it was "
    "just checked. This is a step of the job, not a refusal of it. Do not apologise and do not "
    "stop."
)


# ASKING FOR THE SAME THING AGAIN IN ONE WORD. "check" AFTER "are there any unread messages"
# IS THAT QUESTION ASKED A SECOND TIME AND WAS ANSWERED "still no reply from WhatsApp" WITH
# NOTHING CALLED EITHER TIME. THESE ARE ONLY EVER READ AS THE WHOLE OF WHAT WAS SAID, SO
# "check the file" IS NOT ONE OF THEM, AND "do it" AND "continue" ARE DELIBERATELY NOT HERE:
# THEY FOLLOW ERRANDS AS OFTEN AS QUESTIONS.
ASKED_AGAIN = ("check", "check again", "look again", "try again", "check now", "recheck",
               "check it", "have another look", "look now")


def asked_fresh(said):
    """WHETHER THIS QUESTION IS ABOUT SOMETHING THAT MOVES WHILE NOBODY IS LOOKING."""
    if any(each in said for each in ASKED_FRESH):
        return True

    # A ONE-WORD "check" CARRIES ITS SUBJECT FROM THE QUESTION BEFORE IT, WHICH IS WHY IT IS
    # MATCHED WHOLE RATHER THAN ANYWHERE INSIDE A LONGER SENTENCE.
    return said.strip().strip("?.! ") in ASKED_AGAIN


# WHAT LOOKING ITSELF ANSWERS. A WINDOW SAYS WHAT IS OPEN, WHAT IT IS CALLED AND WHERE IT IS,
# SO A QUESTION ASKING ONLY THAT IS FINISHED THE MOMENT current_activity COMES BACK. SENDING
# THOSE OFF TO READ SOMETHING TOO IS NOT CAUTION, IT IS THE WRONG ANSWER: TOLD TO GO AND READ
# AFTER LOOKING, THE TURN ASKED "show me the link of the video im watching" SEARCHED THE WEB
# FOR A VIDEO IT WAS ALREADY LOOKING AT, WHICH IS THE ONE THING THAT ROW EXISTS TO CATCH.
ON_SCREEN = ("link", "url", "address", "what is this", "what's this", "whats this",
             "what am i", "what im", "what i'm", "which video", "which show", "what show",
             "what video", "what song", "what page","screen", "called", "title", "name of", "open",
             "playing", "tab", "window",
             # AND THE WORD FOR THE THING ITSELF. TOLD "the video im watching right now" AFTER
             # NAMING THE WRONG FILE, THE TURN LOOKED, MATCHED NOTHING HERE, WAS SENT OFF TO
             # READ, AND OPENED A DIFFERENT VIDEO — WITH THE RIGHT ADDRESS ALREADY IN HAND.
             "watching", "this video", "this show", "this page", "this song")

# WHAT A TURN SAYS WHEN IT HAS TALKED ITSELF OUT OF A JOB IT CAN DO, AND THE TOOL THAT DOES
# IT. THE MODEL BELIEVES IT CANNOT MAKE AN OFFICE FILE, BECAUSE MOST MODELS CANNOT; SAYING SO
# IN THE PROMPT DID NOT MOVE IT, SO THE ANSWER IS TURNED BACK HERE INSTEAD.
DISOWNED = {
    "write_document": ("powerpoint", "power point", "presentation", "slide deck", "pptx",
                       "word document", "docx", "spreadsheet", "excel", "xlsx"),
}

# HOW IT SAYS IT CANNOT, AS OPPOSED TO SAYING IT DID NOT.
DISCLAIMS = ("can't create", "cannot create", "can not create", "can't make", "cannot make",
             "unable to create", "unable to make", "can't generate", "cannot generate",
             "don't have the ability", "do not have the ability", "not able to create",
             "copy it into", "copy into a presentation", "paste it into")

DISOWNED_TOLD = (
    "That is not true and you have the tool for it. {name} makes a real {kind} on their disk "
    "that opens in the app that owns it, and it is bound to you right now. Do not offer them "
    "text to copy out by hand. Find out what it is about with the tools that look, then call "
    "{name} and actually make the file."
)


def disowning(words):
    """THE TOOL AND THE THING A REPLY HAS JUST SAID IT CANNOT MAKE, OR None."""
    if not any(each in words for each in DISCLAIMS):
        return None

    for name, kinds in DISOWNED.items():
        for kind in kinds:
            if kind in words:
                return name, kind

    return None


@wrap_model_call
def keep_able(request, handler):
    """A TURN MAY NOT SAY IT CANNOT DO A THING IT HAS A TOOL FOR.

    THIS IS NOT THE SAME AS GIVING UP AFTER A REFUSAL: NOTHING REFUSED, NOTHING WAS EVEN
    TRIED. THE MODEL DECLINED THE JOB OUT OF A BELIEF ABOUT ITSELF THAT IS WRONG HERE, AND
    THE ONE PLACE THAT CAN BE CAUGHT IS THE ANSWER ON ITS WAY OUT."""
    answered = handler(request)
    said = getattr(answered, "result", None) or answered

    if isinstance(said, list):
        said = said[-1] if said else None

    if getattr(said, "tool_calls", None):
        return answered

    words = (getattr(said, "text", "") or "").lower()
    found = disowning(words) if words.strip() else None

    if not found:
        return answered

    name, kind = found
    told = request.override(
        messages=list(request.messages) + [HumanMessage(DISOWNED_TOLD.format(name=name, kind=kind))]
    )

    return handler(told)


@wrap_model_call
def keep_at_it(request, handler):
    """A TURN MAY NOT GIVE UP WHILE A TOOL IS STILL HOLDING THE DOOR OPEN FOR IT.

    A GUARD THAT SAYS "GO AND LOOK, THEN CALL ME AGAIN" IS A STEP OF THE ERRAND. THE MODEL AT
    LOW EFFORT READS ANY REFUSAL AS THE END AND ANSWERS "I can't create that presentation",
    WHICH IS HONEST AND STILL LEAVES THE JOB UNDONE. TELLING IT SO IN THE TOOL'S OWN WORDS DID
    NOT WORK; BEING SENT BACK ONCE DOES."""
    answered = handler(request)

    waiting = [said for said in refused.values() if CARRY_ON in said]

    if not waiting or not surrendering(answered):
        return answered

    told = request.override(
        messages=list(request.messages) + [HumanMessage(GAVE_UP.format(undone="\n\n".join(waiting)))]
    )

    return handler(told)


@wrap_model_call
def keep_looking(request, handler):
    """A TURN MAY NOT ANSWER A QUESTION ABOUT WHAT IS IN FRONT OF THEM OUT OF ITS OWN MEMORY.

    THE WRITING TOOLS HAVE HELD THIS LINE FOR A WHILE, AND THEY HOLD IT ONLY FOR THEMSELVES:
    THE CHECK LIVES IN write_document'S ARGUMENTS, SO A TURN THAT ENDS IN A PLAIN SENTENCE
    NEVER TOUCHES IT. ASKED "how many episodes does this show have", A TURN CALLED NOTHING,
    TOOK THE SHOW'S NAME OFF A current_activity RESULT FROM NINETY MINUTES EARLIER, AND SAID
    "ten" OFF THE WEIGHTS. EVERY PART OF THAT WAS WRONG AND NONE OF IT WAS CATCHABLE ANYWHERE
    BUT HERE, WHICH IS THE ONE PLACE A SPOKEN ANSWER PASSES THROUGH BEFORE IT IS SAID.

    IT IS SENT BACK ONCE. WHAT COMES BACK EITHER CALLS THE TOOLS IT WAS TOLD TO OR ANSWERS
    ANYWAY, AND A SECOND TURNING BACK WOULD ONLY SPEND ANOTHER ROUND ON THE SAME REPLY."""
    answered = handler(request)
    said = conversation.asking() or ""

    if not answering(answered):
        return answered

    pointed = any(each in said.lower() for each in POINTED)

    # THE QUESTION POINTS AT THE SCREEN, OR THE ANSWER DOES. "Oh yeah." POINTS AT NOTHING AND
    # MATCHED NOTHING HERE, AND THE REPLY WAS STILL "You're watching House of the Dragon" —
    # TAKEN OFF A current_activity RESULT FROM SEVEN HOURS EARLIER, WITH NO TOOL CALLED. WHAT
    # MAKES THAT A LIE IS THE CLAIM, NOT THE WORDING OF THE QUESTION, SO THE CLAIM IS READ TOO.
    if not pointed and not pointing(answered):
        return answered

    # LOOKING FIRST, THEN READING: THE TWO ARE ASKED FOR IN THE ORDER THEY HAVE TO HAPPEN, SO
    # A TURN THAT HAS LOOKED IS NOT SENT BACK TO LOOK AGAIN.
    if not already(*LOOKERS):
        # THE QUESTION IS QUOTED BACK WHEN THE QUESTION IS WHAT POINTED. WHEN IT WAS THE
        # ANSWER THAT POINTED, QUOTING "Oh yeah." AT THE MODEL EXPLAINS NOTHING.
        return again(request, handler, answered,
                     UNLOOKED_ALOUD.format(said=said) if pointed else UNASKED_ALOUD)

    # NOBODY ASKED ANYTHING, SO THE LOOKING IS THE WHOLE OF IT. NAMING WHAT IS IN FRONT OF THEM
    # IS EXACTLY WHAT current_activity ANSWERS, AND SENDING THAT OFF TO READ SOMETHING TOO SAYS
    # "go and search the web about this show" TO A TURN THAT WAS ONLY EVER SAYING HELLO BACK.
    if not pointed:
        return answered

    # A QUESTION THE SCREEN ITSELF ANSWERS IS DONE NOW. ANYTHING ELSE — A COUNT, A YEAR, A
    # RUNTIME — IS NOT ON THE SCREEN AND HAS TO BE READ UP BEFORE IT IS SAID.
    if not already(*READERS) and not any(each in said.lower() for each in ON_SCREEN):
        return again(request, handler, answered, UNREAD_ALOUD.format(said=said))

    return answered


@wrap_model_call
def keep_fresh(request, handler):
    """A QUESTION ABOUT SOMETHING THAT MOVES MAY NOT BE ANSWERED WITH NOTHING CALLED.

    THE OTHER HALF OF keep_looking, FOR THE THINGS THAT CHANGE WHERE NOBODY IS LOOKING: A
    MAILBOX, A CHAT, A CALENDAR. ASKED "are there any unread messages on whatsapp" AT TEN AND
    AGAIN AT THREE, THE MORNING'S ANSWER SITS IN THE BACKCHAT IN THE EXACT SHAPE A FRESH ONE
    HAS, AND IT WAS READ BACK OUT — TWICE, WITH NOT ONE TOOL CALLED EITHER TIME.

    keep_looking WILL NOT CATCH IT: THAT ONE ASKS WHETHER THE QUESTION POINTS AT THE SCREEN,
    AND A MAILBOX IS NOT THE SCREEN. SENT BACK ONCE, THE SAME AS EVERY OTHER GUARD HERE."""
    answered = handler(request)

    # A ROUND THAT ASKED FOR A TOOL IS ALREADY GOING TO LOOK, WHICH IS THE WHOLE POINT.
    if not answering(answered):
        return answered

    # SOMETHING RAN THIS TURN, SO THE ANSWER HAS A SOURCE THAT IS NOT MEMORY.
    if ran:
        return answered

    said = conversation.asking() or ""

    if not said or not asked_fresh(said.lower()):
        return answered

    return again(request, handler, answered, ASKED_TOLD.format(said=said))


def again(request, handler, answered, telling):
    """THE ROUND RUN AGAIN WITH THE TELLING ON THE END OF IT, OR THE FIRST ANSWER BACK IF THAT
    CAME TO NOTHING.

    A SENT-BACK ROUND USUALLY GOES OFF TO CALL THE TOOL IT WAS TOLD TO, WHICH IS THE POINT. NOW
    AND THEN IT COMES BACK EMPTY, AND HANDING THAT UP THE CHAIN ENDS THE TURN ON THE "I got
    tangled up" FALLBACK — SILENCE, WHICH IS WORSE THAN THE ANSWER IT WAS BEING CORRECTED FOR.
    SO NOTHING IS ONLY EVER TRADED FOR SOMETHING."""
    global withdrawn, corrected

    # WHAT THE ROUND BEING TURNED BACK ALREADY PUT ON THE SCREEN. NOT NAMED taken: THAT IS
    # THE FUNCTION THE STREAM READS THIS BACK WITH, AND A LOCAL OF THAT NAME MAKES EVERY
    # MENTION OF IT IN HERE LOCAL TOO.
    shown = len(wording(answered))

    told = handler(request.override(messages=list(request.messages) + [HumanMessage(telling)]))
    said = getattr(told, "result", None) or told

    if isinstance(said, list):
        said = said[-1] if said else None

    if getattr(said, "tool_calls", None) or (getattr(said, "text", "") or "").strip():
        # THE ANSWER THAT WAS SHOWN IS NOT THE ANSWER ANY MORE, SO THE STREAM UNSAYS IT,
        # AND FROM HERE ON IT HOLDS EACH ROUND RATHER THAN DRAWING ANOTHER ONE TO UNDRAW.
        withdrawn += shown
        corrected = True

        return told

    return answered


def taken():
    """HOW MANY CHARACTERS A GUARD HAS JUST TAKEN BACK, AND ZERO EVERY TIME AFTER.

    READ ONCE BY THE STREAM AND CLEARED, SO ONE WITHDRAWAL IS UNSAID ONCE."""
    global withdrawn

    given, withdrawn = withdrawn, 0

    return given


def wording(answered):
    """THE WORDS IN A ROUND'S ANSWER, WHATEVER SHAPE IT CAME BACK IN.

    NOT text(): THAT NAME IS ALREADY TAKEN IN HERE, BY THE ONE THAT UNWRAPS A TOOL RESULT.
    DEFINING IT TWICE MEANT THE SECOND QUIETLY REPLACED THE FIRST AND EVERY TOOL IN THE
    SUITE STOPPED BEING READ."""
    said = getattr(answered, "result", None) or answered

    if isinstance(said, list):
        said = said[-1] if said else None

    return str(getattr(said, "text", "") or "")


# HOW A REPLY STATES, AS A FACT, WHAT IS IN FRONT OF THEM THIS MOMENT. THESE ARE CLAIMS ABOUT
# THE SCREEN AND NOTHING ELSE: A TURN THAT SAYS ONE OF THEM HAS EITHER JUST LOOKED, OR IS
# READING A TITLE OUT OF A CONVERSATION THAT HAS MOVED ON SINCE.
CLAIMED = ("you're watching", "youre watching", "you are watching",
           "you're listening to", "youre listening to", "you are listening to",
           "you're on", "youre on", "you are on",
           "you're reading", "youre reading", "you are reading",
           "currently watching", "currently playing", "currently open",
           "is playing right now", "is open right now", "on your screen right now")


def pointing(answered):
    """WHETHER THIS REPLY STATES WHAT IS IN FRONT OF THEM RIGHT NOW AS A FACT."""
    said = getattr(answered, "result", None) or answered

    if isinstance(said, list):
        said = said[-1] if said else None

    # str() FIRST: .text IS AN ACCESSOR OBJECT ON THESE MESSAGES, NOT A STRING, AND `in` AGAINST
    # IT SILENTLY MATCHES NOTHING.
    words = str(getattr(said, "text", "") or "").lower()

    return any(each in words for each in CLAIMED)


def answering(answered):
    """WHETHER THIS ROUND IS THE ANSWER ITSELF RATHER THAN A STEP ON THE WAY TO ONE.

    A ROUND THAT ASKED FOR A TOOL IS ABOUT TO GO AND LOOK, WHICH IS THE THING BEING ASKED FOR,
    AND TURNING IT BACK WOULD INTERRUPT THE VERY BEHAVIOUR THIS IS HERE TO GET."""
    said = getattr(answered, "result", None) or answered

    if isinstance(said, list):
        said = said[-1] if said else None

    if getattr(said, "tool_calls", None):
        return False

    return bool((getattr(said, "text", "") or "").strip())


def surrendering(answered):
    """WHETHER THESE WORDS ARE AN APOLOGY FOR NOT DOING IT RATHER THAN AN ANSWER."""
    said = getattr(answered, "result", None) or answered

    if isinstance(said, list):
        said = said[-1] if said else None

    if getattr(said, "tool_calls", None):
        return False

    words = (getattr(said, "text", "") or "").lower()

    return bool(words.strip()) and any(each in words for each in GIVES_UP)


@wrap_model_call
def keep_honest(request, handler):
    """A REPLY MAY NOT SAY A THING HAPPENED WHEN NO TOOL THIS TURN DID IT — BECAUSE THE ONE
    THAT WOULD HAVE SAID NO, OR BECAUSE NONE WAS EVER CALLED.

    THIS IS THE ONE PLACE IT CAN BE CAUGHT FOR EVERY TOOL AT ONCE. THE MODEL HAS ALREADY BEEN
    TOLD, IN THE TOOL'S OWN WORDS, THAT IT FAILED; WHAT THIS ADDS IS THAT IT CANNOT THEN GO ON
    TO SAY OTHERWISE. IT IS SENT BACK ONCE, WHICH IS ENOUGH — IT EITHER DOES THE THING OR SAYS
    IT DID NOT HAPPEN, AND BOTH OF THOSE ARE HONEST ANSWERS."""
    answered = handler(request)

    if not claiming(answered):
        return answered

    # A TURN THAT RAN NOTHING HAS NO REFUSAL TO POINT AT, WHICH IS WHY THIS WAS MISSED: THE
    # CLAIM IS THE WHOLE OF THE EVIDENCE, AND IT IS ENOUGH.
    if not ran:
        told = request.override(messages=list(request.messages) + [HumanMessage(NOTHING_RAN)])

        return handler(told)

    # AND THE HALF-WAY CASE: SOMETHING RAN, BUT NOTHING THAT COULD HAVE DONE WHAT WAS CLAIMED.
    missing = unbacked(claimed(answered), ran)

    if missing:
        told = request.override(messages=list(request.messages) + [HumanMessage(
            UNBACKED.format(claim=" and ".join(missing), ran=", ".join(dict.fromkeys(ran)))
        )])

        return handler(told)

    if not refused:
        return answered

    told = request.override(
        messages=list(request.messages) + [HumanMessage(DENIED.format(undone="\n".join(unfinished())))]
    )

    return handler(told)


def claimed(answered):
    """THE WORDS OF A REPLY, LOWERCASED, FOR THE CHECKS THAT READ THEM."""
    said = getattr(answered, "result", None) or answered

    if isinstance(said, list):
        said = said[-1] if said else None

    return (getattr(said, "text", "") or "").lower()


def claiming(answered):
    """WHETHER THESE WORDS TELL SOMEBODY A THING WAS DONE WITHOUT OWNING THAT IT WAS NOT."""
    said = getattr(answered, "result", None) or answered

    if isinstance(said, list):
        said = said[-1] if said else None

    # A ROUND THAT ASKED FOR MORE TOOLS IS NOT THE ANSWER YET, SO THERE IS NOTHING TO CHECK.
    if getattr(said, "tool_calls", None):
        return False

    words = (getattr(said, "text", "") or "").lower()

    if not words.strip():
        return False

    return any(each in words for each in CLAIMS) and not any(each in words for each in OWNS)


@wrap_model_call
def keep_recent(request, handler):
    """ONLY THE LAST STRETCH OF THE CONVERSATION GOES TO THE MODEL."""
    return handler(request.override(messages=recent(request.messages)))


@wrap_model_call
def keep_trying(request, handler):
    """A TOOL CALL THE BACKEND COULD NOT READ IS MENDED WHERE THERE IS ONLY ONE WAY TO READ
    IT, AND OTHERWISE NAMED AS A MISTAKE. NEITHER IS THE END OF A TURN."""
    for left in range(TRIES - 1, -1, -1):
        try:
            return handler(request)
        except Exception as error:
            said = str(error)

            if not unparsed(said):
                raise

            amiss(said)

            meant = intended(said, request.tools)

            # PUNCTUATION IS NOT WORTH A WHOLE ROUND: A CALL THAT COULD ONLY HAVE MEANT ONE
            # THING IS MADE AS THAT THING.
            if meant:
                name, args = meant
                amiss(f"{name} mended and run as {json.dumps(args)}")

                return AIMessage(
                    content="",
                    tool_calls=[{"name": name, "args": args, "id": minted(), "type": "tool_call"}],
                )

            if not left:
                raise

            # THE MODEL'S BAD ANSWER NEVER MADE IT ONTO THE CONVERSATION, SO THE
            # CORRECTION GOES ON AS THE NEXT THING SAID TO IT.
            request = request.override(
                messages=list(request.messages) + [HumanMessage(telling(said))]
            )


def minted():
    """AN ID FOR A CALL THE BACKEND NEVER GOT AS FAR AS GIVING ONE."""
    return f"mended_{uuid.uuid4().hex[:8]}"


def telling(said):
    """WHAT TO SAY BACK ABOUT AN UNREADABLE CALL: THE MISTAKE IT MADE, IN ITS OWN OUTPUT.

    TEMPERATURE IS 0, SO AN UNCHANGED REQUEST COMES BACK WORD FOR WORD THE SAME. SHOWING THE
    MODEL WHAT IT WROTE IS WHAT MAKES THE NEXT GO DIFFERENT."""
    raw = mending.wrote(said)

    return (SHOWN if raw else AGAIN).format(trouble=said, raw=raw)


def intended(said, tools):
    """THE ONE CALL AN UNREADABLE ONE CAN ONLY HAVE MEANT, AS (name, args), OR None.

    THE BACKEND SAYS WHAT THE MODEL WROTE BUT NOT WHICH TOOL IT WAS FOR, SO THE ARGUMENTS
    HAVE TO NAME IT: WHERE TWO TOOLS WOULD TAKE THEM THERE IS NO WAY TO CHOOSE, AND ASKING
    AGAIN BEATS CALLING THE WRONG ONE."""
    args = mending.mended(mending.wrote(said))

    if args is None:
        return None

    fits = [each.name for each in tools or [] if mending.fitting(args, wanted(each))]

    return (fits[0], args) if len(fits) == 1 else None


def wanted(tool):
    """A TOOL'S JSON SCHEMA, WHATEVER THE BINDING CALLS IT."""
    schema = getattr(tool, "args_schema", None)

    if schema is not None and hasattr(schema, "model_json_schema"):
        return schema.model_json_schema()

    return getattr(tool, "args", None) or {}


def unparsed(said):
    """WHETHER A FAILURE IS THE MODEL WRITING A BAD TOOL CALL, WHICH IS WORTH ANOTHER GO."""
    lowered = said.lower()

    return any(each in lowered for each in UNPARSED)


# HOW CLOSE A MISSPELT TOOL NAME HAS TO BE TO THE REAL ONE TO BE TAKEN AS IT.
CLOSE = 0.75


@wrap_model_call
def keep_named(request, handler):
    """A TOOL NAME THE MODEL GOT NEARLY RIGHT IS PUT RIGHT BEFORE IT IS LOOKED UP. A FAILED
    LOOKUP COSTS A WHOLE ROUND, AND openApp OR open_app_tool MEANS open_app TO ANYBODY."""
    answered = handler(request)
    message = getattr(answered, "result", None) or answered

    if isinstance(message, list):
        message = message[-1] if message else None

    calls = getattr(message, "tool_calls", None) or []
    known = [each.name for each in request.tools or []]

    for call in calls:
        fixed = nearest(call.get("name") or "", known)

        if fixed and fixed != call.get("name"):
            amiss(f"tool {call.get('name')} taken as {fixed}")
            call["name"] = fixed

    return answered


def nearest(name, known):
    """THE REAL TOOL A NAME MEANS, OR None WHEN IT IS RIGHT ALREADY OR NOTHING IS CLOSE."""
    if not known or name in known:
        return None

    plain = name.lower().replace("-", "_").removesuffix("_tool").removeprefix("functions.")
    snake = "".join(f"_{c.lower()}" if c.isupper() else c for c in plain).strip("_")

    for candidate in (plain, snake):
        if candidate in known:
            return candidate

    close = difflib.get_close_matches(snake, known, n=1, cutoff=CLOSE)

    return close[0] if close else None


@wrap_model_call
def keep_count(request, handler):
    """WHAT EACH ROUND COST, COUNTED WHERE THE MODEL ACTUALLY ANSWERS."""
    global spend

    answered = handler(request)
    spend = counted(answered)

    if spend:
        tell(SPENT, None, None, dict(spend))

    return answered


def counted(answered):
    """WHAT ONE ROUND READ AND WROTE, OR None IF THE BACKEND WILL NOT SAY."""
    said = getattr(answered, "result", None) or answered

    if isinstance(said, list):
        said = said[-1] if said else None

    usage = getattr(said, "usage_metadata", None) or {}

    if not usage.get("input_tokens") and not usage.get("output_tokens"):
        return None

    return {"read": usage.get("input_tokens", 0), "wrote": usage.get("output_tokens", 0),
            "prefill": prefill(said)}


def prefill(said):
    """HOW LONG THE BACKEND SPENT RE-READING THE PROMPT, IN SECONDS.

    A PREFIX IT ALREADY HOLDS COSTS ALMOST NOTHING; ONE IT HAS TO READ AGAIN COSTS THE WHOLE
    CONTEXT AT A FEW HUNDRED TOKENS A SECOND. THE GAP BETWEEN THOSE TWO IS MOST OF A SLOW
    TURN, AND NOTHING ELSE ON THE SPENT LINE SHOWS IT."""
    taken = (getattr(said, "response_metadata", None) or {}).get("prompt_eval_duration")

    return None if taken is None else taken / NANOSECONDS


def claim():
    """THE ROUND'S COST, ONCE."""
    global spend

    taken, spend = spend, None

    return taken


@wrap_tool_call
def keep_record(request, handler):
    """EVERY TOOL CALL GOES ON ITS EXCHANGE, WITH ITS REASON, ARGUMENTS AND TIME."""
    earcon.start()
    call = request.tool_call

    # READ, NOT TAKEN: THE CALL ITSELF GOES ON UNTOUCHED.
    args, why = reasons.without(call)
    name = call.get("name")

    # THE ID TIES THE STARTED AND FINISHED REPORTS TO THE ONE ROW.
    which = call.get("id") or f"{name}-{id(call)}"

    # THE SAME TOOL WITH THE SAME ARGUMENTS GIVES THE SAME ANSWER, AND ASKING TWICE IN ONE TURN
    # IS THE SHAPE EVERY STUCK RUN TAKES. THE ANSWER IT ALREADY HAS IS POINTED AT INSTEAD.
    # AND THE SAME QUESTION IN NEW WORDS, WHICH IS THE SHAPE THE OTHER HALF OF THEM TAKE: A
    # TURN ONCE PUT THE SAME SEARCH THROUGH FOURTEEN REWORDINGS AND THEN GAVE UP ANYWAY.
    refusal = repeated(name, args) or circling(name, args)

    if refusal is not None:
        global missed

        missed += 1
        memory.used(name, args, refusal, 0.0, why, failed=True, spent=claim())
        tell(TOOL, name, 0.0, {"id": which, "why": why, "args": args, "result": refusal,
                               "failed": True, "spent": None})

        return ToolMessage(content=refusal, name=name, tool_call_id=call.get("id") or "", status="error")

    # THE ROUND THAT ASKED FOR THIS CALL, AND WHAT READING THE WHOLE PROMPT AGAIN
    # TO ASK FOR IT COST. TAKEN ON THE WAY IN SO THE FIRST TOOL OF A ROUND GETS IT.
    cost = claim()

    ran.append(name)

    tell(STARTED, name, None, {"id": which, "args": args})

    started = time.perf_counter()

    try:
        result = handler(request)
    except Exception as error:
        taken = time.perf_counter() - started
        gone = {"id": which, "why": why, "args": args, "result": str(error),
                "failed": True, "spent": cost}

        memory.used(name, args, str(error), taken, why, failed=True, spent=cost)
        tell(TOOL, name, taken, gone)

        noting(name, str(error), True)
        missed += 1

        # A TOOL THAT THREW IS A TOOL THAT SAID NO, NOT THE END OF THE TURN: THE CALL
        # STILL GETS ITS REPLY, BECAUSE ONE LEFT UNANSWERED BREAKS EVERY TURN AFTER IT.
        return crashed(call, name, str(error))

    taken = time.perf_counter() - started

    why = why or reason(request)

    # THE MARK COMES OFF HERE AND NOWHERE ELSE, SO THE MODEL READS THE SENTENCE
    # THE TOOL MEANT TO SAY AND NEVER THE BOOKKEEPING IN FRONT OF IT.
    said, nope = reasons.went(text(result))

    # A GUARD THAT TURNED A CALL BACK AND TOLD IT WHAT TO DO NEXT IS NOT A TOOL THAT FAILED.
    # COUNTING THOSE TOWARDS "ENOUGH SAID NO, STOP THE TURN" WOULD END A TURN THAT IS BEING
    # CORRECTED THREE TIMES ON ITS WAY TO GETTING THE JOB RIGHT, WHICH IS THE OPPOSITE OF WHAT
    # THEY ARE FOR.
    missed = 0 if (not nope or CARRY_ON in said) else missed + 1
    noting(name, said, nope)
    remember(name, args, said)

    # TRACK WHETHER read_file LEFT TEXT UNREAD, SO THE MODEL CANNOT ANSWER WITHOUT GETTING IT.
    if name == "read_file":
        check_file_cut(said)

    memory.used(name, args, said, taken, why, failed=nope, spent=cost)

    tell(
        TOOL,
        name,
        taken,
        {"id": which, "why": why, "args": args, "result": memory.brief(said),
         "failed": nope, "spent": cost},
    )

    return plainly(result, said, nope)


def noting(name, said, nope):
    """WHAT THIS TOOL JUST DID, KEPT ONLY WHILE IT IS STILL UNDONE.

    A TOOL THAT SAYS NO AND IS THEN MADE TO WORK HAS NOT FAILED THE TURN, SO ITS NAME COMES
    STRAIGHT BACK OFF. WHAT IS LEFT WHEN THE TURN ENDS IS THE THING THAT NEVER HAPPENED."""
    if nope:
        refused[name] = said
    else:
        refused.pop(name, None)


def already(*names):
    """WHETHER ANY OF THESE HAS ALREADY RUN THIS TURN."""
    return any(name in ran for name in names)


def unfinished():
    """WHAT WAS ASKED FOR THIS TURN AND DID NOT HAPPEN, AS ONE LINE EACH, NEWEST LAST."""
    return [f"{name}: {said}" for name, said in refused.items()]


@wrap_model_call
def keep_going(request, handler):
    """ENOUGH TOOLS IN A ROW SAID NO, SO THE TURN ENDS BEFORE THE MODEL IS ASKED FOR ANOTHER
    ONE. STOPPING HERE AND NOT PART WAY THROUGH A TOOL IS WHAT LEAVES THE CALL ALREADY MADE
    WITH THE REPLY THE CONVERSATION NEEDS IT TO HAVE."""
    if missed >= ENOUGH:
        raise Stuck(NOWHERE)

    return handler(request)


def crashed(call, name, trouble):
    """THE REPLY THAT STANDS IN FOR A TOOL THAT THREW."""
    return ToolMessage(
        content=BROKEN.format(trouble=trouble),
        name=name,
        tool_call_id=call.get("id") or "",
        status="error",
    )


def plainly(result, said, nope):
    """THE ANSWER WITH THE MARK OFF IT, AND THE ORDINARY status FIELD ON INSTEAD."""
    if not hasattr(result, "model_copy"):
        return said

    changed = {"content": said}

    if nope:
        changed["status"] = "error"

    return result.model_copy(update=changed)


def reason(request):
    """WHY THIS CALL, IN THE MODEL'S OWN WORDS BEFORE IT REACHED FOR THE TOOL."""
    wanted = request.tool_call.get("id")

    for message in reversed(request.state.get("messages", [])):
        if any(each.get("id") == wanted for each in getattr(message, "tool_calls", None) or []):
            return (message.text or "").strip() or None

    return None


def text(result):
    """WHAT A TOOL ACTUALLY SAID, OUT OF WHATEVER WRAPPER IT CAME BACK IN."""
    return getattr(result, "content", result)


def check_file_cut(said):
    """WHETHER THIS read_file RESULT WAS CUT SHORT AND WHAT THE NEXT start= IS."""
    global file_was_cut, file_cut_resume

    # THE CUT MARKER SAYS "[...cut. Call this again with start={next} to read on..."
    # SO IF SAID ENDS WITH IT, EXTRACT THAT next VALUE.
    if "[...cut" not in said or "start=" not in said:
        file_was_cut = False
        file_cut_resume = None
        return

    # EXTRACT THE start= VALUE FROM THE CUT MARKER.
    match = re.search(r"start=(\d+)", said)

    if match:
        file_was_cut = True
        file_cut_resume = int(match.group(1))
    else:
        file_was_cut = False
        file_cut_resume = None


UNREAD_FILE = (
    "That file was cut short. You read only part of it. Call read_file again with the exact "
    "start={start} it named, and keep reading until nothing is cut, before you answer or "
    "summarise — a summary made from only the first chunk is not a summary of the whole file."
)


@wrap_model_call
def keep_reading(request, handler):
    """A TURN MAY NOT ANSWER ABOUT A FILE WITHOUT READING ALL OF IT.

    read_file RETURNS TEXT IN CHUNKS FOR LONG FILES AND SAYS IN THE RETURNED TEXT ITSELF
    EXACTLY WHAT TO CALL IT WITH TO GET THE NEXT CHUNK. THE MODEL OFTEN READS ONE CHUNK
    AND ANSWERS OUT OF THAT ALONE, IGNORING THE INSTRUCTION. STOPPING HERE CATCHES THAT:
    IF THE LAST read_file WAS CUT SHORT AND THE MODEL'S ANSWER DID NOT CALL IT AGAIN,
    THE ANSWER IS SENT BACK WITH AN INSTRUCTION TO FINISH READING FIRST.

    IT IS SENT BACK ONCE. WHAT COMES BACK EITHER CALLS read_file OR ANSWERS ANYWAY, AND A
    SECOND TURNING BACK WOULD ONLY SPEND ANOTHER ROUND ON THE SAME REPLY."""
    answered = handler(request)

    # ONLY CHECK FINAL ANSWERS, NOT ROUNDS ASKING FOR ANOTHER TOOL.
    if not answering(answered):
        return answered

    # IF NO FILE WAS CUT, OR IF IT WAS BUT WAS ALREADY FOLLOWED UP, NOTHING TO CORRECT.
    if not file_was_cut or file_cut_resume is None:
        return answered

    # IF THE ANSWER ASKED FOR ANOTHER TOOL, LET IT GO — THE TOOL MIGHT BE read_file.
    # A SECOND CHECK WOULD ONLY INTERRUPT THE CORRECTION.
    return again(request, handler, answered,
                 UNREAD_FILE.format(start=file_cut_resume))