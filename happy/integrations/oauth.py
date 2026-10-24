"""Signing in to MCP servers over OAuth, for when Happy connects to them itself rather than through Claude Code."""

import asyncio
import json
import os
import re
import webbrowser
from urllib.parse import parse_qs, urlparse

from mcp.client.auth import OAuthClientProvider
from mcp.shared.auth import AuthorizationCodeResult, OAuthClientInformationFull, OAuthClientMetadata, OAuthToken

from happy import paths
from happy.config import secrets

PORT = 47321
REDIRECT = f"http://localhost:{PORT}/callback"
FOLDER = paths.HOME / "oauth"
DONE_PAGE = (b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nConnection: close\r\n\r\n"
             b"<html><body style='font-family:-apple-system,sans-serif;background:#0e100f;color:#eceFed;"
             b"display:flex;align-items:center;justify-content:center;height:100vh'>"
             b"<p>Signed in. You can close this tab.</p></body></html>")


class NeedsSignIn(Exception):
    pass


class Storage:
    """Tokens and client details for one server, in a file only this user can read."""

    def __init__(self, name):
        safe = re.sub(r"[^\w.-]", "_", name)
        self.file = FOLDER / f"{safe}.json"
        self.preset = secrets().get("oauth", {}).get(name)

    def load(self):
        try:
            return json.loads(self.file.read_text())
        except (OSError, ValueError):
            return {}

    def save(self, key, value):
        data = self.load()
        data[key] = value
        FOLDER.mkdir(parents=True, exist_ok=True)
        self.file.write_text(json.dumps(data))
        os.chmod(self.file, 0o600)

    async def get_tokens(self):
        data = self.load().get("tokens")
        return OAuthToken.model_validate(data) if data else None

    async def set_tokens(self, tokens):
        self.save("tokens", tokens.model_dump(mode="json", exclude_none=True))

    async def get_client_info(self):
        if self.preset:
            secret = self.preset.get("client_secret")
            return OAuthClientInformationFull(client_id=self.preset["client_id"], client_secret=secret, redirect_uris=[REDIRECT],
                                              token_endpoint_auth_method="client_secret_post" if secret else "none",
                                              grant_types=["authorization_code", "refresh_token"], response_types=["code"])
        data = self.load().get("client")
        return OAuthClientInformationFull.model_validate(data) if data else None

    async def set_client_info(self, info):
        self.save("client", info.model_dump(mode="json", exclude_none=True))

    def signed_in(self):
        return bool(self.load().get("tokens"))


async def wait_for_code(timeout=300):
    """Listens on the loopback address for the browser to come back with the sign-in code."""
    loop = asyncio.get_running_loop()
    arrived = loop.create_future()

    async def answer(reader, writer):
        line = (await reader.readline()).decode(errors="ignore")
        while (await reader.readline()) not in (b"\r\n", b"\n", b""):
            pass
        query = parse_qs(urlparse(line.split(" ")[1] if " " in line else "").query)
        writer.write(DONE_PAGE)
        await writer.drain()
        writer.close()
        if "code" in query and not arrived.done():
            arrived.set_result(AuthorizationCodeResult(code=query["code"][0], state=(query.get("state") or [None])[0],
                                                       iss=(query.get("iss") or [None])[0]))

    server = await asyncio.start_server(answer, host=["127.0.0.1", "::1"], port=PORT)
    try:
        return await asyncio.wait_for(arrived, timeout)
    finally:
        server.close()


def provider(name, url, interactive=False):
    """OAuth for one server; outside a sign-in it never opens a browser, it just reports that one is needed."""
    storage = Storage(name)
    metadata = OAuthClientMetadata(client_name="Happy", redirect_uris=[REDIRECT], response_types=["code"],
                                   grant_types=["authorization_code", "refresh_token"], token_endpoint_auth_method="none")

    async def redirect(address):
        if not interactive:
            raise NeedsSignIn(f"{name} needs sign-in")
        webbrowser.open(address)

    return OAuthClientProvider(url, metadata, storage, redirect_handler=redirect, callback_handler=wait_for_code)
