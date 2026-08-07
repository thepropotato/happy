"""THE LOG AS A PAGE A BROWSER CAN OPEN.

data/happy.log IS THE REAL THING AND THIS IS ONLY A READER FOR IT: THE SAME
LINES, COLOURED BY KIND, WITH SOMEWHERE TO SEARCH THEM. ANYBODY WHO WOULD RATHER
tail -f IT SHOULD, AND NOTHING HERE IS IN THEIR WAY.

A SNAPSHOT AND NOT A WINDOW ONTO THE FILE. WRITING ONE PAGE COSTS NOTHING AND
LEAVES NOTHING LISTENING ON A PORT FOR THE REST OF THE SESSION.
"""

import json
from datetime import datetime
from pathlib import Path

from memory import storage

HERE = Path(__file__).resolve().parent

TEMPLATE = HERE / "viewer.html"
STYLE = HERE / "viewer.css"

PAGE = "logs.html"

LOGS = "__LOGS__"
SHEET = "__STYLE__"

# A </script> INSIDE THE JSON WOULD CLOSE THE TAG THE JSON IS SITTING IN. \/ IS
# AN ESCAPE JSON ALREADY UNDERSTANDS, SO IT PARSES BACK TO THE SAME STRING.
ENDING = ("</", "<\\/")


def gathered():
    """EVERY LINE OF THE LOG, OLDEST FIRST, WITH WHAT THE PAGE NEEDS TO HEAD ITSELF."""
    from face import log

    return {
        "written": datetime.now().astimezone().strftime("%d %b %Y, %H:%M"),
        "file": str(log.FILE),
        "lines": log.lines(),
    }


def written(folder=None):
    """THE PAGE, WRITTEN FRESH. RETURNS IT FOR SOMETHING TO OPEN."""
    where = Path(folder) if folder else storage.path().parent
    where.mkdir(parents=True, exist_ok=True)

    page = where / PAGE

    filled = TEMPLATE.read_text(encoding="utf-8").replace(SHEET, STYLE.read_text(encoding="utf-8"))
    page.write_text(filled.replace(LOGS, inlined(gathered())), encoding="utf-8")

    return page


def inlined(logs):
    """THE LOG AS IT GOES INTO THE PAGE: TIGHT, AND SAFE INSIDE A SCRIPT TAG."""
    return json.dumps(logs, default=str, separators=(",", ":")).replace(*ENDING)


if __name__ == "__main__":
    print(written())
