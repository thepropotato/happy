"""THE TOOLS THAT PUT WORDS ON THE DISK, AND THE ONE THAT READS A WHOLE PROJECT FIRST."""

import re
from pathlib import Path
from typing import Literal

from langchain_core.tools import tool

from brain import wrapping
from hands import reasons
from hands.files import briefing
from hands.files.finding import locate
from hands.files.writers import ALSO_CALLED, writer
from memory import conversation

# EVERY WORD THE TOOL WILL ANSWER TO, SO A MODEL WRITING "presentation" IS UNDERSTOOD
# RATHER THAN BOUNCED OFF THE SCHEMA AND MADE TO GUESS AGAIN.
KINDS = Literal["slides", "document", "sheet", "presentation", "powerpoint", "deck",
                "doc", "word", "report", "spreadsheet", "excel", "table"]

# A NAME ALREADY TAKEN IS NOT THE END OF THE ERRAND, IT IS THE MIDDLE OF ONE. WHAT IS
# ALREADY THERE COMES BACK WITH THE REFUSAL, SO THE NEXT STEP CAN BE DECIDED RATHER THAN
# ASKED ABOUT: NOTHING WORTH KEEPING IS REPLACED IN PLACE, AND ANYTHING ELSE GOES BESIDE IT.
EXISTS = (
    "{path} already exists, so nothing was written yet. This is what is in it now:\n\n"
    "{inside}\n\n"
    "Decide and finish it this turn, without asking them. If that is a draft, a placeholder "
    "or an older go at the very thing you were about to write, replace it: trash it with "
    "move_to_trash and write it again. If it is theirs and worth keeping, leave it alone and "
    "write yours beside it under a name that says what it is."
)

# HOW MUCH OF WHAT IS ALREADY THERE IS WORTH READING BACK. ENOUGH TO TELL A PLACEHOLDER FROM
# SOMEBODY'S WORK, AND NOT SO MUCH THAT THE ANSWER IS THE FILE.
GLANCE = 600

EMPTY = "(nothing at all — it is an empty file)"

UNREADABLE = "(not text, so it cannot be read here — it is a {kind} file)"

NOWHERE = "The folder {folder} does not exist, so there is nowhere to put {name}."

# WRITING PLAIN TEXT UNDER ONE OF THESE MAKES A FILE THAT WILL NOT OPEN, AND EDITING ONE AS
# TEXT CANNOT WORK EITHER: THEY ARE ZIPPED XML, NOT WORDS. IT HAPPENED, AND WHAT LANDED ON
# THE DESKTOP WAS A TEXT FILE WEARING A .pptx NAME THAT NO APP WOULD OPEN.
SEALED = {".pptx": "slides", ".docx": "document", ".xlsx": "sheet"}

NOT_TEXT = (
    "{name} is a {kind} file, which is zipped XML rather than words, so this cannot {doing} "
    "it — doing so makes a file that will not open. Use write_document with kind \"{sort}\" to "
    "make one of these, and to change one, make it again with the content you want."
)

MISSING = (
    "The text to replace is not in {name}, so nothing was changed. Read the file and give the "
    "exact words as they appear."
)

SEVERAL = (
    "Those words appear {count} times in {name}, so nothing was changed. Give a longer stretch "
    "that appears only once."
)

# WORDS THAT POINT AT SOMETHING IN FRONT OF THEM RATHER THAN NAMING IT. WHAT THEY POINT AT IS
# ONLY KNOWABLE BY LOOKING, AND THE CONVERSATION IS NOT LOOKING — IT IS WHAT WAS TRUE EARLIER.
POINTED = (
    "the show i", "the show im", "the show i'm", "the video i", "the video im", "the video i'm",
    "im watching", "i'm watching", "i am watching", "this show", "this video", "this movie",
    "this page", "this song", "this article", "on my screen", "in front of me", "right now",
    "currently watching", "playing right now", "this thing", "what im", "what i'm",
)

# THE TOOLS THAT ACTUALLY GO AND LOOK.
LOOKERS = ("current_activity", "already_open", "screen", "list_open_windows")

# A FIGURE, A YEAR, A DURATION: THE THINGS A DECK STATES THAT ARE EITHER RIGHT OR WRONG.
FIGURE = re.compile(r"\d[\d,.]*\s*(?:%|million|billion|k\b|m\b)?", re.I)

