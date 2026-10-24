"""The agent: the model backends, and the events a turn reports while it runs."""

from dataclasses import dataclass, field


@dataclass
class Text:
    delta: str


@dataclass
class Act:
    tool: str
    args: dict = field(default_factory=dict)
    label: str = ""
    say: str = ""


@dataclass
class Acted:
    tool: str
    result: str = ""
    ok: bool = True


@dataclass
class Problem:
    message: str


class Backend:
    """A model to think with: Claude through Claude Code, or any OpenAI-shaped endpoint."""

    name = "brain"
    sees = False

    async def start(self):
        pass

    async def turn(self, text, emit):
        """Handles one request, reporting Text, Act and Acted events through emit."""
        raise NotImplementedError

    async def interrupt(self):
        pass

    async def reset(self):
        pass

    async def close(self):
        pass
