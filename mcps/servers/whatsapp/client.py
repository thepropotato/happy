"""THE MCP SIDE'S WAY OF ASKING THE BRIDGE THINGS. HTTP OVER LOOPBACK, NOTHING MORE.

SENDING TEXT AND MEDIA IS BACK. THE FILE PATH FOR MEDIA IS RESOLVED AGAINST
THIS MACHINE AND NOTHING ELSE — THE ORIGINAL REACHED INTO CLOUD STORAGE AND A
CONTAINER PATH, NEITHER OF WHICH EXISTS HERE.
"""
import asyncio
import os
import re
from pathlib import Path
from typing import Any

import httpx

from servers.shared.matching import resolve as match
def fix_surrogates(text: str) -> str:
    out = []
    i = 0
    while i < len(text):
        cp = ord(text[i])
        if 0xD800 <= cp <= 0xDBFF and i + 1 < len(text):
            low = ord(text[i + 1])
            if 0xDC00 <= low <= 0xDFFF:
                out.append(chr(0x10000 + ((cp - 0xD800) << 10) + (low - 0xDC00)))
                i += 2
                continue
        if 0xD800 <= cp <= 0xDFFF:
            i += 1
            continue
        out.append(text[i])
        i += 1
    return ''.join(out)


def clean_surrogates(obj):
    if isinstance(obj, str):
        return fix_surrogates(obj)
    if isinstance(obj, list):
        return [clean_surrogates(x) for x in obj]
    if isinstance(obj, dict):
        return {k: clean_surrogates(v) for k, v in obj.items()}
    return obj


BRIDGE_PORT = int(os.environ.get("WHATSAPP_BRIDGE_PORT") or 3001)
BRIDGE_BASE = f"http://127.0.0.1:{BRIDGE_PORT}"
BRIDGE_HEADERS = {"X-Bridge-Key": os.environ.get("INTERNAL_API_SECRET", "")}


