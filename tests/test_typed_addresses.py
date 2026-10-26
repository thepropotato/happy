"""A page past a site's front door opens only when somebody gave its address or a tool showed it."""

from happy import tools
from happy.tools import apps, web


def check(where, said, shown=(), held=()):
    tools.seen.set(list(shown))
    web.results = [{"href": h} for h in held]
    original = tools.said_lately
    tools.said_lately = lambda: said
    try:
        return apps.typed_address({"where": where})
    finally:
        tools.said_lately = original
        web.results = []


def test_a_video_id_from_memory_is_turned_away():
    refused = check("https://www.youtube.com/watch?v=ZlZtB9u5X5I", "can you open the video song for touch me?")
    assert refused and refused.startswith("Error") and "web_search" in refused and '"youtube"' in refused
    assert check("https://www.imdb.com/title/tt1047316/", "open the imdb page for dhoom 2")
    assert check("instagram.com/p/xxxx", "open the instagram post where virat kohli announced his retirement")


def test_sites_searches_and_their_own_words_open():
    assert check("youtube.com", "open youtube") is None
    assert check("https://www.youtube.com/results?search_query=touch+me+dhoom+2", "open touch me") is None
    assert check("github.com/ollama/ollama/issues", "open the github issues for ollama") is None
    assert check("youtube.com/@lofigirl", "open the lofi girl channel") is None
    assert check("Touch Me Dhoom 2 video song", "open touch me") is None


def test_an_address_they_gave_or_a_tool_showed_opens():
    assert check("https://www.youtube.com/watch?v=jfKfPfyJRdk", "open https://www.youtube.com/watch?v=jfkfpfyjrdk") is None
    assert check("https://en.wikipedia.org/wiki/Dhoom_2_(soundtrack)", "open it",
                 ["Dhoom 2 (soundtrack) — https://en.wikipedia.org/wiki/Dhoom_2_(soundtrack)"]) is None
    assert check("https://www.youtube.com/watch?v=Qm3Lp7Tz0aE", "open it", held=["https://www.youtube.com/watch?v=Qm3Lp7Tz0aE"]) is None


def test_an_unknown_backend_goes_ahead():
    assert check("https://www.youtube.com/watch?v=ZlZtB9u5X5I", None) is None


def test_a_placeholder_for_an_id_is_turned_away():
    assert check("https://www.instagram.com/p/Cy", "open the instagram post where virat kohli announced his retirement")
    assert check("https://github.com/ollama/??", "open the github issue about ollama")
    assert check("https://open.spotify.com/track/...", "open blinding lights on spotify", ["https://open.spotify.com/track/7tR0bQ2p8yLdQvYv3c1KxW"])
    assert check("https://...", "show me elon musk's latest tweet")
