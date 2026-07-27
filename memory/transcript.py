"""THE CONVERSATION LAID OUT FOR A PERSON TO READ."""

from datetime import datetime

from memory import conversation, storage

WIDTH = 5

NAMES = {conversation.YOU: "you", conversation.HAPPY: "happy", conversation.TOOL: "  ·"}


def when(entry):
    try:
        return datetime.fromisoformat(entry["at"])
    except (KeyError, ValueError):
        return None


def show(entries=None, tools=False):
    """TOOL CALLS ARE PLUMBING, HIDDEN BY DEFAULT."""
    lines = []

    for entry in conversation.history() if entries is None else entries:
        if entry.get("who") == conversation.TOOL and not tools:
            continue

        stamp = when(entry)
        clock = stamp.strftime("%d %b %H:%M") if stamp else "?"
        who = NAMES.get(entry.get("who"), entry.get("who", "?"))

        if entry.get("who") == conversation.TOOL:
            lines.append(f"{clock}  {who:>{WIDTH}}  {entry.get('tool')}({entry.get('args')})")
        else:
            lines.append(f"{clock}  {who:>{WIDTH}}  {entry.get('text', '')}")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    words = [a for a in sys.argv[1:] if not a.startswith("--")]
    found = conversation.search(" ".join(words)) if words else None

    print(show(found, tools="--tools" in sys.argv) or f"Nothing said yet. ({storage.path()})")
