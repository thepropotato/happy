"""Every action Happy can take, described once and handed to whichever brain is in charge."""

import asyncio
import contextvars
import inspect
import json
import re
import types
import typing
from dataclasses import dataclass, field
from typing import Annotated, Any, Callable, Literal, get_args, get_origin


@dataclass
class Image:
    png: bytes
    note: str = ""


@dataclass
class Tool:
    name: str
    fn: Callable
    description: str
    schema: dict
    say: str = ""
    label: str = ""
    local_only: bool = False
    needs: Callable | None = None
    check: Callable | None = None
    params: dict = field(default_factory=dict)

    def ready(self):
        return self.needs is None or bool(self.needs())

    def refuse(self, args):
        """Why these arguments are turned away before anything is drawn, or None to go ahead."""
        return self.check(args) if self.check else None

    def show(self, args):
        try:
            return (self.label or self.name.replace("_", " ")).format(**{k: v for k, v in args.items() if v not in (None, "")})
        except (KeyError, IndexError):
            return self.name.replace("_", " ")


REGISTRY: dict[str, Tool] = {}
reporter: contextvars.ContextVar[Callable[[str], None] | None] = contextvars.ContextVar("reporter", default=None)
# WHAT THE PERSON SAID THIS TURN, FOR A TOOL THAT MUST NOT GO BEYOND IT; None WHEN THE BACKEND CANNOT SAY.
asked: contextvars.ContextVar[str | None] = contextvars.ContextVar("asked", default=None)
# WHAT EVERY TOOL HANDED BACK THIS TURN, SO A NAME A TOOL SHOWED COUNTS AS KNOWN.
seen: contextvars.ContextVar[list | None] = contextvars.ContextVar("seen", default=None)
GENERIC = {"the", "a", "an", "my", "this", "that", "file", "folder", "document", "doc", "of", "in", "on", "for", "and",
           "pdf", "txt", "docx", "xlsx", "pptx", "png", "jpg", "jpeg", "md", "csv", "zip", "json"}


def said_lately():
    """What the person said this turn and the exchange just before it, or None when the backend cannot say."""
    from happy import history

    words = asked.get()
    if words is None:
        return None
    # THIS TURN'S REQUEST AND THE ONE BEFORE, SO "YES" TO "SEND IT TO JANE?" OR "TELL HER" STILL NAMES HER.
    return " ".join([words] + [f"{turn['request']} {turn['reply']}" for turn in history.recent(limit=2)]).lower()


def named_file(args):
    """A file name nobody gave: not in what they said lately, not a real path, and not in anything a tool showed this turn."""
    from pathlib import Path

    what = (args.get("what") or "").strip().strip('"')
    said = said_lately()
    if said is None or not what or Path(what).expanduser().exists():
        return None
    known = said + " " + " ".join(seen.get() or []).lower()
    words = [w for w in re.split(r"[^\w']+", what.lower()) if w and w not in GENERIC]
    if all(w in known for w in words):
        return None
    # A NAME THE MODEL MADE UP SENT IT LOOKING FOR A "WHATSAPP CHAT LOG" IT ALREADY HELD, THEN TO SAY IT COULD NOT READ WHATSAPP.
    return (f"Error: no file was looked for: nobody named a file called {what}, and no tool showed one. "
            "Do not guess at files. Answer from what your tools already gave you, or ask which file they mean.")


def report(text):
    """Lets a long-running tool tell the person how it is getting on."""
    hook = reporter.get()
    if hook:
        hook(text)


def json_type(hint):
    origin = get_origin(hint)
    if origin is Annotated:
        base, *meta = get_args(hint)
        out = json_type(base)
        notes = [m for m in meta if isinstance(m, str)]
        if notes:
            out["description"] = notes[0]
        return out
    if origin is Literal:
        return {"type": "string", "enum": list(get_args(hint))}
    if origin in (typing.Union, types.UnionType):
        options = [a for a in get_args(hint) if a is not type(None)]
        return json_type(options[0])
    if origin in (list, tuple):
        inner = get_args(hint)
        return {"type": "array", "items": json_type(inner[0]) if inner else {"type": "string"}}
    return {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        dict: {"type": "object"},
    }.get(hint, {"type": "string"})


