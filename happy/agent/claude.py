"""Claude as the brain, through the person's own Claude Code login, with their MCP servers and connectors."""

import base64
import json
import logging
import os
import shutil
import time

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, PermissionResultAllow,
                              PermissionResultDeny, ResultMessage, StreamEvent, SystemMessage, ToolResultBlock,
                              ToolUseBlock, UserMessage, create_sdk_mcp_server, tool as sdk_tool)
from posthog.ai.claude_agent_sdk import PostHogClaudeSDKClient

from happy import paths, tools
from happy.agent import Act, Acted, Backend, Problem, Text
from happy.agent.prompt import stamped, system_prompt
from happy.integrations import discovered
from happy.observability import new_session_id
from happy.tools import Image

log = logging.getLogger("happy.agent")

FORGET_AFTER = 15 * 60
SESSION = paths.HOME / "claude-session.json"
BUILT_IN = ["WebSearch", "WebFetch", "Read", "Glob", "Grep"]
NEVER = {"Bash", "Write", "Edit", "MultiEdit", "NotebookEdit", "KillShell", "BashOutput"}
LABELS = {"WebSearch": ("Searching the web", "Searching the web."), "WebFetch": ("Reading a page", ""),
          "Read": ("Reading a file", ""), "Glob": ("Looking for files", ""), "Grep": ("Searching files", "")}
SPOKEN = {"whatsapp": "Checking WhatsApp.", "gmail": "Checking your mail.", "calendar": "Checking your calendar.",
          "drive": "Looking in your Drive.", "slack": "Checking Slack.", "linear": "Checking Linear."}


GUIDE = """

The 'happy' tools work this computer. Other connected services are yours to use too.
To find a piece of information somewhere in WhatsApp (an address, a number, a link, details someone sent), use whatsapp_find first: the WhatsApp server's own searches only see the latest 50 messages."""


def describe(name):
    """A label and a lead-in for a tool Claude Code runs itself."""
    if name in LABELS:
        return LABELS[name]
    parts = name.split("__")
    server = parts[1] if len(parts) > 2 else name
    action = parts[-1].replace("_", " ")
    shown = server.replace("claude_ai_", "").replace("_", " ").title()
    say = next((line for key, line in SPOKEN.items() if key in server.lower()), "")
    return f"{shown}: {action}", say


def available():
    return bool(shutil.which("claude"))


