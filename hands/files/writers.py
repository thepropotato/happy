"""MAKING THE THREE OFFICE FILES, WHICH ARE ZIPPED XML AND NEED NO OFFICE INSTALLED."""

import re

# A HEADING AND THE LINES UNDER IT: THE SHAPE EVERY ONE OF THESE IS WRITTEN FROM.
BULLET = "-"

# WHAT A MODEL WRITES TO MARK WHERE IT IS UP TO RATHER THAN TO NAME ANYTHING: "Slide 3",
# "Title Slide", "Section 2". LEFT IN, THESE BECOME THE WORDS ON THE SLIDE, AND A DECK GOES
# OUT HEADED "Slide 1" WITH THE REAL SUBJECT HIDDEN IN A BULLET UNDERNEATH IT.
COUNTER = re.compile(r"^(title\s+slide|slide|section|page|part|bullet)\s*\d*\s*[:.)-]?$", re.I)

# THE SAME COUNTING, BUT WITH THE REAL HEADING WRITTEN AFTER IT: "Slide 2: Cast". THE
# COUNTER COMES OFF AND THE NAME STAYS.
PREFIXED = re.compile(r"^(?:title\s+slide|slide|section|page|part)\s*\d*\s*[:.)-]\s*(.+)$", re.I)

# A BULLET THAT IS REALLY THE HEADING FOR ITS OWN SECTION, WRITTEN AS "Title: the thing".
NAMED = re.compile(r"^(title|heading|topic|subject)\s*[:-]\s*(.+)$", re.I)


def parted(text):
    """THE TEXT AS SECTIONS. A LINE ON ITS OWN OPENS ONE, THE LINES UNDER IT FILL IT.

    THIS IS WHAT THE MODEL ACTUALLY WRITES WHEN ASKED FOR SLIDES: A TITLE, THEN SOME
    BULLETS, THEN THE NEXT TITLE. MARKDOWN HASHES AND DASHES ARE ALLOWED AND TAKEN OFF."""
    sections = []

    for line in text.splitlines():
        said = line.strip()

        if not said:
            continue

        if said.startswith(BULLET) or said.startswith("*"):
            point = said.lstrip("-*").strip()

            if point and sections:
                sections[-1][1].append(point)
            elif point:
                sections.append([point, []])
        else:
            sections.append([said.lstrip("#").strip(), []])

    return [named(head, points) for head, points in sections if head]


def named(head, points):
    """A SECTION UNDER ITS REAL NAME RATHER THAN THE MODEL'S COUNTING.

    "Slide 2" IS NOT WHAT THE SECTION IS ABOUT, IT IS WHERE THE MODEL WAS UP TO. WHEN A
    HEADING ONLY COUNTS, THE NAME IS IN THE BULLETS: EITHER ONE WRITTEN "Title: the thing",
    WHICH IS LIFTED OUT AND STOPS BEING A BULLET, OR FAILING THAT THE FIRST BULLET."""
    carried = PREFIXED.match(head)

    if carried:
        return carried.group(1).strip(), points

    if not COUNTER.match(head):
        return head, points

    for index, point in enumerate(points):
        found = NAMED.match(point)

        if found:
            return found.group(2).strip(), points[:index] + points[index + 1:]

    # NOTHING NAMED ITSELF, SO THE FIRST POINT IS THE NEAREST THING TO A HEADING THERE IS.
    return (points[0], points[1:]) if points else (head, points)


def same(one, other):
    """WHETHER TWO HEADINGS ARE THE SAME WORDS, PUNCTUATION AND CASE ASIDE."""
    strip = lambda word: "".join(each for each in word.lower() if each.isalnum())

    return bool(strip(one)) and strip(one) == strip(other)


