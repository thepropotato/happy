"""ONE LIVE CONNECTION TO ONE SERVER, HELD OPEN BETWEEN CALLS.

OPENING COSTS A HANDSHAKE OR A WHOLE PROCESS, WHICH IS MOST OF A SECOND, AND
DOING THAT PER CALL WOULD BE HEARD. SO EACH CONNECTION GETS A TASK THAT OPENS IT
AND THEN SITS ON AN EVENT UNTIL SOMEBODY ASKS IT TO GO. THE TASK HAS TO BE THE
ONE THAT CLOSES IT TOO: THE TRANSPORTS ARE ANYIO SCOPES, AND A SCOPE LEFT BY A
DIFFERENT TASK THAN ENTERED IT IS AN ERROR.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import timedelta

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.exceptions import McpError

GOODBYE_SECONDS = 2

# WHAT THE PROTOCOL RECOMMENDS: THIRTY SECONDS, AND REDIRECTS FOLLOWED.
PATIENCE = httpx.Timeout(30, read=60 * 5)


class Unreachable(Exception):
    """THE SERVER DID NOT COME UP. THE REASON IS WHAT A PERSON SHOULD HEAR."""


@asynccontextmanager
async def carrying(address, headers=None, auth=None):
    """THE HTTP CLIENT AND THE TRANSPORT ON TOP OF IT, OPENED AND CLOSED TOGETHER.

    THE CLIENT IS MADE IN HERE SO THE TASK THAT OPENS IT IS THE ONE THAT SHUTS
    IT. HANDING IN A READY MADE ONE LEAKS A CONNECTION POOL PER RECONNECT.
    """
    async with httpx.AsyncClient(
        headers=headers, auth=auth, timeout=PATIENCE, follow_redirects=True
    ) as client:
        async with streamable_http_client(address, http_client=client) as streams:
            yield streams


def remote(address, headers=None, auth=None):
    """A SERVER SOMEWHERE ELSE. auth IS WHERE A SIGN IN LIVES, WHEN THERE IS ONE."""
    return lambda: carrying(address, headers, auth)


def local(command, arguments=None, environment=None):
    """A SERVER THAT IS A PROGRAM ON THIS MACHINE, TALKED TO OVER ITS PIPES."""
    settings = StdioServerParameters(
        command=command, args=list(arguments or []), env=environment
    )

    return lambda: stdio_client(settings)


class Session:
    """A CONNECTION AND WHAT IT TAKES TO GET IT BACK WHEN IT DROPS."""

    def __init__(self, name, opening, timeout=20):
        self.name = name
        self.opening = opening
        self.timeout = timeout

        self.session = None
        self.trouble = None
        self.task = None
        self.ready = None
        self.closing = None

    def up(self):
        return self.session is not None

    async def serve(self):
        """THE TASK THAT OWNS THE CONNECTION FOR ITS WHOLE LIFE."""
        try:
            async with self.opening() as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()

                    self.session = session
                    self.trouble = None
                    self.ready.set()

                    await self.closing.wait()
        except Exception as error:
            self.trouble = error
        finally:
            self.session = None

            # SET EVEN WHEN IT FAILED, SO NOBODY WAITS OUT THE TIMEOUT FOR A
            # CONNECTION THAT IS ALREADY KNOWN NOT TO BE COMING.
            if self.ready is not None:
                self.ready.set()

    async def open(self):
        """UP AND SHAKEN HANDS WITH, OR Unreachable."""
        if self.up():
            return self.session

        if self.task is None or self.task.done():
            self.ready = asyncio.Event()
            self.closing = asyncio.Event()
            self.task = asyncio.create_task(self.serve(), name=f"mcps:{self.name}")

        try:
            await asyncio.wait_for(self.ready.wait(), self.timeout)
        except TimeoutError:
            await self.close()

            raise Unreachable(f"{self.name} did not answer in time") from None

        if not self.up():
            raise Unreachable(f"{self.name} could not be reached") from self.trouble

        return self.session

    async def close(self):
        """LET THE OWNING TASK OUT OF ITS SCOPES, AND WAIT WHILE IT DOES."""
        task = self.task
        self.task = None

        if self.closing is not None:
            self.closing.set()

        if task is not None and not task.done():
            try:
                await asyncio.wait_for(task, GOODBYE_SECONDS)
            except (TimeoutError, asyncio.CancelledError, Exception):
                pass

        self.session = None

    async def listing(self):
        """EVERY TOOL THIS SERVER OFFERS."""
        session = await self.open()
        found = await session.list_tools()

        return found.tools

    async def call(self, name, arguments):
        session = await self.open()
        waiting = timedelta(seconds=self.timeout)

        try:
            return await session.call_tool(name, arguments, read_timeout_seconds=waiting)
        except McpError:
            raise  # THE SERVER ANSWERED AND SAID NO. RECONNECTING WOULD NOT CHANGE IT.
        except Exception:
            # ONE RECONNECT, NEVER TWO. THE SECOND WAIT IS LONGER THAN A PERSON
            # WILL STAND THERE FOR, AND PLAIN TEXT BACK IS BETTER THAN SILENCE.
            await self.close()

            session = await self.open()

            return await session.call_tool(name, arguments, read_timeout_seconds=waiting)
