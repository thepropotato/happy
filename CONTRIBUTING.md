# Contributing to Happy

Thanks for wanting to work on this. Two documents matter more than this one:

- **[AGENTS.md](AGENTS.md)** — how code in this repo is written. Read it before you write any.
- **[HAPPY.md](HAPPY.md)** — what every file owns, and why the shape is what it is. It records
  decisions that have already been made *and unmade*; a change that reverses one needs to
  answer the paragraph that made it.

## Getting set up

```sh
git clone https://github.com/thepropotato/happy.git
cd happy
./setup.sh          # setup.ps1 on Windows
python main.py
```

`setup.sh` finds a Python 3.11 or newer, makes the virtualenv, installs the requirements and
fetches the models. Everything it does lives in `bones/`, which needs only the standard library.

Useful while working:

- `python -m hands` prints exactly what the model was handed — every tool, grouped by module,
  with the description it actually reads. `--full` adds argument names, `--prompt` dumps the
  system prompt, and a bare word filters. When Happy reaches for the wrong tool, this is the
  honest place to look.
- `python -m ears`, `python -m voice`, `python -m eyes`, `python -m brain` each exercise their
  own module on its own.

## The rules that get a change turned down

These are not style preferences. Each one is load-bearing:

- **Both platforms, always.** A control written for macOS is not finished until the Windows one
  is beside it. A feature that works on one is not a feature yet.
- **No file over 200 lines.** Split it by job, not by size.
- **Every module is a folder** with an `__init__.py`, named after the part of a person that does
  the job. `mcps` is the one deliberate exception and stays one.
- **Comments are rare, one line, uppercase, and say *why*.** Tool docstrings are the exception —
  they are the prompt the model reads, so they are plain prose for a reader.
- **Never hand the model a fact.** The context is directions only. What is on screen, what time
  it is, what is playing — every one of those is fetched by a tool on the turn it is needed, or
  it is not known. Injecting a fetched fact to save a round trip has been tried and taken back
  out.
- **Nothing waits on a yes.** There is no confirmation layer, and adding one back is not a
  change we take.
- **A tool returns short, plain text**, because it may end up spoken out loud.
- **No provider names in class or interface names.** Name a thing after its job.
- **No `_` prefixes** on variables or functions.

## Adding a tool

1. Write `hands/yourthing/` as a folder with an `__init__.py`. Work in files named after what
   they do, tools in `tools.py`.
2. Decorate functions with `@tool` from `langchain_core.tools`. **The docstring is the prompt** —
   it is the only thing the model reads to decide whether to call you. Say when to use it *and
   when not to*, and give an example argument. It is the highest-leverage text in the folder.
3. Export `TOOLS = [...]` from the package.
4. Add the module to `MODULES` in `hands/__init__.py`.

That is the whole extension point. Check your work with `python -m hands yourthing`.

## Adding a service

Services that are not on this machine go in `mcps/servers/<name>/mcp_server.py` — the whole
server in one file unless it genuinely runs past 200 lines. Take credentials, HTTP and answers
from `servers.shared`, ask for the token *inside* each tool rather than above it, and add one
entry to `KNOWN` in `mcps/registry.py`. There is no fourth step; the row, its buttons and its
tools all appear from that entry.

**Happy writes every server it ships.** There is no way to add a server of your own by pasting
a URL or a command, and that is deliberate — see HAPPY.md. A pull request that adds one back
will not be taken.

## Pull requests

- Branch off `main`, one concern per pull request.
- Say what changed and why. If it undoes something HAPPY.md argues for, argue back in the
  description.
- Run it on your machine before opening. If you only have one of the two platforms, say so —
  somebody will check the other.
- Update HAPPY.md if you added, moved or removed a file. The layout table is meant to be true.

## Reporting things

Bugs and features go in [issues](https://github.com/thepropotato/happy/issues); the templates
ask for what is actually needed to reproduce something. Security problems do **not** go there —
see [SECURITY.md](SECURITY.md).

Everyone taking part is held to the [Code of Conduct](CODE_OF_CONDUCT.md).
