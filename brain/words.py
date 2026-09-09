"""THE WORDS A GUARD JUDGES BY: WHAT A REPLY CLAIMS, WHAT IT DISOWNS, WHAT IT PUTS OFF.

LIFTED OUT OF brain/wrapping.py WHOLE AND UNCHANGED. NOTHING HERE TOUCHES WHAT THE TURN HAS
DONE — EVERY NAME IS A LIST OF WORDINGS OR A JUDGEMENT OVER ONE STRING — WHICH IS WHY IT
COULD MOVE AT ALL, AND WHY IT IS WORTH READING ON ITS OWN: THIS IS THE VOCABULARY, AND
brain/wrapping.py IS THE MACHINERY THAT ACTS ON IT.

EVERY LINE OF IT WAS LEARNED OFF A TURN THAT WENT WRONG, SO THE COMMENTS NAME THE EVENING."""

import re

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


# A TURN THAT ENDS ON ONE OF THESE HAS SAID WHAT IT IS ABOUT TO DO INSTEAD OF DOING IT. THEY
# ARE ONLY EVER WRONG AT THE END OF A TURN: MID-JOB THE SAME WORDS ARE FINE, AND THE ROUND
# THAT WRITES THEM IS ON ITS WAY TO A TOOL, WHICH IS WHY THIS IS CHECKED ONLY ON A ROUND THAT
# CALLED NOTHING.
ANNOUNCING = ("let me ", "i'll ", "i will ", "i am going to", "i'm going to", "going to ",
              "now i ", "next i", "one moment", "just a moment", "hold on", "give me a sec",
              "let's ", "lets ", "i can pull", "i can open", "shall i", "want me to")

# THE OPPOSITE: WORDS THAT REPORT A FINISHED THING.
FINISHED = ("i've ", "i have ", "opened", "open now", "is up", "it's up", "its up", "playing",
            "sent", "saved", "created", "made ", "written", "wrote ", "done", "here is",
            "here's", "found", "there are", "there is", "it says", "shows")

# WHAT A COURTESY ENDS ON. "I OPENED IT, LET ME KNOW IF YOU WANT MORE" ANNOUNCES NOTHING: THE
# NEXT MOVE IS THEIRS AND THE JOB IS DONE. "LET ME PULL IT UP" IS THE OPPOSITE, SO THE TWO
# ARE TOLD APART BY WHO ACTS NEXT.
COURTESIES = ("let me know", "let me know if", "tell me if", "say the word", "just say")

# TELLING THEM TO GO AND CLICK SOMETHING IS THE JOB HANDED BACK. THEY CANNOT SEE THE RESULTS
# AT ALL — THE LIST IS SOMETHING ONLY THE MODEL WAS SHOWN — SO "click the first link" NAMES A
# THING THAT IS NOT IN FRONT OF THEM, AND THE PROMPT HAS FORBIDDEN IT ALL ALONG WITH NOTHING
# TO ENFORCE IT.
HANDBACK = ("click the first", "click the second", "click the third", "click on the first",
            "click on the second", "click the link", "click that link", "click this link",
            "click on it", "click it", "the first link", "the second link", "first result",
            "second result", "you can click", "just click", "click through", "tap the first",
            "open the first link", "select the first")

HANDED_BACK = (
    "Stop. They cannot see any search results — the numbered list was shown to you and to "
    "nobody else — so telling them which link to click names something that is not in front "
    "of them, and leaves the job with them.\n\n"
    "Open it yourself now: call open_url with the number of the result you mean and "
    'because="show". Then say what is up, from what the tool came back with. This is a step '
    "of the job, not a refusal of it. Do not apologise and do not stop."
)

ANNOUNCED = (
    "Stop. You just said what you were about to do and then stopped without doing it, which "
    "leaves them waiting for something that is never coming. Saying it is not doing it.\n\n"
    "Do that very thing now, in this turn, with the tools for it, and keep going until the "
    "job they asked for is actually finished. Then say what happened, in the past tense, "
    "from what the tools told you. Never end a turn on what you are about to do."
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

    # AND THE SAME QUESTIONS AS A PERSON ACTUALLY ASKS THEM. THE LIST ABOVE WAS WRITTEN OFF
    # THE WORDINGS THAT HAPPENED TO GO WRONG, SO "did anyone message me" AND "what show is
    # this" WALKED PAST IT AND WERE ANSWERED OUT OF A SESSION FIVE HOURS OLD. THE PROMPT
    # ITSELF NAMES "did anyone message me" AS A THING TO GO AND CHECK, AND THE GUARD DID NOT
    # KNOW THE PHRASE.
    "message me", "messaged", "messaging me", "texted", "any texts", "any text",
    "anything new", "anyone message", "anybody message", "who messaged",
    "who's messaging", "whos messaging", "my messages", "read my message",
    "any mail", "got any mail", "get any mail", "my mail",
    "check whatsapp", "check my",
    "the screen", "my screen", "what show", "which show", "what episode",
    "which episode", "how far in", "still playing", "still watching",
    "still on", "what movie", "which movie", "what song", "which song",
    "am i watching", "am i playing", "am i on",
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


