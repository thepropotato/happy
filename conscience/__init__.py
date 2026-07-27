"""ASKING BEFORE DOING SOMETHING THAT CANNOT BE UNDONE."""

YES = {"y", "yes", "yeah", "yep", "ok", "okay", "sure", "go ahead", "do it"}

REFUSED = "Cancelled, the user said no. Do not try to do it another way."


def console_confirm(what, reason):
    print(f"\n  Happy wants to do something that {reason}:\n    {what}")

    try:
        return input("  Allow it? [y/N] ").strip().lower() in YES
    except (EOFError, KeyboardInterrupt):
        print()

        return False


handler = console_confirm


def asks(ask):
    """WIRE UP HOW HAPPY ASKS. None PUTS THE CONSOLE BACK."""
    global handler

    handler = ask or console_confirm


def allowed(what, reason):
    """TRUE WHEN THE PERSON SAID YES."""
    return handler(what, reason)