class WhatsAppClient:

    def __init__(self, username: str = "default"):
        self.username = username

    async def get(self, path: str, timeout: float = 5.0) -> Any:
        async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
            r = await client.get(f"{BRIDGE_BASE}/{self.username}{path}", headers=BRIDGE_HEADERS)
            if r.status_code >= 400:
                try:
                    return clean_surrogates(r.json())
                except Exception:
                    r.raise_for_status()
            return clean_surrogates(r.json())

    async def post(self, path: str, body: dict, timeout: float = 10.0) -> Any:
        async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
            r = await client.post(f"{BRIDGE_BASE}/{self.username}{path}", json=body, headers=BRIDGE_HEADERS)
            if r.status_code >= 400:
                try:
                    return clean_surrogates(r.json())
                except Exception:
                    r.raise_for_status()
            return clean_surrogates(r.json())

    def unavailable(self, extra: str = "") -> dict:
        msg = "WhatsApp service is not running. Start it via the configure button."
        if extra:
            msg += f" ({extra})"
        return {"error": msg}

    async def get_status(self) -> dict[str, Any]:
        try:
            return await self.get("/status")
        except Exception as e:
            return self.unavailable(str(e))

    async def get_qr_code(self) -> dict[str, Any]:
        try:
            return await self.get("/qr", timeout=8.0)
        except Exception as e:
            return {"status": "loading", "qr": None, "error": str(e)}

    async def sync(self) -> dict[str, Any]:
        try:
            return await self.post("/sync", {}, timeout=120.0)
        except Exception as e:
            return {"error": str(e)}

    async def resolve_contact(self, query: str) -> str:
        try:
            result = await self.get(f"/resolve-contact?q={query}")
            return result.get("jid", query)
        except Exception:
            return query

    async def get_contacts(self) -> list[dict[str, str]]:
        try:
            return await self.get("/contacts")
        except Exception:
            return []

    async def search_contacts(self, query: str) -> list[dict[str, str]]:
        try:
            return await self.get(f"/search-contacts?q={query}")
        except Exception:
            contacts = await self.get_contacts()
            q = query.lower()
            return [
                c for c in contacts
                if q in c.get("name", "").lower() or q in c.get("number", "")
            ]

    async def get_chats(self) -> list[dict[str, Any]]:
        try:
            return await self.get("/chats")
        except Exception:
            return []

    async def get_messages(self, contact: str, limit: int = 20, media_only: bool = False, order: str = "newest", received_only: bool = False) -> list[dict[str, Any]]:
        jid = await self.resolve_contact(contact)
        if "@" not in jid:
            jid = f"{jid}@s.whatsapp.net"
        try:
            media_param = "&media=true" if media_only else ""
            order_param = f"&order={order}" if order != "newest" else ""
            received_param = "&received=true" if received_only else ""
            return await self.get(f"/messages/{jid}?limit={limit}{media_param}{order_param}{received_param}", timeout=10.0)
        except Exception:
            return []


    async def get_groups(self) -> list[dict[str, Any]]:
        try:
            return await self.get("/groups")
        except Exception:
            return []

    async def search_groups(self, query: str) -> list[dict[str, Any]]:
        groups = await self.get_groups()
        q = query.lower()
        return [
            g for g in groups
            if q in g.get("name", "").lower() or q in g.get("description", "").lower()
        ]

    async def get_group_by_id(self, group_id: str) -> dict[str, Any]:
        groups = await self.get_groups()
        for g in groups:
            if g.get("id") == group_id:
                return g
        return {"error": "Group not found", "group_id": group_id}

    async def get_group_participants(self, group_id: str) -> dict[str, Any]:
        try:
            return await self.get(f"/group-participants/{group_id}")
        except Exception as e:
            return {"error": str(e)}

    async def find_common_groups(self, contacts: list[str]) -> dict[str, Any]:
        try:
            contacts_param = ",".join(contacts)
            return await self.get(f"/search-groups-by-contacts?contacts={contacts_param}")
        except Exception as e:
            return {"error": str(e)}

    async def get_group_messages(self, group: str, limit: int = 20, order: str = "newest") -> list[dict[str, Any]]:
        jid = await self.resolve_contact(group)
        try:
            order_param = f"&order={order}" if order != "newest" else ""
            return await self.get(f"/messages/{jid}?limit={limit}{order_param}", timeout=10.0)
        except Exception:
            return []





    async def download_media_from_message(self, message_id: str, chat: str = "", download_path: str = "") -> dict[str, Any]:
        try:
            result = await self.get(f"/media/{message_id}")
            already_cached = "local_path" in result and not result.get("error")

            if not already_cached:
                chat_id = None
                if chat:
                    resolve_result = await self.get(f"/resolve-contact?q={chat}")
                    if "error" not in resolve_result:
                        chat_id = resolve_result.get("jid")

                result = await self.post("/download-media", {"chatId": chat_id, "messageId": message_id})
                if "error" in result:
                    return result

            local_path = result.get("local_path", "")

            if download_path and local_path:
                src = Path(local_path)
                if src.exists():
                    asked = Path(download_path).expanduser()
                    if asked.suffix:
                        dest = asked
                    else:
                        asked.mkdir(parents=True, exist_ok=True)
                        dest = asked / src.name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(src.read_bytes())
                    result["file_path"] = str(dest)
                    result["local_path"] = str(dest)
                    result["filename"] = dest.name

            return result
        except Exception as e:
            return {"error": str(e)}

    async def get_latest_received_message(self, include_groups: bool = False) -> dict[str, Any]:
        try:
            groups_param = "?groups=true" if include_groups else ""
            return await self.get(f"/latest-received-message{groups_param}")
        except Exception as e:
            return {"error": str(e)}

    async def get_latest_sent_message(self) -> dict[str, Any]:
        try:
            return await self.get("/latest-sent-message")
        except Exception as e:
            return {"error": str(e)}

    async def query_messages(self, chat: str = "", sender: str = "", limit: int = 5, from_me: str = "", date: str = "", order: str = "newest") -> list[dict[str, Any]]:
        try:
            from urllib.parse import urlencode
            def clean_param(v): return " ".join(str(v).split())
            params = {}
            if chat: params["chat"] = clean_param(chat)
            if sender: params["sender"] = clean_param(sender)
            if limit != 5: params["limit"] = limit
            if from_me: params["fromMe"] = clean_param(from_me)
            if date: params["date"] = clean_param(date)
            if order != "newest": params["order"] = clean_param(order)
            qs = ("?" + urlencode(params)) if params else ""
            return await self.get(f"/query-messages{qs}", timeout=10.0)
        except Exception as e:
            return {"error": str(e)}

    async def rebuild_senders(self) -> dict[str, Any]:
        try:
            return await self.post("/rebuild-senders", {}, timeout=30.0)
        except Exception as e:
            return {"error": str(e)}


    async def send_message(self, recipient: str, message: str) -> dict[str, str]:
        try:
            result = await self.post("/send", {"to": recipient, "message": message})
            if isinstance(result, dict) and "websocket not connected" in result.get("error", ""):
                await self.post("/stop", {}, timeout=5.0)
                await self.post("/start", {}, timeout=5.0)
                await asyncio.sleep(8)
                result = await self.post("/send", {"to": recipient, "message": message})
            return result
        except Exception as e:
            return {"error": str(e)}

    async def send_group_message(self, group: str, message: str) -> dict[str, str]:
        try:
            result = await self.post("/send", {"to": group, "message": message})
            if isinstance(result, dict) and "websocket not connected" in result.get("error", ""):
                await self.post("/stop", {}, timeout=5.0)
                await self.post("/start", {}, timeout=5.0)
                await asyncio.sleep(8)
                result = await self.post("/send", {"to": group, "message": message})
            return result
        except Exception as e:
            return {"error": str(e)}

    async def send_media_message(self, recipient: str, source: str, caption: str = "") -> dict[str, Any]:
        try:
            url = source.replace("file://", "") if source.startswith("file://") else source

            if not url.startswith("http"):
                here = Path(url).expanduser()
                if here.exists():
                    url = str(here.resolve())

            filename = Path(url).name if not url.startswith("http") else Path(url.split("?")[0]).name
            return await self.post("/send-media", {
                "to": recipient,
                "url": url,
                "caption": caption,
                "filename": filename,
            })
        except Exception as e:
            return {"error": str(e)}

    def close(self):
        pass


