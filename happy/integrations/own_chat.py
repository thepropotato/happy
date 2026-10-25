"""Happy's own WhatsApp group: what the person writes there from their phone is a request, and the answer goes back there."""

import base64
import logging
import re
import time

import httpx

from happy.integrations import whatsapp

log = logging.getLogger("happy.whatsapp")

WORDS = re.compile(r"[^\W_]+", re.UNICODE)
# A GROUP WHATSAPP REFUSED TO MAKE IS NOT ASKED FOR AGAIN EVERY FEW SECONDS.
AGAIN_SECONDS = 600
# HOW OFTEN THE GROUP'S NAME AND PICTURE ARE CHECKED AGAINST THE SETTINGS.
SYNC_SECONDS = 60
# BUMPED WHEN THE DRAWING ITSELF CHANGES, SO EVERY GROUP GETS THE NEW PICTURE.
PICTURE = 1


class Chat:
    def __init__(self, cfg, load=None):
        from happy.config import Config

        self.cfg = cfg
        self.load = load or Config
        self.id = cfg.get("whatsapp.own_chat_id") or None
        self.tried = 0.0
        self.synced = 0.0
        self.since = time.time()
        self.seen = set()

    @property
    def name(self):
        # READ FRESH, SO A NAME OR COLOUR CHANGED IN THE SETTINGS REACHES THE GROUP WITHOUT A RESTART.
        self.cfg = self.load()
        return (self.cfg.get("name") or "Happy").strip()

    def keep(self, key, value):
        self.cfg.set(f"whatsapp.{key}", value)
        self.cfg.save()

    def plain(self, text):
        return " ".join(WORDS.findall((text or "").lower()))

    def find(self):
        """Happy's group: the one made before, else one with his name, else a new one with nobody else in it."""
        if self.id and time.monotonic() - self.synced < SYNC_SECONDS:
            return self.id
        groups = httpx.get(f"{whatsapp.BASE}/groups", timeout=10).json()
        known = {g["id"]: g for g in groups}
        if self.id not in known:
            found = [g for g in groups if self.plain(g.get("name")) == self.plain(self.name)]
            self.id = found[0]["id"] if found else None
            if self.id:
                self.keep("own_chat_id", self.id)
        if self.id:
            self.sync(known.get(self.id, {}).get("name", ""))
        elif time.monotonic() - self.tried > AGAIN_SECONDS:
            self.tried = time.monotonic()
            made = httpx.post(f"{whatsapp.BASE}/create-group", json={"name": self.name}, timeout=20).json()
            if made.get("id"):
                self.id = made["id"]
                self.keep("own_chat_id", self.id)
                log.info("made the %s group on WhatsApp", self.name)
                self.sync(self.name)
                self.send("This is my chat. Write here from your phone and I'll do it on your computer and answer here.")
            else:
                log.warning("could not make the %s group: %s", self.name, made.get("error"))
        return self.id

    def sync(self, shown):
        """Puts the group's name and picture back in line with Happy's name and colour."""
        self.synced = time.monotonic()
        name = self.name
        if shown and shown != name:
            done = httpx.post(f"{whatsapp.BASE}/set-group-name", json={"group": self.id, "name": name}, timeout=20).json()
            log.info("renamed the WhatsApp group to %s%s", name, f" ({done['error']})" if done.get("error") else "")
        colour = self.cfg.get("colour") or "#658761"
        wanted = f"{colour}/{PICTURE}"
        if self.cfg.get("whatsapp.own_chat_picture") != wanted:
            from happy.ui.picture import smile_jpeg

            photo = base64.b64encode(smile_jpeg(colour)).decode()
            done = httpx.post(f"{whatsapp.BASE}/set-group-photo", json={"group": self.id, "photo": photo}, timeout=30).json()
            if done.get("error"):
                log.warning("could not set the WhatsApp group's picture: %s", done["error"])
            else:
                self.keep("own_chat_picture", wanted)

    def requests(self):
        """New messages the person wrote into the group since Happy started, never Happy's own answers."""
        if not whatsapp.listening() or not self.find():
            return []
        found = httpx.get(f"{whatsapp.BASE}/messages/{self.id}", params={"limit": 10}, timeout=10).json()
        mine = {p["id"] for p in httpx.get(f"{whatsapp.BASE}/pushed", params={"since": self.since - 60}, timeout=10).json()}
        new = []
        for message in reversed(found if isinstance(found, list) else []):
            ident = message.get("id")
            # ONLY THE OWNER'S OWN ACCOUNT, AND NOT WHAT THIS COMPUTER SENT AS THE ANSWER.
            if (not ident or ident in self.seen or ident in mine or not message.get("fromMe")
                    or message.get("timestamp", 0) < self.since or not (message.get("body") or "").strip()):
                continue
            self.seen.add(ident)
            new.append(message["body"].strip())
        return new

    def send(self, text):
        if not self.id or not text.strip():
            return False
        try:
            reply = httpx.post(f"{whatsapp.BASE}/send-group", json={"groupId": self.id, "message": text}, timeout=20).json()
        except (httpx.HTTPError, ValueError) as error:
            log.warning("could not answer on WhatsApp: %s", error)
            return False
        if reply.get("messageId"):
            self.seen.add(reply["messageId"])
        return bool(reply.get("success"))