# TWO OR MORE CAPITALISED WORDS MAKING ONE NAME: A PERSON, A PLACE, AN EPISODE, A BATTLE.
# THE SMALL WORDS INSIDE A NAME STAY LOWERCASE — "Battle of the Bastards", "House of the
# Dragon" — SO THEY HAVE TO BE ALLOWED THROUGH THE MIDDLE OR THE NAME IS NEVER SEEN WHOLE.
# ONE CAPITALISED WORD ALONE IS TOO ORDINARY TO JUDGE: IT STARTS EVERY SENTENCE.
JOINERS = r"(?:of|the|and|in|for|to|de|van|von|at|on)"

JOINER_WORDS = {"of","the","and","in","for","to","de","van","von","at","on","by"}
NAMES = re.compile(rf"\b[A-Z][a-z]+(?:[ '’-](?:{JOINERS}[ ])*[A-Z][a-z]+)+")

# A NAME MAY NOT BEGIN WITH THE ORDINARY WORD THAT OPENED THE SENTENCE. "Based on Jane
# Austen" IS THE WORD "Based", A JOINER, AND THEN THE ACTUAL NAME, AND TAKING THE WHOLE RUN
# AS ONE FACT MEANT A SOURCED NAME WENT LOOKING FOR A SOURCE UNDER A NAME NOBODY WROTE.
OPENERS = {"based", "directed", "starring", "written", "produced", "adapted", "set",
           "released", "nominated", "created", "featuring", "known", "made", "shot"}

# WORDS THAT ARE CAPITALISED BECAUSE THEY OPEN A LINE OR LABEL ONE, NOT BECAUSE THEY NAME
# ANYTHING, PLUS THE FURNITURE OF A DECK.
ORDINARY = {
    "title slide", "key moments", "key points", "the show", "the video", "slide one",
    "overview", "introduction", "conclusion", "key takeaways", "thank you", "summary",
}

# HOW MANY UNSOURCED FACTS ARE WORTH NAMING BACK. ENOUGH TO SHOW THE SHAPE OF THE PROBLEM.
MOST_NAMED = 6

# A LINE THIS SHORT WITH NO COLON AND NO BULLET IS A HEADING, NOT A STATEMENT.
HEADING_WORDS = 4

# FROM THIS MANY MADE-UP FACTS ON, THE DECK IS NOT WORTH SAVING AND IS TURNED BACK WHOLE.
# BELOW IT, THE LINES CARRYING THEM COME OUT AND THE REST IS WRITTEN.
MOSTLY_INVENTED = 3

DROPPED = (
    "Wrote {where} ({made}). {count} line(s) were left out because no tool this turn came back "
    "with what they said: {named}. Tell them the deck is done and that you left those out "
    "rather than guess. If they matter, go and read them up and add them with write_document "
    "again under a new name."
)

UNSOURCED = (
    "Nothing was written, because {much} in it came from nowhere. No tool this turn came back "
    "with:\n{made_up}\n\nEvery name, figure, date and episode in a file has to have been read "
    "off something first — a deck they keep and show to people is the worst place to guess. "
    "Either go and read up on it now, with read_page or search_web or describe_project, and "
    "write it again out of what comes back, or write only what you were actually told and "
    "leave the rest out. Do not put a fact in and hope.\n\n"
    "This is a step of the job, not a refusal of it. Go and read now, then call this again "
    "with the same path this turn. Do not apologise and do not stop."
)

# EVERY REFUSAL HERE IS THE MIDDLE OF THE ERRAND, NOT THE END OF IT. THE LAST LINE OF EACH
# SAYS WHAT TO DO NEXT, IN ORDER, BECAUSE A TOOL THAT ONLY SAYS NO GETS AN APOLOGY BACK
# INSTEAD OF THE JOB: THE TURN THAT WAS STOPPED FROM WRITING A FALSE DECK ANSWERED "I can't
# create that presentation" RATHER THAN GOING AND LOOKING.
UNLOOKED = (
    "Not written yet — you have not looked, so you do not know what it is about. They said "
    "{said!r}, which points at whatever is in front of them right now, and nothing this turn "
    "has been and found out what that is. What was said earlier in this conversation is what "
    "was true earlier, not what is on their screen now.\n\n"
    "Carry on and finish it, this turn, without asking them anything:\n"
    "1. current_activity, to see what is actually there.\n"
    "2. search_web or read_page about whatever that turns out to be.\n"
    "3. this tool again, written out of what those two came back with.\n"
    "This is a step of the job, not a refusal of it. Do not apologise and do not stop."
)


