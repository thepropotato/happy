"""A file is looked for only when somebody named it or a tool showed it; a name the model made up is turned away."""

from happy import tools


def check(what, said, shown=()):
    tools.seen.set(list(shown))
    original = tools.said_lately
    tools.said_lately = lambda: said
    try:
        return tools.named_file({"what": what})
    finally:
        tools.said_lately = original


def test_a_file_they_named_is_looked_for():
    assert check("resume", "what does my resume say") is None
    assert check("resume.pdf", "what does my resume say") is None
    assert check("old notes", "delete the screenshot called old notes") is None


def test_a_file_a_tool_showed_is_looked_for():
    assert check("Q3 plan", "read the pdf my boss sent", ["[document] (file Q3-plan.pdf)"]) is None


def test_a_made_up_file_is_turned_away():
    refused = check("WhatsApp chat log", "summarise the chat that happened today in that group")
    assert refused and refused.startswith("Error") and "WhatsApp chat log" in refused


def test_a_real_path_and_an_unknown_backend_go_ahead():
    assert check("/etc/hosts", "anything") is None
    assert check("WhatsApp chat log", None) is None
