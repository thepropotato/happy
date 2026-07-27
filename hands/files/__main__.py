"""FIND AND READ ONE FILE: python -m hands.files resume"""

import sys

from hands.files.tools import read_file

print(read_file.invoke({"path": " ".join(sys.argv[1:]) or "~/.zshrc"})[:2000])
