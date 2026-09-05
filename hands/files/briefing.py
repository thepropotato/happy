"""WHAT A PROJECT IS, WORKED OUT FROM ITS FOLDER: ENOUGH TO SAY SOMETHING TRUE ABOUT IT IN ONE CALL."""

import re
from collections import Counter
from pathlib import Path

from hands.files.finding import dig
from hands.files.projects import looks, pick

SKIP = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next", "target"}

LANGUAGES = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript", ".jsx": "JavaScript",
    ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin", ".swift": "Swift", ".c": "C",
    ".cpp": "C++", ".h": "C", ".rb": "Ruby", ".php": "PHP", ".cs": "C#", ".md": "Markdown",
    ".html": "HTML", ".css": "CSS", ".sh": "Shell", ".ps1": "PowerShell", ".sql": "SQL",
}

READMES = ("README.md", "README.rst", "README.txt", "README", "readme.md")

ENTRIES = ("main.py", "app.py", "__main__.py", "index.js", "index.ts", "main.go", "main.rs", "src/main.rs", "cmd")

# THE FIRST THING A SOURCE FILE SAYS ABOUT ITSELF: A DOCSTRING OR A LEADING COMMENT.
OPENING = re.compile(r'^\s*(?:"""(.*?)"""|\'\'\'(.*?)\'\'\'|((?:\s*(?://|#)[^\n]*\n)+))', re.S)

DEPTH = 2
MOST_FILES = 40
MOST_SOURCES = 12
README_CHARS = 1200
OPENING_CHARS = 240


def brief(project):
    """THE WHOLE PICTURE AS LINES, OR None AND WHY WHEN THERE IS NO SUCH PROJECT."""
    root = where(project)

    if root is None:
        return None, f"Nothing here is a project or folder called {project}."

    files = sources(root)
    lines = [f"{root.name} at {root}" + (" (a git repository)" if (root / ".git").exists() else "")]
    lines.append(f"{len(files)} files" + (f", mostly {spoken(files)}" if files else ", none of them source code"))

    for name in ENTRIES:
        if (root / name).exists():
            lines.append(f"Starts from {name}")
            break

    lines.append("Inside: " + ", ".join(tree(root)))

    readme = about(root)

    if readme:
        lines.append(f"Its README says: {readme}")
    else:
        lines.append("It has no README.")

    for path in files[:MOST_SOURCES]:
        said = opening(path)

        if said:
            lines.append(f"{path.relative_to(root)}: {said}")

    return lines, None


def where(project):
    said = (project or "").strip()

    if not said:
        return None

    path = Path(said).expanduser()

    if path.is_dir():
        return path

    found = pick(said)

    return found if found is not None and found.is_dir() else None


def sources(root):
    """EVERY SOURCE FILE TO A SHALLOW DEPTH, BIGGEST FIRST, SO THE ONES THAT MATTER ARE READ."""
    found = []

    for path in walk(root, DEPTH):
        if path.suffix.lower() in LANGUAGES and path.suffix.lower() != ".md":
            found.append(path)

    return sorted(found, key=lambda each: each.stat().st_size, reverse=True)[:MOST_FILES]


def walk(root, depth):
    try:
        entries = sorted(root.iterdir(), key=lambda each: each.name.lower())
    except OSError:
        return

    for each in entries:
        if each.name.startswith(".") or each.name in SKIP:
            continue

        if each.is_file():
            yield each
        elif each.is_dir() and depth > 0:
            yield from walk(each, depth - 1)


def tree(root):
    """WHAT SITS AT THE TOP OF THE FOLDER, FOLDERS MARKED."""
    try:
        entries = sorted(root.iterdir(), key=lambda each: (not each.is_dir(), each.name.lower()))
    except OSError:
        return []

    return [f"{each.name}/" if each.is_dir() else each.name
            for each in entries if not each.name.startswith(".") and each.name not in SKIP]


def spoken(files):
    counted = Counter(LANGUAGES[each.suffix.lower()] for each in files)

    return " and ".join(name for name, _ in counted.most_common(2))


def about(root):
    for name in READMES:
        path = root / name

        if path.is_file():
            try:
                text = " ".join(path.read_text(encoding="utf-8", errors="replace").split())
            except OSError:
                continue

            return text[:README_CHARS] + ("..." if len(text) > README_CHARS else "")

    return ""


def opening(path):
    try:
        head = path.read_text(encoding="utf-8", errors="replace")[:4000]
    except OSError:
        return ""

    found = OPENING.match(head)

    if not found:
        return ""

    said = next((each for each in found.groups() if each), "")
    said = " ".join(re.sub(r"^\s*(//|#)\s?", "", said, flags=re.M).split())

    return said[:OPENING_CHARS] + ("..." if len(said) > OPENING_CHARS else "")