def slides(path, title, text):
    """A PRESENTATION: A TITLE SLIDE, THEN ONE SLIDE PER SECTION."""
    from pptx import Presentation

    deck = Presentation()
    sections = parted(text)

    cover = deck.slides.add_slide(deck.slide_layouts[0])
    cover.shapes.title.text = title
    body = sections

    # A FIRST SECTION THAT ONLY REPEATS THE TITLE IS THE COVER, NOT A SLIDE OF ITS OWN. IT
    # GOES UNDER THE TITLE AS THE SUBTITLE AND DOES NOT COME ROUND AGAIN, WHICH IS WHAT PUT
    # THE SAME WORDS ON SLIDE ONE AND SLIDE TWO OF EVERY DECK.
    if sections and same(sections[0][0], title):
        body = sections[1:]
        under = sections[0][1][0] if sections[0][1] else ""
    else:
        under = sections[0][0] if sections else ""

    if len(cover.placeholders) > 1:
        cover.placeholders[1].text = under

    for head, points in body:
        slide = deck.slides.add_slide(deck.slide_layouts[1])
        slide.shapes.title.text = head
        frame = slide.placeholders[1].text_frame

        if not points:
            continue

        # THE FRAME OPENS WITH ONE EMPTY PARAGRAPH ALREADY IN IT, SO THE FIRST POINT GOES
        # INTO THAT ONE; ADDING IT WOULD LEAVE EVERY SLIDE STARTING ON A BLANK BULLET.
        frame.text = points[0]

        for point in points[1:]:
            frame.add_paragraph().text = point

    deck.save(path)

    return f"{len(deck.slides)} slides"


def document(path, title, text):
    """A WORD DOCUMENT: THE TITLE, THEN EACH SECTION AS A HEADING AND ITS PARAGRAPHS."""
    from docx import Document

    paper = Document()
    paper.add_heading(title, level=0)
    sections = parted(text)

    for head, points in sections:
        paper.add_heading(head, level=1)

        for point in points:
            paper.add_paragraph(point, style="List Bullet")

    paper.save(path)

    return f"{len(sections)} sections"


def sheet(path, title, text):
    """A SPREADSHEET: ONE ROW PER LINE, SPLIT INTO CELLS ON COMMAS OR TABS."""
    from openpyxl import Workbook

    book = Workbook()
    page = book.active
    page.title = title[:31] or "Sheet1"  # EXCEL REFUSES A TAB NAME LONGER THAN THIS.
    rows = 0

    for line in text.splitlines():
        said = line.strip()

        if not said:
            continue

        splitter = "\t" if "\t" in said else ","
        page.append([cell.strip() for cell in said.lstrip("-*").split(splitter)])
        rows += 1

    book.save(path)

    return f"{rows} rows"


# WHAT EACH KIND IS CALLED, WHAT IT ENDS IN, AND WHAT MAKES IT.
WRITERS = {
    "slides": (".pptx", slides),
    "document": (".docx", document),
    "sheet": (".xlsx", sheet),
}

# THE WORDS A PERSON AND A MODEL ACTUALLY REACH FOR. THE SCHEMA NAMES ONE WORD PER KIND AND
# THE MODEL WROTE "presentation", WHICH COST A WHOLE ROUND TO A VALIDATION ERROR AND TAUGHT
# IT NOTHING; THE NEAR WORDS ARE TAKEN AS MEANT INSTEAD.
ALSO_CALLED = {
    "presentation": "slides", "powerpoint": "slides", "deck": "slides", "pptx": "slides",
    "slide": "slides", "slideshow": "slides",
    "doc": "document", "word": "document", "docx": "document", "letter": "document",
    "report": "document", "text": "document",
    "spreadsheet": "sheet", "excel": "sheet", "xlsx": "sheet", "table": "sheet",
    "csv": "sheet", "workbook": "sheet",
}


def writer(kind):
    """THE ENDING AND THE MAKER FOR A KIND, UNDER WHATEVER WORD IT WAS ASKED FOR."""
    named = str(kind or "").strip().lower()

    return WRITERS.get(named) or WRITERS.get(ALSO_CALLED.get(named, ""))
