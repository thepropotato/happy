"""THE GOOGLE SERVER, STARTED.

MAIL, CALENDAR AND DRIVE LIVE BESIDE THIS FILE AND ARE PULLED IN FOR THEIR
DECORATORS, WHICH IS THE ONLY REASON THEY ARE IMPORTED AND NEVER NAMED AGAIN.
"""

import sys
from pathlib import Path

# LEFT ON THE PATH, calendar.py BESIDE THIS FILE ANSWERS EVERY import calendar IN
# THE PROCESS, AND THE FOLDER ITSELF SWALLOWS THE REAL google.auth.
sys.path[0] = str(Path(__file__).resolve().parents[2])

from servers.google import calendar, drive, mail, mcp  # noqa: E402, F401

if __name__ == "__main__":
    mcp.run()
