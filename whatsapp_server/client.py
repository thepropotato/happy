"""THE MCP SIDE'S WAY OF ASKING THE BRIDGE THINGS."""
import asyncio
import base64
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

from whatsapp_server import contacts as knowledge
from whatsapp_server import key as bridge_key
from whatsapp_server import nearing

import httpx


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
BRIDGE_HEADERS = {"X-Bridge-Key": bridge_key.read()}

# HOW LONG A SEND IS GIVEN TO BE ACKNOWLEDGED BEFORE THIS SIDE GIVES UP ON IT. A SLOW SEND
# THAT SUCCEEDS A FEW SECONDS LATE USED TO BE REPORTED AS FAILED BECAUSE THE OLD LIMIT WAS
# ONLY 10 SECONDS, WHICH A MEDIA SEND CAN EASILY TAKE LONGER THAN.
SEND_TIMEOUT = 60.0


class WhatsAppClient:

    def __init__(self, username: str = "default"):
        self.username = username
        self.unreachable = False

    async def get(self, path: str, timeout: float = 5.0) -> Any:
        async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
            try:
                r = await client.get(f"{BRIDGE_BASE}/{self.username}{path}", headers=BRIDGE_HEADERS)
            except Exception:
                # SET HERE AND CLEARED HERE, SO ONE DEAD CALL CANNOT OUTLIVE THE
                # BRIDGE COMING BACK.
                self.unreachable = True

                raise

            self.unreachable = False

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

    # AN EMPTY LIST IS AN ANSWER — THIS CHAT HAS NOTHING — AND A BRIDGE THAT NEVER
    # ANSWERED IS NOT. THEY LOOKED THE SAME FOR EVERY READ HERE, SO A DEAD BRIDGE
    # READ AS AN EMPTY WHATSAPP AND WAS REPORTED AS ONE.
    def failed(self, doing: str, error: Exception) -> dict:
        return {"error": f"Could not {doing}: {self.reason(error)}"}

    def reason(self, error: Exception) -> str:
        said = str(error).strip()

        if isinstance(error, httpx.ConnectError) or "connection attempts failed" in said.lower():
            return (
                "the WhatsApp bridge is not answering, so nothing could be read. It is not "
                "that there is nothing there. Say this rather than reporting an empty result."
            )

        if isinstance(error, httpx.TimeoutException):
            return "the WhatsApp bridge took too long to answer, so nothing could be read."

        return said or error.__class__.__name__

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

    async def resolve_contact(self, query: str) -> str | None:
        resolved = await self.resolve_contact_with_source(query)

        return resolved.get("jid")

    async def resolve_contact_with_source(self, query: str) -> dict[str, str | None]:
        asked = (query or "").strip()
        bare = re.sub(r"\s*\([^()]*\)$", "", asked)

        # A NAME HANDED BACK WITH ITS NOTE STILL ON, LIKE "Aunty (WhatsApp profile name Notjane)", IS STILL
        # THAT NAME, UNLESS SOMEONE IS SAVED WITH THE BRACKETS AS PART OF IT.
        if bare and bare != asked and not await self.exact_contact(asked):
            asked = bare
        known = knowledge.recall(asked, "whatsapp")
        looked = known or asked
        original = None if known else self.pending_original(asked)

        try:
            result = await self.get(f"/resolve-contact?q={looked}")
            jid = (result or {}).get("jid") if isinstance(result, dict) else None

            if self.real_jid(jid):
                source = "known" if known else "exact"

                if original:
                    source = "fresh_confirmation"
                    self.clear_pending(asked)

                return {
                    "jid": jid,
                    "source": source,
                    "said": original or asked,
                    "resolved": asked,
                }
        except Exception:
            pass

        found = await self.search_contacts(asked)

        if found:
            jid = self.contact_jid(found[0])

            if jid:
                source = "known" if known else "exact"

                if original:
                    source = "fresh_confirmation"
                    self.clear_pending(asked)

                return {
                    "jid": jid,
                    "source": source,
                    "said": original or asked,
                    "resolved": asked,
                }

        return {"jid": None, "source": "none", "said": asked, "resolved": None}

    def pending_original(self, said: str) -> str | None:
        return knowledge.awaiting(said, "whatsapp")

    def clear_pending(self, said: str) -> None:
        knowledge.settle(said, "whatsapp")

    def queue_pending(self, said: str, candidate: str) -> None:
        knowledge.expect(said, candidate, "whatsapp")

    def remember_note(self, resolved: dict[str, str | None]) -> str | None:
        """THE ALIAS IS SAVED HERE, NOT ASKED FOR.

        THIS ONCE RETURNED A SENTENCE TELLING THE MODEL TO CALL remember_contact ITSELF, AND
        IN THREE CONFIRMATIONS IT NEVER ONCE DID: THE NUDGE ARRIVES ATTACHED TO A SEND THAT
        ALREADY WORKED, WHICH IS THE MOMENT A TURN IS FINISHED AND SPEAKING. THE CODE KNOWS
        BOTH NAMES AND THAT IT WORKED, SO THE CODE WRITES IT DOWN."""
        if resolved.get("source") != "fresh_confirmation":
            return None

        said = str(resolved.get("said") or "").strip()
        means = str(resolved.get("resolved") or "").strip()

        if not said or not means:
            return None

        knowledge.remember_fact(said, "whatsapp", means)
        knowledge.settle(means, "whatsapp")

        return (
            f"Remembered that '{said}' means '{means}' here, so it will not need asking "
            "again."
        )

    def real_jid(self, value: str | None) -> bool:
        if not value or not isinstance(value, str):
            return False

        left, sep, right = value.partition("@")

        return bool(sep and left and right)

    def contact_jid(self, contact: dict[str, Any]) -> str | None:
        jid = contact.get("jid") or contact.get("id")

        if isinstance(jid, str) and jid:
            return jid

        number = str(contact.get("number") or "").strip()

        if not number:
            return None

        return number if "@" in number else f"{number}@s.whatsapp.net"

    async def nearest(self, asked: str) -> list[tuple[str, str]]:
        """THE PEOPLE asked COULD MEAN, ONCE EACH, AS (THE NAME A LOOKUP TAKES, THEIR PROFILE NAME).

        ONE PERSON CAN BE SAVED UNDER A NAME, KNOWN BY A PROFILE NAME AND HELD UNDER A SECOND
        ID AS WELL, AND LISTED SEPARATELY THEY READ AS THREE PEOPLE: "Aunty", "Notjane" AND
        "Aunty (profile Notjane)" WERE PUT TO THE PERSON AS A CHOICE, AND THE THIRD, WHICH NO
        LOOKUP TAKES, WAS THE ONE PICKED. EACH NAME IS RESOLVED, AND ONE ID IS ONE PERSON."""
        contacts = await self.get_contacts()
        names = [c.get("name") for c in contacts]
        # A PROFILE NAME IS WEIGHED ON ITS OWN BUT STANDS FOR THE SAVED NAME, WHICH IS WHAT A LOOKUP TAKES.
        names += [(c["profile"], c.get("name")) for c in contacts
                  if c.get("profile") and c.get("name") and c.get("profile") != c.get("name")]
        chats = await self.get_chats()

        if isinstance(chats, list):
            names += [c.get("name") for c in chats]

        people, seen = [], set()

        for name in nearing.nearest(asked, names, most=nearing.MOST * 3):
            try:
                found = await self.get(f"/resolve-contact?q={quote(name)}")
            except Exception:
                found = None

            found = found if isinstance(found, dict) and found.get("jid") else {}
            who = found.get("jid") or name.lower()

            if who in seen:
                continue

            seen.add(who)
            saved = found.get("name") or name
            profile = found.get("profile") or ""
            people.append((saved, profile if profile.lower() != saved.lower() else ""))

            if len(people) == nearing.MOST:
                break

        return people

    async def get_contacts(self) -> list[dict[str, str]]:
        try:
            found = await self.get("/contacts")
        except Exception:
            return []

        return found if isinstance(found, list) else []

    async def search_contacts(self, query: str) -> list[dict[str, str]]:
        asked = (query or "").strip()
        known = knowledge.recall(asked, "whatsapp")
        looked = known or asked

        found = await self.raw_contacts(looked)

        if not found:
            return []

        if known:
            return found

        exact = await self.exact_contact(asked)

        if exact:
            return [exact]

        guess = self.contact_name(found[0])
        self.queue_pending(asked, guess)
        knowledge.resolve_or_confirm(asked, "whatsapp", guess)

        return []

    async def raw_contacts(self, query: str) -> list[dict[str, str]]:
        looked = (query or "").strip()

        try:
            found = await self.get(f"/search-contacts?q={looked}")
        except Exception:
            contacts = await self.get_contacts()
            q = looked.lower()
            found = [
                c for c in contacts
                if q in c.get("name", "").lower() or q in c.get("number", "")
            ]

        # THE ENDPOINT ANSWERS WITH NOTHING RATHER THAN AN EMPTY LIST WHEN IT HAS
        # NOTHING, AND EVERY CALLER HERE ITERATES WHAT COMES BACK.
        return found or []

    async def exact_contact(self, query: str) -> dict[str, str] | None:
        asked = (query or "").strip().lower()

        if not asked:
            return None

        for contact in await self.get_contacts():
            name = str(contact.get("name") or "").strip().lower()
            number = str(contact.get("number") or "").strip().lower()
            jid = str(contact.get("jid") or contact.get("id") or "").strip().lower()

            if asked in (name, number, jid):
                return contact

        return None

    def contact_name(self, contact: dict[str, Any]) -> str:
        return str(contact.get("name") or contact.get("number") or contact.get("id") or "that contact").strip()

    async def get_chats(self) -> list[dict[str, Any]] | dict[str, Any]:
        try:
            return await self.get("/chats")
        except Exception as e:
            return self.failed("read your chats", e)

    async def get_messages(self, contact: str, limit: int = 20, media_only: bool = False, order: str = "newest", received_only: bool = False) -> list[dict[str, Any]]:
        jid = await self.resolve_contact(contact)

        if not jid:
            if self.unreachable:
                return self.failed(f"read messages from '{contact}'", httpx.ConnectError(""))

            return {"error": nearing.missed(contact, await self.nearest(contact))}

        if "@" not in jid:
            jid = f"{jid}@s.whatsapp.net"
        try:
            media_param = "&media=true" if media_only else ""
            order_param = f"&order={order}" if order != "newest" else ""
            received_param = "&received=true" if received_only else ""
            return await self.get(f"/messages/{jid}?limit={limit}{media_param}{order_param}{received_param}", timeout=10.0)
        except Exception as e:
            return self.failed(f"read messages from '{contact}'", e)


    async def get_groups(self) -> list[dict[str, Any]] | dict[str, Any]:
        try:
            return await self.get("/groups")
        except Exception as e:
            return self.failed("read your groups", e)

    async def search_groups(self, query: str) -> list[dict[str, Any]]:
        groups = await self.get_groups()

        if not isinstance(groups, list):
            return []

        q = query.lower()
        found = [
            g for g in groups
            if q in g.get("name", "").lower() or q in g.get("description", "").lower()
        ]

        return found

    async def resolve_group(self, query: str) -> str:
        asked = (query or "").strip()
        found = await self.search_groups(asked)

        exact = [
            group
            for group in found
            if asked.lower()
            in {
                str(group.get("name") or "").strip().lower(),
                str(group.get("id") or "").strip().lower(),
                str(group.get("jid") or "").strip().lower(),
            }
        ]

        if exact:
            gid = exact[0].get("id") or exact[0].get("jid")

            if isinstance(gid, str) and gid:
                return gid

        if found:
            guess = str(found[0].get("name") or found[0].get("id") or "that group").strip()
            raise LookupError(
                f"'{asked}' isn't an exact match — the closest group I found is '{guess}'. "
                "Confirm with the person directly whether this is correct before using it."
            )

        raise LookupError(
            f"I couldn't find a group matching '{asked}'. Ask the person for the exact group "
            "name they see in WhatsApp."
        )

    async def get_group_by_id(self, group_id: str) -> dict[str, Any]:
        groups = await self.get_groups()

        if not isinstance(groups, list):
            return groups

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

        if not jid:
            return []

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

    async def get_pushed(self, since: float) -> list[dict[str, Any]]:
        try:
            return await self.get(f"/pushed?since={since}")
        except Exception:
            return []

    async def create_group(self, name: str) -> dict[str, Any]:
        try:
            return await self.post("/create-group", {"name": name}, timeout=30.0)
        except Exception as e:
            return {"error": str(e)}

    async def set_group_photo(self, group: str, photo: bytes) -> dict[str, Any]:
        try:
            body = {"group": group, "photo": base64.b64encode(photo).decode()}
            return await self.post("/set-group-photo", body, timeout=30.0)
        except Exception as e:
            return {"error": str(e)}

    async def get_recent_sent(self, limit: int = 25) -> list[dict[str, Any]] | dict[str, Any]:
        try:
            return await self.get(f"/recent-sent?limit={limit}")
        except Exception as e:
            return self.failed("read what you recently sent", e)

    async def get_latest_sent_message(self) -> dict[str, Any]:
        try:
            return await self.get("/latest-sent-message")
        except Exception as e:
            return {"error": str(e)}

    async def query_messages(self, chat: str = "", sender: str = "", limit: int = 5, from_me: str = "", date: str = "", order: str = "newest", kind: str = "", filename: str = "", since: str = "", until: str = "", text: str = "") -> list[dict[str, Any]]:
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
            if kind: params["kind"] = clean_param(kind)
            if filename: params["filename"] = clean_param(filename)
            if since: params["since"] = clean_param(since)
            if until: params["until"] = clean_param(until)
            if text: params["text"] = clean_param(text)
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
            resolved = await self.resolve_contact_with_source(recipient)
            to = resolved.get("jid")

            if not to:
                return {"error": f"Contact '{recipient}' not found."}

            result = await self.post("/send", {"to": to, "message": message}, timeout=SEND_TIMEOUT)
            if isinstance(result, dict) and "websocket not connected" in result.get("error", ""):
                await self.post("/stop", {}, timeout=5.0)
                await self.post("/start", {}, timeout=5.0)
                await asyncio.sleep(8)
                result = await self.post("/send", {"to": to, "message": message}, timeout=SEND_TIMEOUT)

            note = self.remember_note(resolved)
            if note and isinstance(result, dict) and "error" not in result:
                result["note"] = note

            return result
        except httpx.TimeoutException:
            return {"error": f"Timed out waiting for WhatsApp to confirm the send after {SEND_TIMEOUT:.0f} seconds."}
        except Exception as e:
            return {"error": str(e)}

    async def send_group_message(self, group: str, message: str) -> dict[str, str]:
        try:
            resolved = await self.resolve_contact_with_source(group)
            to = resolved.get("jid")

            if not to:
                to = await self.resolve_group(group)
                resolved = {
                    "jid": to,
                    "source": "exact",
                    "said": (group or "").strip(),
                    "resolved": (group or "").strip(),
                }

            result = await self.post("/send", {"to": to, "message": message}, timeout=SEND_TIMEOUT)
            if isinstance(result, dict) and "websocket not connected" in result.get("error", ""):
                await self.post("/stop", {}, timeout=5.0)
                await self.post("/start", {}, timeout=5.0)
                await asyncio.sleep(8)
                result = await self.post("/send", {"to": to, "message": message}, timeout=SEND_TIMEOUT)

            note = self.remember_note(resolved)
            if note and isinstance(result, dict) and "error" not in result:
                result["note"] = note

            return result
        except httpx.TimeoutException:
            return {"error": f"Timed out waiting for WhatsApp to confirm the send after {SEND_TIMEOUT:.0f} seconds."}
        except Exception as e:
            return {"error": str(e)}

    async def send_media_message(self, recipient: str, source: str, caption: str = "") -> dict[str, Any]:
        try:
            resolved = await self.resolve_contact_with_source(recipient)
            to = resolved.get("jid")

            if not to:
                return {"error": f"Contact '{recipient}' not found."}

            url = source.replace("file://", "") if source.startswith("file://") else source

            if not url.startswith("http"):
                here = Path(url).expanduser()
                if here.exists():
                    url = str(here.resolve())

            filename = Path(url).name if not url.startswith("http") else Path(url.split("?")[0]).name
            result = await self.post("/send-media", {
                "to": to,
                "url": url,
                "caption": caption,
                "filename": filename,
            }, timeout=SEND_TIMEOUT)

            note = self.remember_note(resolved)
            if note and isinstance(result, dict) and "error" not in result:
                result["note"] = note

            return result
        except httpx.TimeoutException:
            return {"error": f"Timed out waiting for WhatsApp to confirm the send after {SEND_TIMEOUT:.0f} seconds."}
        except Exception as e:
            return {"error": str(e)}

    def close(self):
        pass