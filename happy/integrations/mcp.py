"""MCP servers Happy talks to: WhatsApp, plus whatever the person already set up for other agents."""

import asyncio
import base64
import logging
import os
import time

from happy import paths
from happy.tools import Image

log = logging.getLogger("happy.mcp")
logging.getLogger("mcp.client.auth").setLevel(logging.CRITICAL)


def render(result):
    """An MCP tool result as text, or as an Image when the server sent a picture."""
    texts, picture = [], None
    for block in getattr(result, "content", None) or []:
        kind = getattr(block, "type", "")
        if kind == "text":
            texts.append(block.text)
        elif kind == "image" and picture is None:
            picture = base64.b64decode(block.data)
        elif kind == "resource" and getattr(block.resource, "text", None):
            texts.append(block.resource.text)
    text = "\n".join(texts).strip() or ("Done." if not getattr(result, "is_error", False) else "It failed.")
    if getattr(result, "is_error", False):
        text = "Error: " + text
    return Image(picture, text) if picture else text


class Server:
    def __init__(self, name, spec, source):
        self.name = name
        self.spec = spec
        self.source = source
        self.client = None
        self.tools = []
        self.error = ""
        self.task = None
        self.ready = None
        self.closing = None
        self.tried = 0.0
        self.interactive = False

    def target(self):
        """A remote server with its headers and sign-in, or a process whose chatter goes to a log instead of the terminal."""
        from mcp import StdioServerParameters
        from mcp.client.stdio import stdio_client

        if self.spec.get("url"):
            import httpx2
            from mcp.client.streamable_http import streamable_http_client

            from happy.integrations import oauth

            client = httpx2.AsyncClient(auth=oauth.provider(self.name, self.spec["url"], self.interactive),
                                        headers=self.spec.get("headers") or {}, follow_redirects=True,
                                        timeout=httpx2.Timeout(30, read=300))
            return streamable_http_client(self.spec["url"], http_client=client)
        env = {**os.environ, **(self.spec.get("env") or {})}
        env.pop("ELECTRON_RUN_AS_NODE", None)
        params = StdioServerParameters(command=self.spec["command"], args=self.spec.get("args") or [],
                                       env=env, cwd=self.spec.get("cwd"))
        paths.HOME.mkdir(parents=True, exist_ok=True)
        return stdio_client(params, errlog=open(paths.HOME / "mcp-servers.log", "a"))

    async def run(self):
        from mcp import Client

        try:
            async with Client(self.target()) as client:
                self.client = client
                self.tools = (await client.list_tools()).tools
                self.ready.set()
                await self.closing.wait()
        except asyncio.CancelledError:
            self.error = "stopped"
        except BaseException as error:
            while isinstance(error, BaseExceptionGroup) and error.exceptions:
                error = error.exceptions[0]
            from happy.integrations.oauth import NeedsSignIn

            self.error = "needs sign-in" if isinstance(error, NeedsSignIn) else str(error) or type(error).__name__
            log.info("%s did not connect: %s", self.name, self.error)
        finally:
            self.client = None
            self.ready.set()

    async def connect(self, timeout=25):
        """Connects once; a server that failed is tried again after a short while, so a new sign-in is picked up."""
        stale = self.task is not None and self.task.done() and self.client is None and time.monotonic() - self.tried > 15
        if self.task is None or stale:
            self.ready, self.closing = asyncio.Event(), asyncio.Event()
            self.error = ""
            self.tried = time.monotonic()
            self.task = asyncio.create_task(self.run())
        try:
            await asyncio.wait_for(self.ready.wait(), timeout)
        except asyncio.TimeoutError:
            self.error = "took too long to start"
        return self.client is not None

    async def sign_in(self):
        """Signs in through the browser, on screen, then connects with the new sign-in."""
        await self.close()
        self.task, self.client, self.interactive = None, None, True
        try:
            return await self.connect(timeout=320)
        finally:
            self.interactive = False

    async def call(self, tool, args, timeout=180):
        if not await self.connect():
            return f"Error: {self.name} is not available ({self.error})."
        try:
            result = await self.client.call_tool(tool, args or {}, read_timeout_seconds=timeout)
        except Exception as error:
            return f"Error: {self.name} {tool} failed: {error}"
        return render(result)

    async def close(self):
        if self.closing:
            self.closing.set()
        if self.task:
            try:
                await asyncio.wait_for(self.task, 5)
            except (asyncio.TimeoutError, Exception):
                self.task.cancel()


class Hub:
    def __init__(self):
        self.servers: dict[str, Server] = {}

    def add(self, name, spec, source):
        if name not in self.servers:
            self.servers[name] = Server(name, spec, source)

    def get(self, name):
        return self.servers.get(name)

    def inherited(self):
        return [s for s in self.servers.values() if s.source != "happy"]

    async def call(self, server, tool, args, timeout=180):
        found = self.servers.get(server)
        if not found:
            return f"Error: no service called {server} is connected."
        return await found.call(tool, args, timeout)

    async def close(self):
        await asyncio.gather(*(s.close() for s in self.servers.values()), return_exceptions=True)


hub = Hub()
