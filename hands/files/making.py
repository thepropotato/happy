"""THE TOOLS THAT PUT WORDS ON THE DISK, AND THE ONE THAT READS A WHOLE PROJECT FIRST."""

from pathlib import Path

from langchain_core.tools import tool

from hands import reasons
from hands.files import briefing
from hands.files.finding import locate

EXISTS = (
    "{path} already exists, so nothing was written. To change it, read it and use edit_file. "
    "To make something new, pick a name that is not taken."
)

NOWHERE = "The folder {folder} does not exist, so there is nowhere to put {name}."

MISSING = (
    "The text to replace is not in {name}, so nothing was changed. Read the file and give the "
    "exact words as they appear."
)

SEVERAL = (
    "Those words appear {count} times in {name}, so nothing was changed. Give a longer stretch "
    "that appears only once."
)


@tool
def describe_project(project: str) -> str:
    """Understand a project folder before saying or writing anything about it:
    where it is, how many files and in what languages, what it starts from, what
    is inside at the top level, what its README says, and the first thing each
    main source file says about itself.

    Call this first whenever you are asked to document, describe, explain,
    summarise or write about a project, a repository or a codebase, and before
    build for work on one. Give it the project's name, like "untitled", or its
    path. Do not list folders and read files one at a time to piece this together
    yourself: this is the whole picture in one call."""
    lines, complaint = briefing.brief(project)

    if lines is None:
        return reasons.no(complaint)

    return "\n".join(lines)


@tool
def write_file(path: str, text: str) -> str:
    """Create a new file with exactly this text in it. Give the full path,
    including the name, like "~/Desktop/projects/untitled/docs.md". This only
    ever creates: if something is already at that path it refuses and nothing is
    touched, so it can never wipe out somebody's work. To change a file that
    exists, use edit_file. Never write a file with run_command."""
    where = Path(path).expanduser()

    if where.exists():
        return reasons.no(EXISTS.format(path=where))

    if not where.parent.is_dir():
        return reasons.no(NOWHERE.format(folder=where.parent, name=where.name))

    try:
        where.write_text(text, encoding="utf-8")
    except OSError as error:
        return reasons.no(f"Could not write {where.name}: {error}")

    return f"Wrote {where} ({len(text.splitlines())} lines)."


@tool
def edit_file(path: str, find: str, replace: str) -> str:
    """Change part of a file that exists: the exact text in "find" is swapped for
    "replace", once. Read the file first so "find" is copied from it word for
    word; if it is not there, or is there more than once, nothing changes and
    this says so. To add to the end, make "find" the last line and "replace" that
    line plus the new ones. To create a file, use write_file instead."""
    found, note = locate(path)

    if found is None:
        return reasons.no(note)

    if found.is_dir():
        return reasons.no(f"{found} is a folder, not a file.")

    try:
        text = found.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return reasons.no(f"Could not read {found.name}: {error}")

    count = text.count(find) if find else 0

    if count == 0:
        return reasons.no(MISSING.format(name=found.name))

    if count > 1:
        return reasons.no(SEVERAL.format(count=count, name=found.name))

    try:
        found.write_text(text.replace(find, replace, 1), encoding="utf-8")
    except OSError as error:
        return reasons.no(f"Could not write {found.name}: {error}")

    return f"Changed {found}."


TOOLS = [describe_project, write_file, edit_file]
