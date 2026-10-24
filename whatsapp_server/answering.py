"""WHAT EVERY TOOL ON EVERY SERVER ANSWERS WITH: ONE SHORT JSON STRING."""

import json

# THIS ONLY GUARDS THE MODEL'S CONTEXT: THE CLIENT CUTS IT AGAIN BEFORE SPEAKING.
MOST = 4000


def ok(data):
    return json.dumps(data, default=str, ensure_ascii=False)[:MOST]


def some(text, most=300):
    """A FIELD SOMEBODY ELSE WROTE, WITH ITS NEWLINES AND ITS ESSAY TAKEN OFF."""
    return "" if not text else " ".join(str(text).split())[:most]
