"""ONE RUNNING SERVER, HELD OPEN BETWEEN CALLS."""

import asyncio
import contextlib
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import McpError

GOODBYE_SECONDS = 2

WENT_QUIET = "{name} went quiet for {seconds:g} seconds"


class Alive:
    """HOW LONG SINCE A CALL LAST SHOWED A SIGN OF LIFE.

    THE TIMEOUT IS THERE TO CATCH A SERVER THAT HAS HUNG, AND AN ERRAND THAT IS
    STILL WORKING HAS NOT HUNG NO MATTER HOW LONG IT TAKES. SO THE CLOCK IS ON
    THE SILENCE AND NEVER ON THE LENGTH: EVERY WORD OUT OF THE SERVER PUTS THE
    WHOLE TIMEOUT BACK.
    """

    def __init__(self, patience):
        self.patience = patience
        self.spoke = time.monotonic()

    async def stirred(self, progress=None, total=None, message=None):
        """WHAT THE SERVER CALLS TO SAY IT IS STILL GOING."""
        self.spoke = time.monotonic()

    def left(self):
        return self.patience - (time.monotonic() - self.spoke)


class Unreachable(Exception):
    """THE SERVER DID NOT COME UP. THE REASON IS WHAT A PERSON SHOULD HEAR."""


def local(command, arguments=None, environment=None):
    """A SERVER THAT IS A PROGRAM ON THIS MACHINE, TALKED TO OVER ITS PIPES."""
    settings = StdioServerParameters(
        command=command, args=list(arguments or []), env=environment
    )

    return lambda: stdio_client(settings)


class Session:
    """A RUNNING SERVER AND WHAT IT TAKES TO GET IT BACK WHEN IT DIES."""

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
        """THE TASK THAT OWNS THE SERVER FOR ITS WHOLE LIFE."""
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

            # SET EVEN ON FAILURE: NOBODY SHOULD WAIT OUT THE TIMEOUT FOR A SERVER
            # ALREADY KNOWN NOT TO BE COMING.
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
            raise Unreachable(f"{self.name} could not be started") from self.trouble

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

        try:
            return await self.patiently(session, name, arguments)
        except (McpError, TimeoutError):
            raise  # THE SERVER ANSWERED AND SAID NO, OR STOPPED ANSWERING AT ALL.
        except Exception:
            # ONE RESTART, NEVER TWO: THE SECOND WAIT OUTLASTS ANYONE'S PATIENCE.
            await self.close()

            session = await self.open()

            return await self.patiently(session, name, arguments)

    async def patiently(self, session, name, arguments):
        """THE CALL, GIVEN THE WHOLE TIMEOUT BACK EVERY TIME IT SAYS IT IS STILL WORKING."""
        alive = Alive(self.timeout)
        work = asyncio.create_task(
            session.call_tool(name, arguments, progress_callback=alive.stirred)
        )

        while True:
            done, _ = await asyncio.wait({work}, timeout=max(alive.left(), 0))

            if done:
                return work.result()

            # IT SPOKE WHILE WE WERE SAT WAITING, SO THE WAIT STARTS OVER.
            if alive.left() > 0:
                continue

            work.cancel()

            with contextlib.suppress(BaseException):
                await work

            raise TimeoutError(WENT_QUIET.format(name=self.name, seconds=self.timeout))