@tool
def describe_project(project: str) -> str:
    """Understand a project folder before saying or writing anything about it:
    where it is, how many files and in what languages, what it starts from, what
    is inside at the top level, what its README says, and the first thing each
    main source file says about itself.

    Call this first whenever you are asked to document, describe, explain,
    summarise or write about a project, a repository or a codebase, and before
    build for work on one. Give it the project's name, like "untitled", or its
    path. Do not list folders and read files one at a time to piece this together
    yourself: this is the whole picture in one call."""
    lines, complaint = briefing.brief(project)

    if lines is None:
        return reasons.no(complaint)

    return "\n".join(lines)


@tool
def write_file(path: str, text: str) -> str:
    """Create a new file of plain text with exactly this text in it. Give the
    full path, including the name, like "~/Desktop/projects/untitled/docs.md".
    This only ever creates: if something is already at that path it refuses and
    nothing is touched, so it can never wipe out somebody's work. To change a
    file that exists, use edit_file. Never write a file with run_command.

    A presentation, a Word document and a spreadsheet are not plain text and
    are made with write_document instead."""
    where = Path(path).expanduser()
    sort = SEALED.get(where.suffix.lower())

    if sort:
        return reasons.no(NOT_TEXT.format(name=where.name, kind=where.suffix.lstrip("."),
                                          doing="write", sort=sort))

    if where.exists():
        return reasons.no(EXISTS.format(path=where, inside=inside(where)))

    if not where.parent.is_dir():
        return reasons.no(NOWHERE.format(folder=where.parent, name=where.name))

    try:
        where.write_text(text, encoding="utf-8")
    except OSError as error:
        return reasons.no(f"Could not write {where.name}: {error}")

    return f"Wrote {where} ({len(text.splitlines())} lines)."


def flattened(words):
    """THE LETTERS AND DIGITS ONLY, LOWERCASE. A NAME IS THE SAME NAME WHETHER A PAGE WROTE
    IT "Unbowed and Unbent", A TITLE BAR WROTE IT "Unbowed And Unbent" OR AN ADDRESS WROTE IT
    "unbowed-and-unbent", AND A DECK MUST NOT BE REFUSED OVER A HYPHEN."""
    return "".join(each.lower() for each in words if each.isalnum())


# "535K", "1.2 million", "17.4M": A FIGURE A PAGE WROTE SHORT.
SHORT = re.compile(r"(\d+(?:\.\d+)?)\s*(k|m|b|thousand|million|billion)\b", re.I)

SCALE = {"k": 1_000, "thousand": 1_000, "m": 1_000_000, "million": 1_000_000,
         "b": 1_000_000_000, "billion": 1_000_000_000}


def expanded(seen):
    """EVERY SHORT FIGURE IN WHAT THE TOOLS SAID, WRITTEN OUT IN FULL."""
    out = set()

    for number, scale in SHORT.findall(seen):
        try:
            out.add(str(int(float(number) * SCALE[scale.lower()])))
        except (ValueError, KeyError):
            continue

    return out


def rounded(bare):
    """A FIGURE AND THE NEARBY ROUNDINGS OF IT, SO 535000 ANSWERS FOR A PAGE'S 535K."""
    return {bare, bare.lstrip("0")} | {str(int(bare[:each] + "0" * (len(bare) - each)))
                                       for each in range(1, min(4, len(bare)) + 1)}


def without(text, made_up):
    """THE DECK WITH THE LINES THAT STATE A MADE-UP FACT TAKEN OUT, AND THE REST LEFT ALONE."""
    kept = [line for line in text.splitlines()
            if not any(each in line for each in made_up)]

    return "\n".join(kept)


