"""WHERE THE TURN CAME FROM, PUT IN WORDS HE CAN READ.

A MESSAGE IS NOT A ROOM. "TELL HER I LOVE HER" MEANS NOTHING UNLESS HE KNOWS
WHOSE CHAT HE IS STOOD IN, AND THE ANSWER IS NOT SOMETHING HE HAS TO GO AND LOOK
UP: THE MESSAGE ARRIVED FROM SOMEWHERE, AND WHO THAT SOMEWHERE IS WITH IS THE
WHOLE OF WHO "HER" IS.

THE OTHER HALF IS WHAT BECOMES OF HIS ANSWER. IT IS NOT READ OUT TO WHOEVER ASKED
— IT IS SENT INTO THAT CHAT, WHERE THE OTHER PERSON READS IT. TOLD THAT, "TELL
HER I LOVE HER" IS ANSWERED BY SAYING IT TO HER, WHICH IS THE WHOLE ERRAND. NOT
TOLD IT, HE ANSWERS "I'VE LET HER KNOW" AND SHE IS THE ONE WHO READS THAT.
"""

from mcps.servers.whatsapp import talking

TAIL = 8  # MESSAGES OF THE CHAT PUT IN FRONT OF HIM. ENOUGH TO FOLLOW A THREAD.

LONGEST = 200  # PER MESSAGE. A PASTED WALL OF TEXT IS NOT CONTEXT.

GROUPS = "@g.us"

whose = None


def about(chat, entry, his):
    """THE FEW LINES THAT SAY WHERE HE IS STANDING, OR None IN HIS OWN GROUP."""
    if his:
        return None

    owner = named()
    with_whom = str(entry.get("chatName") or "").strip() or "this chat"

    if GROUPS in chat:
        where = (
            f"You are answering inside {owner}'s WhatsApp group \"{with_whom}\". What you say "
            f"next is sent into that group from {owner}'s own account and everybody in it reads "
            f"it. {owner} is the one who asked you, and \"her\", \"him\" and \"them\" mean "
            f"whoever is being talked about in there."
        )
        like = "\"tell them the meeting is at 5\" is answered \"The meeting is at 5\""
    else:
        where = (
            f"You are answering inside {owner}'s WhatsApp chat with {with_whom}. Everything you "
            f"say next is already on its way into that chat, sent from {owner}'s own account, so "
            f"{with_whom} is who reads it. {owner} is not in the room to hear you, and \"her\", "
            f"\"him\" and \"them\" mean {with_whom} unless the message names somebody else."
        )
        like = "\"tell her I love her\" is answered \"I love you\""

    # THE STANDING RULE IS NEVER TO READ A MESSAGE OUT AS THE ANSWER, BECAUSE
    # NORMALLY THE ANSWER IS SPOKEN INTO A ROOM AND THE MESSAGE GOES BY TOOL.
    # HERE THEY ARE ONE THING. TOLD ONLY GENTLY, HE STILL REACHES FOR THE TOOL AND
    # IT GOES TWICE: ONCE AS THE MESSAGE, ONCE AS WHAT HE SAID ABOUT SENDING IT.
    # SO THE RULE IS NAMED AND LIFTED, AND THE SHAPE OF THE ANSWER SHOWN TWICE.
    return join(where, (
        f"Your answer is itself the message and it is sent for you, so never hand your answer to "
        f"a message tool as well — that would deliver it twice. Your other tools work as they "
        f"always do, and anything genuinely going somewhere else still goes by tool. The standing "
        f"rule about never reading a message out as your answer is the one thing that does not "
        f"apply here — writing it out is what sends it. Asked to tell them something, answer with "
        f"that thing itself, in {owner}'s own voice and nothing else around it: {like}."
    ), lines(chat, owner, with_whom))


def join(*parts):
    return "\n\n".join(part for part in parts if part)


def lines(chat, owner, with_whom):
    """THE TAIL OF THAT CHAT, OLDEST FIRST, EACH LINE NAMED BY WHO SAID IT."""
    said = []

    for entry in talking.look(chat, TAIL):
        body = " ".join(str(entry.get("body") or "").split())

        if not body:
            continue

        who = owner if entry.get("fromMe") else (str(entry.get("from") or "").strip() or with_whom)
        said.append(f"{who}: {body[:LONGEST]}")

    return "What has been said in there, oldest first:\n" + "\n".join(said) if said else ""


def named():
    """WHOSE ACCOUNT THIS IS, AS WHATSAPP HAS THE NAME. ASKED ONCE PER RUN."""
    global whose

    if whose is None:
        whose = str((talking.asked(talking.client().get_status()) or {}).get("name") or "").strip()

    return whose or "the owner"
