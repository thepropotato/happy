"""THE CONVERSATION LAID OUT FOR A PERSON TO READ."""

from datetime import datetime

from memory import conversation, storage

WIDTH = 5

YOU = "you"
HAPPY = "happy"
TOOL = "  ·"


def when(entry):
    try:
        return datetime.fromisoformat(entry["at"])
    except (KeyError, ValueError):
        return None


def show(entries=None, tools=False):
    """TOOL CALLS ARE PLUMBING, HIDDEN BY DEFAULT."""
    lines = []

    for entry in conversation.history() if entries is None else entries:
        stamp = when(entry)
        clock = stamp.strftime("%d %b %H:%M") if stamp else "?"

        if entry.get("message"):
            lines.append(line(clock, YOU, entry["message"]))

        if tools:
            lines.extend(called(clock, entry.get("tools", [])))

        if entry.get("reply"):
            lines.append(line(clock, HAPPY, entry["reply"]))

    return "\n".join(lines)


def line(clock, who, words):
    return f"{clock}  {who:>{WIDTH}}  {words}"


def called(clock, calls):
    """ONE LINE PER CALL, AND WHY IT WAS MADE WHEN THE MODEL SAID WHY."""
    lines = []

    for each in calls:
        lines.append(line(clock, TOOL, f"{each.get('name')}({each.get('args')})"))

        if each.get("why"):
            lines.append(line(clock, "", f"  {each['why']}"))

    return lines


if __name__ == "__main__":
    import sys

    words = [a for a in sys.argv[1:] if not a.startswith("--")]
    found = conversation.search(" ".join(words)) if words else None

    print(show(found, tools="--tools" in sys.argv) or f"Nothing said yet. ({storage.path()})")
