"""THE FACTS A SCRIPT-DRAWN PAGE STILL SHIPS INSIDE ITS HTML, READ WITHOUT RUNNING ANY SCRIPT."""

import json
import re

import extruct
from bs4 import BeautifulSoup

# THE FOUR WAYS A PAGE CAN DECLARE ITS OWN FACTS. A SITE PICKS ONE AND LEAVES THE OTHERS
# EMPTY, AND WHICH ONE IT PICKS IS NOT KNOWABLE IN ADVANCE, SO ALL FOUR ARE READ.
SYNTAXES = ("json-ld", "microdata", "rdfa", "opengraph")

# A SCRIPT HANDING ITS PAGE A LUMP OF STATE: "var anything = {", "window.thing={", AND THE
# ONES THAT SIT IN A TYPED SCRIPT TAG. THE NAME IS DELIBERATELY NOT PART OF THE PATTERN.
ASSIGNED = re.compile(r"(?:var|let|const)?\s*[\w.$\[\]\"']{2,80}\s*=\s*\{")

# BELOW THIS A SCRIPT IS A HANDFUL OF SETTINGS RATHER THAN THE PAGE'S OWN FACTS.
LEAST_BLOB = 400

# THE FIELD NAMES SITES ACTUALLY USE FOR A TALLY, AND WHAT EACH ONE IS. THIS IS THE WHOLE
# OF WHAT MAKES THE READING GENERAL: NO PATH INTO ANY PARTICULAR SITE'S DATA, JUST THE
# NAMES THAT MEAN THE SAME THING WHEREVER THEY TURN UP.
MEANS = {
    "viewcount": "Views", "views": "Views", "viewcounttext": "Views", "playcount": "Plays",
    "likecount": "Likes", "likes": "Likes", "favoritecount": "Likes",
    "dislikecount": "Dislikes",
    "commentcount": "Comments", "comments": "Comments", "numcomments": "Comments",
    "replycount": "Replies", "sharecount": "Shares", "repostcount": "Reposts",
    "subscribercount": "Subscribers", "followercount": "Followers", "followers": "Followers",
    "followingcount": "Following", "score": "Score", "upvotes": "Upvotes", "ups": "Upvotes",
    "ratingcount": "Ratings", "reviewcount": "Reviews", "answercount": "Answers",
    "stargazers_count": "Stars", "forks_count": "Forks", "watchers_count": "Watchers",
}

META = ("og:title", "og:description", "description", "og:site_name")

# THE FIELDS WORTH SAYING OUT OF STRUCTURED DATA, AND WHAT TO CALL EACH.
SAID = (
    ("name", "Title"), ("headline", "Title"), ("description", "About"),
    ("datePublished", "Published"), ("uploadDate", "Published"), ("duration", "Length"),
)

MOST_ABOUT = 400

# WHAT SCHEMA.ORG CALLS A TALLY, SAID THE WAY A PERSON SAYS IT. A WATCH AND A VIEW ARE ONE
# THING UNDER TWO NAMES, SO BOTH BECOME Views AND THE SECOND FALLS OUT AS A DUPLICATE.
COUNTED = {"Like": "Likes", "Watch": "Views", "Comment": "Comments", "Share": "Shares",
           "Follow": "Followers", "Subscribe": "Subscribers"}


def summary(html):
    """WHAT THE PAGE SAYS ABOUT ITSELF, AS LINES, OR "" WHEN IT SAYS NOTHING USEFUL.

    WHAT A SITE DECLARES IN ITS MARKUP AND WHAT IT HANDS ITS OWN SCRIPTS ARE DIFFERENT
    FACTS, AND EACH KNOWS THINGS THE OTHER LEAVES OUT, SO THESE ADD UP RATHER THAN TAKE
    TURNS. NEITHER OF THEM KNOWS WHICH SITE IT IS READING."""
    lines = declared(html) + shipped(html)

    if not lines:
        lines = tags(html)

    return "\n".join(once(line for line in lines if line))


