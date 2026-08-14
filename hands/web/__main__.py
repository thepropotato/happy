"""SEARCH, OR READ ONE PAGE: python -m hands.web "weather hyderabad tomorrow" python -m
hands.web en.wikipedia.org/wiki/Hyderabad"""

import sys

from hands.web.tools import read_page, search_web

asked = " ".join(sys.argv[1:]) or "what day is it today"
looks_like_an_address = " " not in asked and "." in asked

if looks_like_an_address:
    print(read_page.invoke({"url": asked}))
else:
    print(search_web.invoke({"query": asked}))
