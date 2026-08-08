# RULES FOR WRITING CODE

## Comments

- Write as few comments as possible. Most code needs none.
- A comment earns its place only when it says *why*, and only when the code cannot. Never
  restate what the line already says.
- Keep every comment to one line where you can, two at the most. No essays, no paragraphs of
  prose above a function, no decorative banners.
- Use only uppercase letters for comments.
- A module gets one short docstring saying what it owns. A function gets one only when its
  name is not enough.
- Tool docstrings are the exception: they are the prompt the model reads, so they are written
  as plain prose for a reader, not as comments.

## Structure

- Every module is a folder with an `__init__.py`, never a bare file at the top level.
- The folders are named after a person: `brain` thinks, `ears` hear, `voice` speaks, `eyes`
  see, `hands` do, `memory` remembers, `face` shows. A new capability gets the name of the
  part of a person that would do it.
- `mcps` is the one deliberate exception, and it stays one. It holds connections to MCP
  servers that are not on this machine, and a body part would hide what they actually are.
  It cannot be `mcp`, which would shadow the installed SDK, nor `tools`, which collides with
  `hands.tools()`. Do not rename it back.
- No file may be longer than 200 lines. Split it by job, not by size.
- Modularity is the most important thing. DO NOT use provider specific terms. Each
  class/interface should be named after their job, not their provider or something.
- DO NOT use `_` (underscore) prefixes for naming variables and functions.

## Behaviour

- Every feature we build should be compatible with both Windows and macOS. A control written
  for one system is not finished until the other one is beside it.
- A tool returns short, plain text. Whatever it returns may end up spoken out loud.