def once(lines):
    """EACH FACT SAID ONE TIME. THE SAME FACT ARRIVES WORDED TWO WAYS — "PT37M49S" BESIDE
    "37 minutes 49 seconds" — SO IT IS THE LABEL THAT DECIDES, AND THE FIRST ONE WINS."""
    kept = {}

    for line in lines:
        label = line.split(":", 1)[0] if ":" in line else line
        kept.setdefault(label, line)

    return kept.values()


def declared(html):
    """WHAT A PAGE STATES ABOUT ITSELF IN THE MARKUP EVERY SITE AGREES ON, AS LINES."""
    return structured(html)


def shipped(html):
    """THE FACTS A PAGE HANDS ITS OWN SCRIPTS, FOUND WITHOUT KNOWING WHOSE PAGE IT IS.

    A SITE THAT DRAWS ITSELF PUTS THE NUMBERS IT IS ABOUT TO DRAW IN A BLOB OF JSON FIRST.
    THE BLOB IS NAMED DIFFERENTLY EVERYWHERE, SO NOTHING HERE LOOKS FOR A NAME: IT READS
    EVERY BLOB THE PAGE CARRIES AND KEEPS THE FIELDS WHOSE NAMES MEAN A TALLY."""
    lines = []

    for data in blobs(html):
        for label, value in tallies(data):
            lines.append(f"{label}: {value}")

    return lines


def blobs(html):
    """EVERY JSON OBJECT THE PAGE CARRIES, WHATEVER IT CALLS THEM, BIGGEST FIRST."""
    found = []

    for script in BeautifulSoup(html, "lxml").find_all("script"):
        body = script.string or ""

        if not body or len(body) < LEAST_BLOB:
            continue

        for opening in ASSIGNED.finditer(body):
            data = balanced(body, opening.end() - 1)

            if isinstance(data, dict):
                found.append(data)
                break  # ONE OBJECT PER SCRIPT: THE FIRST IS THE PAGE'S OWN STATE.

    return sorted(found, key=lambda each: -len(each))


def tallies(data):
    """THE COUNTS INSIDE A BLOB, AS (WHAT IT IS, HOW MANY). NAMES DECIDE, NOT PLACES."""
    found = {}

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                label = MEANS.get(key.lower())

                if label and label not in found:
                    number = counted(value)

                    if number:
                        found[label] = number

                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(data)

    return found.items()


def counted(value):
    """THE NUMBER A FIELD IS SAYING, WHETHER IT SAYS IT PLAINLY OR WRAPS IT IN WORDS."""
    if isinstance(value, bool):
        return ""

    if isinstance(value, (int, float)):
        return f"{int(value):,}"

    if isinstance(value, str) and value.strip().replace(",", "").isdigit():
        return f"{int(value.replace(',', '')):,}"

    return ""


def structured(html):
    """THE PRODUCT, ARTICLE OR VIDEO A PAGE DECLARES ITSELF TO BE, IN WHICHEVER OF THE FOUR
    WAYS IT DECLARES IT. READING ONLY THE FIRST MISSES SITES THAT USE ANY OF THE OTHERS."""
    lines = []

    for syntax in SYNTAXES:
        for item in marked(html, syntax):
            lines += described(item)

    return lines


def marked(html, syntax):
    """ONE SYNTAX'S WORTH OF WHAT THE PAGE DECLARES, OR NOTHING WHEN IT DECLARES NONE OF IT."""
    try:
        return extruct.extract(html, syntaxes=[syntax], uniform=True).get(syntax) or []
    except Exception:
        return []  # A PAGE WITH BROKEN MARKUP IS STILL A PAGE, AND THE OTHER READERS FOLLOW.


