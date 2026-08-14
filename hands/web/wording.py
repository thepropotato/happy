"""RESULTS AS THE FEW LINES THE MODEL READS BEFORE IT SAYS ANYTHING."""

from urllib.parse import parse_qsl, urlencode, urlparse

MOST = 2000

# WHAT A SITE HANGS OFF AN ADDRESS TO KNOW WHERE THE CLICK CAME FROM.
COUNTERS = ("fbclid", "gclid", "msclkid", "igshid", "si", "ref_src", "ref_url")

NOTHING = "Nothing came back for {question}."

HEADING = "Results for {question}:"


def written(question, results):
    """EVERY RESULT AS A TITLE, AN ADDRESS AND A LINE OF WHAT THE PAGE SAYS."""
    if not results:
        return NOTHING.format(question=question)

    lines = [HEADING.format(question=question)]

    for number, each in enumerate(results, 1):
        lines.append(f"{number}. {each.title} — {short(each.url)}")

        if each.summary:
            lines.append(f"   {each.summary}")

    return "\n".join(lines)[:MOST]


def kept(query):
    """THE QUESTION PUT TO THE PAGE, WITHOUT THE PARTS THAT ONLY COUNT CLICKS."""
    asked = [
        (name, value)
        for name, value in parse_qsl(query, keep_blank_values=True)
        if not name.startswith("utm_") and name not in COUNTERS
    ]

    return urlencode(asked)


def short(url):
    """THE ADDRESS WITHOUT THE TRACKING, BUT WITH WHATEVER NAMES THE PAGE."""
    parsed = urlparse(url)
    plain = f"{parsed.netloc}{parsed.path}".removeprefix("www.").rstrip("/")

    if not plain:
        return url

    query = kept(parsed.query)

    return f"{plain}?{query}" if query else plain
