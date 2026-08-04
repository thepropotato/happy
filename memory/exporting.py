"""EVERY EXCHANGE AS A PAGE A BROWSER CAN OPEN, AND THE JSON UNDER IT.

THE PANEL SHOWS THE LAST FEW TURNS IN A COLUMN THE WIDTH OF A PHONE. WHY A TURN
WENT THE WAY IT DID IS NOT READABLE THERE: THAT IS EVERY CALL'S ARGUMENTS AND
EVERYTHING THAT CAME BACK, LAID OUT WITH SOMEWHERE TO SEARCH THEM.

A SNAPSHOT AND NOT A WINDOW ONTO THE DATABASE. WRITING TWO FILES COSTS NOTHING
AND LEAVES NOTHING LISTENING ON A PORT FOR THE REST OF THE SESSION.
"""

import json
from datetime import datetime
from pathlib import Path

from memory import conversation, storage

HERE = Path(__file__).resolve().parent

TEMPLATE = HERE / "viewer.html"
STYLE = HERE / "viewer.css"

PAGE = "logs.html"
DATA = "logs.json"

LOGS = "__LOGS__"
SHEET = "__STYLE__"

# A </script> INSIDE THE JSON WOULD CLOSE THE TAG THE JSON IS SITTING IN. \/ IS
# AN ESCAPE JSON ALREADY UNDERSTANDS, SO IT PARSES BACK TO THE SAME STRING.
ENDING = ("</", "<\\/")


def gathered():
    """EVERY EXCHANGE, OLDEST FIRST, WITH WHAT THE PAGE NEEDS TO HEAD ITSELF."""
    return {
        "written": datetime.now().astimezone().strftime("%d %b %Y, %H:%M"),
        "database": str(storage.path()),
        "turns": conversation.history(),
    }


def written(folder=None):
    """BOTH FILES, WRITTEN FRESH. RETURNS THE PAGE FOR SOMETHING TO OPEN."""
    where = Path(folder) if folder else storage.path().parent
    where.mkdir(parents=True, exist_ok=True)

    logs = gathered()
    page = where / PAGE

    (where / DATA).write_text(json.dumps(logs, indent=2, default=str), encoding="utf-8")

    filled = TEMPLATE.read_text(encoding="utf-8").replace(SHEET, STYLE.read_text(encoding="utf-8"))
    page.write_text(filled.replace(LOGS, inlined(logs)), encoding="utf-8")

    return page


def inlined(logs):
    """THE DATA AS IT GOES INTO THE PAGE: TIGHT, AND SAFE INSIDE A SCRIPT TAG."""
    return json.dumps(logs, default=str, separators=(",", ":")).replace(*ENDING)


if __name__ == "__main__":
    print(written())