def described(item):
    if not isinstance(item, dict):
        return []

    if "@graph" in item:
        return [line for each in item["@graph"] for line in described(each)]

    lines = [f"{label}: {spoken(label, item[key])}" for key, label in SAID if item.get(key)]
    offer = item.get("offers")

    if isinstance(offer, list):
        offer = offer[0] if offer else None

    if isinstance(offer, dict) and offer.get("price"):
        lines.append(f"Price: {offer.get('price')} {offer.get('priceCurrency', '')}".strip())

    rating = item.get("aggregateRating")

    if isinstance(rating, dict) and rating.get("ratingValue"):
        lines.append(f"Rating: {rating['ratingValue']} from {rating.get('ratingCount') or rating.get('reviewCount', '?')} ratings")

    stats = item.get("interactionStatistic") or []

    for stat in stats if isinstance(stats, list) else [stats]:
        if isinstance(stat, dict) and stat.get("userInteractionCount"):
            kind = str(stat.get("interactionType", "")).rsplit("/", 1)[-1].removesuffix("Action")
            lines.append(f"{COUNTED.get(kind, kind or 'Interactions')}: {views(stat['userInteractionCount'])}")

    return lines


# WHAT A DESCRIPTION TAG ACTUALLY IS. CALLING IT "About" READ AS CONTENT ON THE PAGE, AND A
# PROFILE'S BLURB WENT OUT AS THAT PERSON'S LATEST POST.
BLURB = "The page describes itself as"

WARNING = "This is the page's own blurb, not anything posted on it."


def tags(html):
    """THE OPEN GRAPH AND DESCRIPTION TAGS, WHICH NEARLY EVERY PAGE CARRIES. THIS IS THE LAST
    RESORT: WHEN IT IS ALL WE HAVE, THE PAGE ITSELF WAS NEVER READ, AND SAYING SO MATTERS."""
    page = BeautifulSoup(html, "lxml")
    lines = []
    blurbed = False

    for name in META:
        tag = page.find("meta", attrs={"property": name}) or page.find("meta", attrs={"name": name})

        if tag and tag.get("content"):
            if "description" in name:
                label = BLURB
                blurbed = True
            else:
                label = name.split(":")[-1].replace("_", " ").title()

            lines.append(f"{label}: {short(tag['content'])}")

    if blurbed:
        lines.append(WARNING)

    return lines


def balanced(text, start):
    """THE JSON OBJECT THAT OPENS AT start, FOUND BY COUNTING BRACES, OR None."""
    if start >= len(text) or text[start] != "{":
        return None

    depth = 0
    quoted = False
    escaped = False

    for index in range(start, len(text)):
        char = text[index]

        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1

            if depth == 0:
                try:
                    return json.loads(text[start:index + 1])
                except ValueError:
                    return None

    return None


# HOW LONG SOMETHING RUNS, WRITTEN THE WAY THE STANDARD WRITES IT: PT37M49S, PT00H01M02S.
CLOCK = re.compile(r"^P(?:\d+D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$")


def spoken(label, value):
    """A FIELD AS IT SHOULD BE HEARD. A LENGTH IN THE STANDARD'S OWN SHORTHAND IS UNSAYABLE,
    SO IT BECOMES HOURS AND MINUTES; EVERYTHING ELSE IS SAID AS IT CAME."""
    said = short(str(value))

    if label != "Length":
        return said

    found = CLOCK.match(said.strip())

    if not found:
        return said

    hours, minutes, seconds = (int(each or 0) for each in found.groups())
    parts = [f"{hours} hours" if hours else "", f"{minutes} minutes" if minutes else "",
             f"{seconds} seconds" if seconds else ""]

    return " ".join(part for part in parts if part) or said


def views(count):
    try:
        return f"{int(count):,}"
    except (TypeError, ValueError):
        return str(count or "")


def short(said):
    said = " ".join(str(said).split())

    return said if len(said) <= MOST_ABOUT else said[:MOST_ABOUT].rstrip() + "..."
