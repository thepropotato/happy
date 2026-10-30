"""Says when a reply claims Happy did something that no tool this turn did."""

import re

# EACH DEED IS THE PAST TENSE OF AN ACT AND THE TOOLS THAT CAN PERFORM IT; A CONNECTED SERVICE'S TOOL MAY PERFORM ANY OF THEM.
DEEDS = [
    ("saved|wrote|written|created", {"write_file", "remember", "whatsapp_remember", "routine", "download", "reminder"}),
    ("sent|messaged|replied|forwarded|emailed", {"whatsapp_send", "tell_coding_agent"}),
    ("deleted|trashed|removed", {"move_to_trash", "forget", "reminder", "routine"}),
    ("downloaded", {"download"}),
    ("opened", {"open_app", "open_file", "open_link", "write_file", "browser_tabs", "hand_off_coding"}),
]
DONE_BY = r"(?:I(?:['’]ve| have)?(?: just)?|It['’]s|has been|have been|is(?: now)?|are(?: now)?)"


def unbacked(text, done):
    """The first sentence in text claiming a deed none of the done tools can perform, or None."""
    if any("__" in name or name in ("use_service_tool", "account_connector") for name in done):
        return None
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        for verbs, tools in DEEDS:
            claim = rf"(?:\b{DONE_BY}\s+(?:now\s+|also\s+|successfully\s+)?|^\W*)(?:{verbs})\b"
            if re.search(claim, sentence.strip(), re.IGNORECASE) and not tools & done:
                return sentence.strip()
    return None


def correction(claim):
    return (f'You said "{claim}", but no tool did that this turn. If they asked for it, call the tool now. '
            f"If not, answer again without saying it was done.")