def schema_of(fn):
    hints = typing.get_type_hints(fn, include_extras=True)
    props, required = {}, []
    for name, param in inspect.signature(fn).parameters.items():
        props[name] = json_type(hints.get(name, str))
        if param.default is inspect.Parameter.empty:
            required.append(name)
    return {"type": "object", "properties": props, "required": required}


def tool(say="", label="", local_only=False, needs=None, check=None):
    """Registers a function as a tool; its docstring is what the model reads."""

    def wrap(fn):
        doc = inspect.cleandoc(fn.__doc__ or fn.__name__)
        schema = schema_of(fn)
        REGISTRY[fn.__name__] = Tool(
            name=fn.__name__, fn=fn, description=doc, schema=schema, say=say, label=label,
            local_only=local_only, needs=needs, check=check, params=schema["properties"],
        )
        return fn

    return wrap


def coerce(value, spec):
    """Turns what a small model wrote into what the function expects."""
    kind = spec.get("type")
    if value is None:
        return None
    if kind == "integer":
        if isinstance(value, str):
            value = value.strip().rstrip("%").strip()
        return int(round(float(value)))
    if kind == "number":
        return float(str(value).rstrip("%"))
    if kind == "boolean":
        if isinstance(value, str):
            return value.strip().lower() in ("true", "yes", "1", "on")
        return bool(value)
    if kind == "array":
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                value = parsed if isinstance(parsed, list) else [parsed]
            except json.JSONDecodeError:
                value = [part.strip() for part in value.split(",") if part.strip()]
        return [coerce(v, spec.get("items", {})) for v in value]
    if kind == "string":
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        value = str(value)
        if "enum" in spec and value not in spec["enum"]:
            lowered = {e.lower(): e for e in spec["enum"]}
            if value.lower() not in lowered:
                raise ValueError(f"must be one of {spec['enum']}")
            value = lowered[value.lower()]
        return value
    return value


def prepare(tool_, args):
    args = dict(args or {})
    clean = {}
    for name, spec in tool_.params.items():
        if name in args and args[name] not in (None, ""):
            try:
                clean[name] = coerce(args[name], spec)
            except (TypeError, ValueError) as error:
                raise ValueError(f"{name}: {error}") from None
    missing = [n for n in tool_.schema["required"] if n not in clean]
    if missing:
        raise ValueError(f"missing {', '.join(missing)}")
    return clean


async def call(name, args):
    """Runs a tool and always comes back with something the model can read."""
    tool_ = REGISTRY.get(name)
    if tool_ is None:
        return f"Error: there is no tool called {name}."
    refused = tool_.refuse(args)
    if refused:
        return refused
    try:
        clean = prepare(tool_, args)
    except ValueError as error:
        return f"Error: bad arguments for {name} ({error}). Call it again with fixed arguments."
    try:
        if inspect.iscoroutinefunction(tool_.fn):
            result = await tool_.fn(**clean)
        else:
            result = await asyncio.to_thread(tool_.fn, **clean)
    except Exception as error:
        return f"Error: {name} failed: {error}"
    shown = seen.get()
    if shown is not None:
        shown.append(str(getattr(result, "note", result)))
    return "Done." if result is None else result


def available(local=True):
    """The tools that can run right now, for the given kind of brain."""
    load()
    return [t for t in REGISTRY.values() if t.ready() and (local or not t.local_only)]


def load():
    from happy.tools import apps, browser, coding, controls, downloads, files, notes, other_mcps, reminders, routines, screen, status, weather, web, whatsapp  # noqa: F401