class Claude(Backend):
    sees = True

    def __init__(self, cfg, extra_servers=None, posthog_client=None, ai_session_id=None):
        self.cfg = cfg
        self.model = cfg.get("brain.model") or "sonnet"
        self.name = f"Claude ({self.model})"
        self.extra_servers = extra_servers or {}
        self.posthog_client = posthog_client
        self.ai_session_id = ai_session_id or new_session_id("happy")
        self.client = None
        self.emit = lambda event: None
        self.last = 0.0
        self.resuming = None
        saved = self.saved()
        if saved and time.time() - saved["at"] < FORGET_AFTER:
            self.resuming, self.last = saved["id"], saved["at"]
        self.running = {}

    def wrap(self, registered):
        async def handler(args):
            refused = registered.refuse(args)
            if refused:
                self.emit(Acted(registered.name, refused, False))
                return {"content": [{"type": "text", "text": refused}], "is_error": True}
            self.emit(Act(registered.name, args, registered.show(args), registered.say))
            result = await tools.call(registered.name, args)
            if isinstance(result, Image):
                self.emit(Acted(registered.name, result.note))
                content = [{"type": "image", "data": base64.b64encode(result.png).decode(), "mimeType": "image/png"}]
                if result.note:
                    content.append({"type": "text", "text": result.note})
                return {"content": content}
            text = str(result)
            self.emit(Acted(registered.name, text, not text.startswith("Error")))
            return {"content": [{"type": "text", "text": text}], "is_error": text.startswith("Error")}

        return sdk_tool(registered.name, registered.description, registered.schema)(handler)

    def options(self):
        own = create_sdk_mcp_server("happy", tools=[self.wrap(t) for t in tools.available(local=False)])
        servers = {"happy": own}
        known = discovered.claude_code()
        for name, spec in self.extra_servers.items():
            if name in known or spec.get("codex_only"):
                continue
            if spec.get("url"):
                servers[name] = {"type": "http", "url": spec["url"], **({"headers": spec["headers"]} if spec.get("headers") else {})}
            else:
                servers[name] = {"type": "stdio", "command": spec["command"], "args": spec.get("args") or [],
                                 "env": spec.get("env") or {}}
        return ClaudeAgentOptions(
            system_prompt=system_prompt(self.cfg) + GUIDE,
            mcp_servers=servers,
            tools=BUILT_IN,
            can_use_tool=self.permit,
            setting_sources=["user"],
            include_partial_messages=True,
            model=self.model,
            effort=self.cfg.get("brain.effort") or "low",
            cwd=os.path.expanduser("~"),
            cli_path=shutil.which("claude"),
            resume=self.resuming,
        )

    @staticmethod
    def saved():
        """The last conversation's session, so a restart within a few minutes carries on from it."""
        try:
            return json.loads(SESSION.read_text())
        except (OSError, ValueError):
            return None

    @staticmethod
    def keep(session):
        if session:
            SESSION.parent.mkdir(parents=True, exist_ok=True)
            SESSION.write_text(json.dumps({"id": session, "at": time.time()}))

    async def permit(self, name, args, context):
        if name in NEVER:
            return PermissionResultDeny(message="Happy does not change files or run commands itself; hand coding work off instead.")
        return PermissionResultAllow()

    async def start(self):
        if self.client is None:
            if self.posthog_client:
                self.client = PostHogClaudeSDKClient(
                    self.options(),
                    posthog_client=self.posthog_client,
                    posthog_properties={"$ai_session_id": self.ai_session_id},
                    posthog_privacy_mode=False,
                )
            else:
                self.client = ClaudeSDKClient(options=self.options())
            await self.client.connect()

    async def reset(self):
        if self.client is not None:
            try:
                await self.client.disconnect()
            except Exception:
                pass
            self.client = None

    async def refresh(self):
        # A SYSTEM PROMPT IS FIXED FOR A SESSION, SO THE SAME CONVERSATION IS RESUMED UNDER THE NEW ONE.
        saved = self.saved()
        self.resuming = saved["id"] if saved and time.time() - saved["at"] < FORGET_AFTER else None
        await self.reset()

    async def close(self):
        await self.reset()

    async def interrupt(self):
        if self.client is not None:
            try:
                await self.client.interrupt()
            except Exception:
                pass

    async def turn(self, text, emit):
        if time.time() - self.last > FORGET_AFTER:
            await self.reset()
            self.resuming = None
        self.last = time.time()
        await self.start()
        self.emit = emit
        said, streamed = [], False
        await self.client.query(stamped(text))
        async for message in self.client.receive_response():
            if isinstance(message, StreamEvent):
                event = message.event
                if event.get("type") == "content_block_start" and event.get("content_block", {}).get("type") == "text" and said:
                    emit(Text(" "))
                if event.get("type") == "content_block_delta" and event.get("delta", {}).get("type") == "text_delta":
                    streamed = True
                    said.append(event["delta"]["text"])
                    emit(Text(event["delta"]["text"]))
            elif isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, ToolUseBlock) and not block.name.startswith("mcp__happy__"):
                        label, say = describe(block.name)
                        self.running[block.id] = block.name
                        emit(Act(block.name, block.input, label, say))
                    elif hasattr(block, "text") and not streamed and block.text:
                        said.append(block.text)
                        emit(Text(block.text))
            elif isinstance(message, UserMessage) and isinstance(message.content, list):
                for block in message.content:
                    if isinstance(block, ToolResultBlock) and block.tool_use_id in self.running:
                        content = block.content if isinstance(block.content, str) else " ".join(
                            part.get("text", "") for part in block.content or [] if isinstance(part, dict))
                        emit(Acted(self.running.pop(block.tool_use_id), content or "", not block.is_error))
            elif isinstance(message, SystemMessage) and message.subtype == "init":
                from happy.integrations import status

                status.claude_servers = {s.get("name"): s.get("status") for s in message.data.get("mcp_servers", [])}
            elif isinstance(message, ResultMessage):
                self.keep(message.session_id)
                if message.is_error and not said:
                    emit(Problem(str(message.result or message.subtype)))
        self.emit = lambda event: None
        return "".join(said)
