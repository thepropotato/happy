"""WHERE ELSE ON THE WEB A PICTURE APPEARS, WHICH IS THE NEAREST THING TO ASKING WHAT IT IS OF."""

import io

import httpx
from bs4 import BeautifulSoup

from hands.web.searching import LIKE_A_BROWSER, SearchError

PATIENCE = 25

# BIGGER THAN THIS AND THE UPLOAD TAKES LONGER THAN THE ANSWER IS WORTH.
WIDEST = 1024

MOST = 8

YANDEX = "https://yandex.com/images/search"

# ONE BLOCK OF ITS OWN PAGE IS ALL WE WANT BACK: WHERE IT PUT THE PICTURE WE JUST SENT.
LINK = '{"blocks":[{"block":"b-page_type_search-by-image__link"}]}'

# THE TITLE OF A PAGE THE PICTURE SITS ON, AND THE LINE UNDER IT.
SITES = ".CbirSites-ItemTitle"

# A PAGE THAT ONLY EMBEDS THE PICTURE NAMES ITSELF, NOT THE PICTURE, SO THESE SAY NOTHING.
NOISE = ("soundcloud", "brainly", "telegraph", "pinterest", "youtube", "facebook", "instagram")

MOST_TITLE = 120

SHORTEST = 4


def shrunk(image):
    """THE PICTURE SMALL ENOUGH TO SEND, AS PNG BYTES."""
    if image.width > WIDEST or image.height > WIDEST:
        ratio = WIDEST / max(image.width, image.height)
        image = image.resize((int(image.width * ratio), int(image.height * ratio)))

    hold = io.BytesIO()
    image.save(hold, format="PNG")

    return hold.getvalue()


def worth(title):
    """WHETHER A MATCH SAYS ANYTHING ABOUT THE PICTURE, OR IS A SITE NAMING ITSELF."""
    said = title.strip().lower()

    return len(said) >= SHORTEST and not any(word in said for word in NOISE)


def matched(image, most=MOST):
    """THE TITLES OF PAGES THIS PICTURE APPEARS ON, BEST FIRST.

    THESE ARE A CLUE AND NEVER AN ANSWER: A PAGE THAT SHOWS A PICTURE OFTEN SAYS WHAT IT IS,
    AND JUST AS OFTEN IS SOMEBODY'S PLAYLIST THAT HAPPENED TO USE IT AS A COVER."""
    picture = shrunk(image)

    with httpx.Client(headers=LIKE_A_BROWSER, timeout=PATIENCE, follow_redirects=True) as client:
        sent = client.post(
            YANDEX,
            params={"rpt": "imageview", "format": "json", "request": LINK},
            files={"upfile": ("shot.png", picture, "image/png")},
        )

        if sent.status_code >= 400:
            raise SearchError(f"yandex answered {sent.status_code} to the picture.")

        try:
            found = sent.json()["blocks"][0]["params"]["cbirId"]
        except Exception:
            raise SearchError("yandex would not say where it put the picture.")

        page = client.get(
            YANDEX, params={"rpt": "imageview", "cbir_id": found, "cbir_page": "sites"}
        )

        if page.status_code >= 400:
            raise SearchError(f"yandex answered {page.status_code} for the matches.")

    titles, seen = [], set()

    for part in BeautifulSoup(page.text, "lxml").select(SITES):
        title = " ".join(part.get_text(" ", strip=True).split())[:MOST_TITLE]

        if not worth(title) or title.lower() in seen:
            continue

        seen.add(title.lower())
        titles.append(title)

    return titles[:most]