def claimed(text):
    """THE LINES OF A DECK THAT STATE SOMETHING, WITHOUT THE HEADINGS THAT ONLY ORGANISE IT.

    "Main Characters" IS FURNITURE: IT ANNOUNCES A SLIDE AND ASSERTS NOTHING, AND HOLDING IT
    TO A SOURCE IS HOW A TURN ENDED UP WRITING THE SAME DECK FOUR TIMES. A LINE THAT CARRIES A
    BULLET, A COLON OR A SENTENCE IS MAKING A CLAIM; A BARE TWO OR THREE WORDS IS NOT."""
    kept = []

    for line in text.splitlines():
        said = line.strip()

        if not said:
            continue

        bare = said.lstrip("-*#").strip()
        heading = ":" not in bare and len(bare.split()) <= HEADING_WORDS and said == bare

        if not heading:
            kept.append(said)

    return "\n".join(kept)


def unsourced(text, title):
    """THE FACTS IN THIS THAT NO TOOL THIS TURN CAME BACK WITH, WORST FIRST.

    A FACT IS A FIGURE OR A NAME OF TWO WORDS OR MORE, BECAUSE THOSE ARE THE THINGS THAT ARE
    EITHER TRUE OR NOT. THE PROSE AROUND THEM IS HAPPY'S OWN AND IS NOT JUDGED — HE IS
    WRITING THE DECK, NOT COPYING ONE OUT."""
    seen = flattened(wrapping.learned() + " " + (conversation.asking() or ""))

    if not seen.strip():
        return []

    missing = []
    digits = "".join(each for each in seen if each.isdigit())

    # A PAGE SAYS "535K views" AND A SHEET SAYS 535000, WHICH IS THE SAME FACT WRITTEN OUT
    # RATHER THAN A MADE-UP ONE. THE SHORT FORMS THE PAGE USED ARE EXPANDED ONCE HERE SO A
    # HONESTLY EXPANDED FIGURE IS NOT CHASED FOR A SOURCE IT ALREADY HAS.
    shorthand = expanded(wrapping.learned())
    said = claimed(text)

    for found in list(NAMES.finditer(said)) + list(FIGURE.finditer(said)):
        fact = found.group(0).strip().strip(".,")
        head = fact.split()[0].lower() if fact.split() else ""

        # THE OPENING WORD WAS NOT PART OF THE NAME, SO THE NAME IS WHAT FOLLOWS IT.
        if head in OPENERS:
            fact = " ".join(fact.split()[1:]).lstrip()

            while fact.split() and fact.split()[0].lower() in JOINER_WORDS:
                fact = " ".join(fact.split()[1:])

            if len(fact.split()) < 2:
                continue

        if not fact or fact.lower() in ORDINARY or fact.lower() in title.lower():
            continue

        # A FIGURE IS SOURCED IF ITS DIGITS TURN UP ANYWHERE, COMMAS AND SPACING ASIDE: A
        # TOOL SAYING "17,358,020" ANSWERS FOR A DECK SAYING "17358020".
        bare = "".join(each for each in fact if each.isdigit())

        if bare and len(bare) > 2:
            if bare in digits or rounded(bare) & shorthand:
                continue
        elif flattened(fact) in seen:
            continue
        elif bare:
            continue  # A SHORT NUMBER IS A COUNT OR A BULLET, NOT A CLAIM WORTH CHASING.

        if fact not in missing:
            missing.append(fact)

    return missing[:MOST_NAMED]


def inside(where):
    """THE FIRST OF WHAT IS ALREADY IN A FILE, FOR TELLING A PLACEHOLDER FROM SOMEBODY'S WORK."""
    from hands.files import readers  # LATE: readers PULLS IN THE OFFICE LIBRARIES.

    try:
        said = readers.extract(where).strip()
    except Exception:
        return UNREADABLE.format(kind=where.suffix.lstrip(".") or "binary")

    if not said:
        return EMPTY

    return said[:GLANCE] + ("..." if len(said) > GLANCE else "")


