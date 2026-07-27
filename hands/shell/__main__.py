"""ONE COMMAND STRAIGHT THROUGH THE TOOL: python -m hands.shell "ls ~" """

import sys

from hands.shell.tools import run_command

print(run_command.invoke({"command": " ".join(sys.argv[1:]) or "echo hello && pwd"}))
