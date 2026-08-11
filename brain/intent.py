"""WHAT THE PERSON PROBABLY WANTS, DECIDED BY WORDS ALONE — NO MODEL CALL."""

import re

KEYWORDS = {
    "messaging": {
        "send", "text", "message", "msg", "whatsapp", "call", "ring", "email",
        "mail", "slack", "chat", "dm", "forward", "reply", "respond", "contact",
        "tell", "inform", "notify", "attach", "file to",
    },
    "browsing": {
        "open", "play", "search", "website", "site", "video", "youtube", "watch",
        "browse", "look up", "find", "google", "bing", "read", "article", "news",
        "show me", "go to", "navigate", "url", "link",
    },
    "remembering": {
        "remember", "don't forget", "forget", "note that", "save that", "keep that",
        "store", "recall", "memory", "remind",
    },
    "coding": {
        "code", "build", "script", "github", "git", "program", "function",
        "write a", "create a", "fix the", "debug", "run", "execute", "terminal",
        "shell", "bash", "python", "install",
    },
}


def word_match(keyword, lowered):
    """TRUE ONLY WHEN keyword APPEARS AS A DISTINCT WORD (OR PHRASE) IN lowered."""
    escaped = re.escape(keyword)
    return bool(re.search(rf"(?<![\w])({escaped})(?![\w])", lowered))


def classify(speech):
    """A frozenset OF INTENT LABELS, OR None WHEN NO CONFIDENT MATCH.

    RETURNS None — NOT AN EMPTY FROZENSET — WHEN NOTHING MATCHED CONFIDENTLY,
    SO CALLERS FALL BACK TO THE FULL TOOL SET RATHER THAN A NARROW EMPTY ONE.
    CONTACTS IS ALWAYS ADDED WITH MESSAGING; MULTI-LABEL RESULTS ARE RETURNED
    ONLY WHEN MORE THAN ONE CATEGORY MATCHED, SINCE A WIDE RESULT IS SAFER THAN
    A NARROW WRONG ONE.
    """
    lowered = (speech or "").lower()
    found = set()

    for label, words in KEYWORDS.items():
        for word in words:
            if word_match(word, lowered):
                found.add(label)
                break

    if not found:
        return None

    if "messaging" in found:
        found.add("contacts")

    return frozenset(found)