@tool
def edit_file(path: str, find: str, replace: str) -> str:
    """Change part of a file that exists: the exact text in "find" is swapped for
    "replace", once. Read the file first so "find" is copied from it word for
    word; if it is not there, or is there more than once, nothing changes and
    this says so. To add to the end, make "find" the last line and "replace" that
    line plus the new ones. To create a file, use write_file instead."""
    found, note = locate(path)

    if found is None:
        return reasons.no(note)

    if found.is_dir():
        return reasons.no(f"{found} is a folder, not a file.")

    sort = SEALED.get(found.suffix.lower())

    if sort:
        return reasons.no(NOT_TEXT.format(name=found.name, kind=found.suffix.lstrip("."),
                                          doing="change", sort=sort))

    try:
        text = found.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return reasons.no(f"Could not read {found.name}: {error}")

    count = text.count(find) if find else 0

    if count == 0:
        return reasons.no(MISSING.format(name=found.name))

    if count > 1:
        return reasons.no(SEVERAL.format(count=count, name=found.name))

    try:
        found.write_text(text.replace(find, replace, 1), encoding="utf-8")
    except OSError as error:
        return reasons.no(f"Could not write {found.name}: {error}")

    return f"Changed {found}."


@tool
def write_document(kind: KINDS, path: str, title: str, text: str) -> str:
    """Make a presentation, a Word document or a spreadsheet, as a real file of
    that kind that opens in the app that owns it. "slides" for a presentation or
    a deck, "document" for a letter, report or anything written up, "sheet" for
    a table, a list of figures or anything with columns.

    Use this whenever what was asked for is one of those three, and write the
    content yourself: they asked for a presentation about a thing, not for a
    file of notes about it. Put the whole thing in "text", a line on its own for
    each heading and the points under it each starting with "-"; that becomes
    one slide per heading, or a heading and its bullets, or one row per line
    with commas between the cells. Give the path including the name and leave
    the ending off, like "~/Desktop/greenhouse gases". write_file makes a plain
    text file and is not how any of these three are made.

    What it is about has to be found before it can be written about, and this
    is the last tool of the job rather than the first. When the subject is this
    thing here rather than something named outright — the show I am watching,
    this page, that song, my project — go and look with the tool that knows,
    this turn, before calling this. What was on their screen earlier in the
    conversation is not what is on it now, and a deck written out of a
    remembered title is a deck about the wrong thing.

    Then go and read about it before writing a line: search_web and read_page
    for anything out in the world, describe_project or read_file for something
    of theirs. Every name, date and figure that goes in has to have come back
    from a tool this turn. A director, a year or a fact you did not read
    somewhere is one you are making up, and it goes into a file they keep and
    show to people, which is a worse place to be wrong than out loud."""
    said = conversation.asking() or ""
    pointing = any(each in said.lower() for each in POINTED)

    if pointing and not wrapping.already(*LOOKERS):
        return reasons.no(UNLOOKED.format(said=said))

    # LOOKING IS NOT KNOWING. THE TURN THAT PUT "Battle of the Bastards" INTO A DECK ABOUT
    # HOUSE OF THE DRAGON HAD LOOKED, AND READ THE TITLE, AND THEN WROTE THE REST OUT OF THE
    # MODEL. SO WHAT GOES IN IS CHECKED AGAINST WHAT CAME BACK, NOT AGAINST WHETHER IT ASKED.
    # A DECK BUILT OUT OF NOTHING IS TURNED BACK. A DECK THAT IS RIGHT EXCEPT FOR A DETAIL OR
    # TWO IS WRITTEN, WITH THOSE TAKEN OUT AND SAID BACK — REFUSING THE WHOLE FILE OVER ONE
    # NAME SENT A TURN ROUND THE SAME DECK FOUR TIMES AND COST A MINUTE AND A HALF.
    made_up = unsourced(text, title)

    if len(made_up) >= MOSTLY_INVENTED:
        return reasons.no(UNSOURCED.format(
            much="much of what you were about to put",
            made_up="\n".join(f"- {each}" for each in made_up)))

    if made_up:
        text = without(text, made_up)

    made_for = writer(kind)

    if not made_for:
        return reasons.no(f"There is no kind of file called {kind!r}. Use slides, document or sheet.")

    ending, make = made_for
    where = Path(path).expanduser().with_suffix(ending)

    if where.exists():
        return reasons.no(EXISTS.format(path=where, inside=inside(where)))

    if not where.parent.is_dir():
        return reasons.no(NOWHERE.format(folder=where.parent, name=where.name))

    try:
        made = make(str(where), title, text)
    except Exception as error:
        return reasons.no(f"Could not write {where.name}: {error}")

    if made_up:
        return DROPPED.format(where=where, made=made, count=len(made_up),
                              named=", ".join(made_up))

    return f"Wrote {where} ({made})."


TOOLS = [describe_project, write_file, edit_file, write_document]
