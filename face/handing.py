"""PICTURES HANDED BACK WITH THE ANSWER, FOR SOMEBODY WHO IS NOT IN THE ROOM."""

from pathlib import Path

# A REPLY IS NOT AN ALBUM. THE MODEL LOOPING ON A TOOL THAT WORKS IS A REAL SHAPE.
MOST = 3


carrying = None


def opened():
    """THE START OF A TURN WHOSE ANSWER IS GOING SOMEWHERE A PICTURE CAN FOLLOW."""
    global carrying

    carrying = []


def closed():
    """WHAT THE TURN HANDED OVER, AND THE END OF ANYTHING BEING ABLE TO."""
    global carrying

    found, carrying = carrying or [], None

    return found


def wanted():
    """TRUE WHEN THERE IS SOMEBODY TO SHOW SOMETHING TO."""
    return carrying is not None


def offer(path):
    """LEAVE A PICTURE FOR THE ANSWER TO CARRY. FALSE WHEN IT WILL NOT BE TAKEN."""
    if carrying is None or len(carrying) >= MOST:
        return False

    carrying.append(Path(path))

    return True
