"""THE HALF THAT HOLDS THE WHATSAPP CONNECTION."""
import base64
import hmac
import io
import json
import logging
import os
import re
import shutil
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import segno
from flask import Flask, request, jsonify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("whatsapp-bridge")

from neonize import NewClient
from neonize.utils.jid import build_jid, Jid2String
from neonize.proto.Neonize_pb2 import (
    Message as MessageEv, Connected as ConnectedEv, Disconnected as DisconnectedEv,
    HistorySync as HistorySyncEv, LoggedOut as LoggedOutEv,
    OfflineSyncPreview as OfflineSyncPreviewEv, OfflineSyncCompleted as OfflineSyncCompletedEv,
    Receipt as ReceiptEv,
    _RECEIPT_RECEIPTTYPE,
)
from neonize.utils.enum import ParticipantChange

RECEIPT_READ_SELF = _RECEIPT_RECEIPTTYPE.values_by_name["READ_SELF"].number

# READING ON THE PHONE CLEARS THE BADGE THERE, SO IT HAS TO CLEAR IT HERE TOO.
RECEIPTS_THAT_CLEAR_UNREAD = {
    _RECEIPT_RECEIPTTYPE.values_by_name[n].number
    for n in ("READ_SELF", "READ", "PLAYED_SELF")
}



app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False


@app.before_request
def require_bridge_key():
    # is_bridge_running() POLLS THIS WITHOUT THE KEY, AND IT LEAKS NOTHING.
    if request.path == "/health":
        return
    # A REAL BROWSER CANNOT BE MADE TO SEND A HEADER, AND THE QR IS USELESS TO
    # ANYBODY NOT HOLDING THE PHONE.
    if request.path.endswith("/scan"):
        return
    if not BRIDGE_SECRET:
        return
    provided = request.headers.get("X-Bridge-Key", "")
    if not hmac.compare_digest(provided, BRIDGE_SECRET):
        return jsonify({"error": "Unauthorized"}), 401


@app.errorhandler(Exception)
def handle_exception(e):
    # A BROWSER ASKS FOR A FAVICON ON EVERY SCAN PAGE AND THERE IS NONE TO GIVE IT, WHICH IS
    # NOT WORTH A TRACEBACK. EVERYTHING ELSE IS: SWALLOWING THESE IS WHY A BRIDGE THAT MISBEHAVES
    # LEAVES NOTHING TO READ AFTERWARDS.
    if request.path == "/favicon.ico":
        return "", 404

    logger.exception(f"[http] {request.method} {request.path} failed")

    return jsonify({"error": "Internal bridge error"}), 500


# BESIDE THE REST OF WHAT HAPPY KEEPS, NOT INSIDE THE SERVER'S OWN FOLDER.
DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "whatsapp"

PORT = int(os.environ.get("WHATSAPP_BRIDGE_PORT") or 3001)

# NOTHING BUT THIS MACHINE CAN REACH THE PORT, SO THE KEY IS OPTIONAL AND OFF BY DEFAULT.
BRIDGE_SECRET = os.environ.get("INTERNAL_API_SECRET", "")

# HOW LONG A QR CODE IS WORTH SHOWING.
QR_FIRST = 60
QR_LATER = 20
QR_SLACK = 10

# HOW LONG THE SOCKET HAS TO STAY SHUT BEFORE THE RUN COUNTS AS OVER, SINCE A
# PAIRING SHUTS IT TOO AND COMES BACK LOGGED IN A SECOND OR TWO LATER.
QR_GRACE = 5

# HOW OFTEN THE CODE ON SCREEN IS CHECKED, AND HOW LONG A HIT ON THE PAGE COUNTS
# AS SOMEBODY STILL STANDING THERE WITH THEIR PHONE OUT.
QR_EVERY = 1
QR_WATCHED = 120

# WHAT A RESTART OPENS WITH, IN THE USER'S OWN FOLDER SO UNLINKING TAKES IT TOO.
CACHE = "cache.json"

# HOW MANY OF THE OWNER'S OWN MESSAGES ARE HELD BACK FOR WHOEVER IS WATCHING.
RECENT_SENT = 50

# AND HOW MANY OF OUR OWN SENDS. ONLY THIS TURN'S ARE EVER ASKED FOR.
PUSHED = 50

# raw_messages IS NOT IN HERE AND CANNOT BE: THEY ARE LIVE PROTOBUFS.
KEPT = (
    "phone", "name",
    "contacts", "chats", "groups", "messages", "media",
    "latest_received_message", "latest_sent_message",
    "downloaded_media", "lid_name_map", "lid_to_pn",
)


def fix_surrogates(text: str) -> str:
    """Convert valid surrogate pairs to proper Unicode (preserves emojis), strip lone surrogates."""
    out = []
    i = 0
    while i < len(text):
        cp = ord(text[i])
        if 0xD800 <= cp <= 0xDBFF and i + 1 < len(text):  # high surrogate
            low = ord(text[i + 1])
            if 0xDC00 <= low <= 0xDFFF:  # valid pair → real emoji
                out.append(chr(0x10000 + ((cp - 0xD800) << 10) + (low - 0xDC00)))
                i += 2
                continue
        if 0xD800 <= cp <= 0xDFFF:  # lone surrogate - drop it
            i += 1
            continue
        out.append(text[i])
        i += 1
    return ''.join(out)


def clean(obj):
    if isinstance(obj, str):
        return fix_surrogates(obj)
    if isinstance(obj, list):
        return [clean(x) for x in obj]
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    return obj


EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FFFF"   # Misc symbols, emoticons, transport, supplemental
    "\U00002600-\U000027BF"    # Misc symbols & dingbats
    "\U00002300-\U000023FF"    # Misc technical
    "\U0000FE00-\U0000FE0F"    # Variation selectors
    "\U0001F1E0-\U0001F1FF"    # Regional indicator (flags)
    "\U00003000-\U000030FF"    # CJK symbols
    "]+",
    flags=re.UNICODE,
)


def strip_emoji(text: str) -> str:
    """Remove emoji characters and collapse extra whitespace - used for fuzzy name matching."""
    return re.sub(r'\s+', ' ', EMOJI_RE.sub('', text)).strip()


def name_match(query: str, name: str) -> bool:
    """True if query matches name via substring or lenient alphanumeric comparison."""
    q, n = query.lower(), name.lower()
    if q in n:
        return True
    q2, n2 = strip_emoji(q), strip_emoji(n)
    if bool(q2) and q2 in n2:
        return True
    # BIDIRECTIONAL: THE AGENT DROPS PUNCTUATION AND ADDS WORDS IN EITHER DIRECTION.
    q3 = re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9\s]', ' ', q2)).strip()
    n3 = re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9\s]', ' ', n2)).strip()
    if q3 and n3:
        return q3 in n3 or n3 in q3
    return False


def jid_str(jid) -> str:
    try:
        return Jid2String(jid)
    except Exception:
        return str(jid)


def contact_name(contact_msg) -> str:
    """Extract display name from a contactMessage."""
    name = getattr(contact_msg, 'displayName', "") or ""
    if name:
        return name
    vcard = getattr(contact_msg, 'vcard', "") or ""
    for line in vcard.splitlines():
        if line.upper().startswith("FN:"):
            fn = line[3:].strip()
            if fn:
                return fn
    # waid= IS THE WHATSAPP NUMBER EMBEDDED IN THE TEL FIELD.
    for line in vcard.splitlines():
        m = re.search(r'waid=(\d+)', line, re.IGNORECASE)
        if m:
            return f"+{m.group(1)}"
    for line in vcard.splitlines():
        if line.upper().startswith("TEL"):
            parts = line.split(":")
            if len(parts) >= 2:
                phone = re.sub(r'[^\d+]', '', parts[-1].strip())
                if phone:
                    return phone
    return ""


def contacts_array_name(arr_msg) -> str:
    """Extract names from a contactsArrayMessage (multiple contacts forwarded at once)."""
    names = []
    for c in getattr(arr_msg, 'contacts', []):
        n = contact_name(c)
        if n:
            names.append(n)
    if names:
        return ", ".join(names)
    return getattr(arr_msg, 'displayName', "") or "[Contact]"


def resolve_lid(session, jid):
    jid_s = jid_str(jid)
    if "@lid" not in jid_s:
        return jid_s
    if jid_s in session.lid_to_pn:
        return session.lid_to_pn[jid_s]
    if session.client:
        try:
            lid_user = jid_s.split("@")[0]
            lid_jid = build_jid(lid_user, "lid")
            pn_jid = session.client.get_pn_from_lid(lid_jid)
            resolved = jid_str(pn_jid)
            if "@lid" not in resolved:
                session.lid_to_pn[jid_s] = resolved
                return resolved
        except Exception as e:
            pass
    return jid_s


def resolve_lid_str(session, jid_string):
    if not jid_string or "@lid" not in str(jid_string):
        return str(jid_string)
    jid_s = str(jid_string)
    if jid_s in session.lid_to_pn:
        return session.lid_to_pn[jid_s]
    if session.client:
        try:
            lid_user = jid_s.split("@")[0]
            lid_jid = build_jid(lid_user, "lid")
            pn_jid = session.client.get_pn_from_lid(lid_jid)
            resolved = jid_str(pn_jid)
            if "@lid" not in resolved:
                session.lid_to_pn[jid_s] = resolved
                return resolved
        except Exception:
            pass
    return jid_s
















class Session:
    def __init__(self, username):
        self.username = username
        self.lock = threading.RLock()

        user_dir = DATA_DIR / username
        user_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = str(user_dir / "session.db")
        self.dl_dir = str(user_dir / "downloads")
        os.makedirs(self.dl_dir, exist_ok=True)

        self.client = None
        self.connect_thread = None

        self.connected = False
        self.authenticated = False
        self.phone = None
        self.name = None
        self.qr_data = None
        self.qr_at = 0
        self.qr_life = QR_FIRST
        self.qr_shut = 0
        self.qr_seen = 0

        self.contacts = []
        self.chats = []
        self.groups = []
        self.messages = {}   # { jid: [text] }
        self.media = {}      # { jid: [media] }
        self.latest_received_message = None
        self.latest_sent_message = None
        self.recent_sent = []  # THE OWNER'S OWN, ANY CHAT, OLDEST FIRST. THIS RUN ONLY.
        self.pushed = []  # WHAT THIS DEVICE SENT ITSELF, WHICH NO CHAT EVER SHOWS BACK.
        self.downloaded_media = {}
        self.raw_messages = {}
        self.failed_downloads = set()

        self.lid_name_map = {}
        self.jid_cache = {}
        self.lid_to_pn = {}
        self.pn_to_lid = {}  # THE OTHER WAY ROUND, WHICH IS THE ONE SENDING NEEDS.
        self.active_conversations = {}  # { chat_jid: {"id", "ts", "thread_id"} }

        self.sync_status = {
            "syncing": False, "phase": "idle",
            "contacts": 0, "chats": 0, "groups": 0,
            "error": None, "message": None,
            "startedAt": None, "completedAt": None,
        }

        self.contacts_enriched = False
        self.last_history_sync_at = 0
        self.do_sync_done = False
        self.persist_timer = None
        self.reconnect_count = 0
        self.max_reconnect = 10
        self.offline_msgs_pending = 0
        self.offline_msgs_received = 0
        self.stop_event = threading.Event()
        self.deleted = False

        # BEFORE ANYTHING CONNECTS.
        remembered(self)

    def build_jid_to_name(self):
        jid_to_name = {c["id"]: c.get("name", c["id"].split("@")[0]) for c in self.chats}
        for c in self.contacts:
            cname = c.get("name")
            if cname and cname != c.get("number"):
                jid_to_name[c["id"]] = cname
            else:
                jid_to_name.setdefault(c["id"], c.get("name", c["id"].split("@")[0]))
        if self.phone:
            jid_to_name[f"{self.phone}@s.whatsapp.net"] = self.name or "Saved Messages"
        return jid_to_name

    def rebuild_latest_received(self):
        """Scan all stored messages once and set latest_received_message. Called on state load and after sync."""
        best = None
        best_ts = 0
        jid_to_name = self.build_jid_to_name()
        all_jids = set(self.messages.keys()) | set(self.media.keys())
        for jid in all_jids:
            if "@newsletter" in jid or "@broadcast" in jid:
                continue
            for store in (self.messages.get(jid, []), self.media.get(jid, [])):
                for m in store:
                    if not m.get("fromMe") and m.get("timestamp", 0) > best_ts and m.get("type") != "reaction":
                        best_ts = m["timestamp"]
                        best = {**m, "chatName": jid_to_name.get(jid, jid.split("@")[0]), "chatJid": jid}
        self.latest_received_message = best

    def rebuild_latest_sent(self):
        best = None
        best_ts = 0
        jid_to_name = self.build_jid_to_name()
        all_jids = set(self.messages.keys()) | set(self.media.keys())
        for jid in all_jids:
            if "@newsletter" in jid or "@broadcast" in jid:
                continue
            for store in (self.messages.get(jid, []), self.media.get(jid, [])):
                for m in store:
                    if not m.get("fromMe") or m.get("type") == "reaction":
                        continue
                    ts = m.get("timestamp", 0)
                    # ON A TIE THE MEDIA COPY WINS: THE TEXT ONE IS THE DEGRADED CAPTION.
                    is_better = ts > best_ts or (ts == best_ts and m.get("hasMedia") and best and not best.get("hasMedia"))
                    if is_better:
                        best_ts = ts
                        best = {**m, "chatName": jid_to_name.get(jid, jid.split("@")[0])}
        self.latest_sent_message = best

    def rebuild_group_senders(self):
        """Resolve group message sender JIDs from: 1."""
        name_to_jid = {}
        for c in self.contacts:
            cname = (c.get("name") or "").strip()
            cnum = (c.get("number") or "")
            if cname and cname != cnum:
                name_to_jid[cname.lower()] = c["id"]
        for g in self.groups:
            for p in g.get("participants", []):
                pname = (p.get("name") or "").strip()
                pnum = (p.get("number") or "")
                if pname and pname != pnum and p.get("id"):
                    name_to_jid.setdefault(pname.lower(), p["id"])

        fixed = 0
        for store_dict in (self.messages, self.media):
            for jid, msgs in store_dict.items():
                if "@g.us" not in jid:
                    continue
                for m in msgs:
                    if m.get("fromMe"):
                        continue
                    from_jid = m.get("fromJid", "")
                    sender_name = (m.get("from") or "").strip()

                    if "@lid" in from_jid:
                        resolved = self.lid_to_pn.get(from_jid)
                        if resolved:
                            m["fromJid"] = resolved
                            m["phoneNumber"] = resolved.split("@")[0] if "@" in resolved else None
                            for c in self.contacts:
                                if c["id"] == resolved:
                                    m["from"] = c.get("name") or resolved.split("@")[0]
                                    break
                            fixed += 1
                            continue

                    # fromJid STILL THE GROUP MEANS THE SENDER IS ONLY A pushName.
                    if from_jid != jid or not sender_name or sender_name == "unknown":
                        continue
                    matched_jid = name_to_jid.get(sender_name.lower())
                    if matched_jid:
                        m["fromJid"] = matched_jid
                        m["phoneNumber"] = matched_jid.split("@")[0] if "@" in matched_jid else None
                        fixed += 1
        if fixed:
            pass


sessions = {}
sessions_lock = threading.Lock()


def get_session(username):
    with sessions_lock:
        if username not in sessions:
            sessions[username] = Session(username)
        return sessions[username]


def format_message(session, message):
    info = message.Info
    src = info.MessageSource
    msg = message.Message

    chat_jid = resolve_lid(session, src.Chat)
    sender_jid = resolve_lid(session, src.Sender)
    from_me = src.IsFromMe
    msg_id = info.ID
    raw_ts = int(info.Timestamp)
    if raw_ts > 4102444800:  # PAST THE YEAR 2100, SO IT IS MILLISECONDS.
        raw_ts = raw_ts // 1000
    timestamp = raw_ts if 0 < raw_ts < 4102444800 else 0
    push_name = info.Pushname or ""

    phone_number = sender_jid.split("@")[0] if "@" in sender_jid else None
    if phone_number and (len(phone_number) > 15 or ":" in phone_number):
        phone_number = None

    if from_me:
        sender_name = session.name or session.phone or "Me"
    else:
        # A SAVED CONTACT NAME BEATS THE pushName.
        sender_name = "unknown"
        for c in session.contacts:
            if c["id"] == sender_jid:
                saved = c.get("name", "")
                num = c.get("number", "")
                if saved and saved != num:
                    sender_name = saved
                break
        if sender_name == "unknown":
            sender_name = push_name or (phone_number if phone_number else "unknown")

    body, msg_type, has_media, media_type = "", "chat", False, None
    filename, mime_type, file_size = None, None, 0

    if msg.conversation:
        body = msg.conversation
    elif msg.HasField('extendedTextMessage'):
        body = (msg.extendedTextMessage.text
                or getattr(msg.extendedTextMessage, 'matchedText', '')
                or getattr(msg.extendedTextMessage, 'title', '')
                or "")
    elif msg.HasField('imageMessage') and msg.imageMessage.URL:
        has_media, media_type, msg_type = True, "image", "image"
        body = msg.imageMessage.caption or ""
        mime_type = msg.imageMessage.mimetype or "image/jpeg"
        file_size = msg.imageMessage.fileLength or 0
    elif msg.HasField('videoMessage') and msg.videoMessage.URL:
        has_media, media_type, msg_type = True, "video", "video"
        body = msg.videoMessage.caption or ""
        mime_type = msg.videoMessage.mimetype or "video/mp4"
        file_size = msg.videoMessage.fileLength or 0
    elif msg.HasField('audioMessage') and msg.audioMessage.URL:
        has_media = True
        media_type = "audio" if not msg.audioMessage.PTT else "ptt"
        msg_type = "audio"
        mime_type = msg.audioMessage.mimetype or "audio/ogg"
        file_size = msg.audioMessage.fileLength or 0
    elif msg.HasField('documentMessage') and msg.documentMessage.URL:
        has_media, media_type, msg_type = True, "document", "document"
        body = msg.documentMessage.caption or ""
        filename = msg.documentMessage.fileName or None
        mime_type = msg.documentMessage.mimetype or "application/octet-stream"
        file_size = msg.documentMessage.fileLength or 0
    elif msg.HasField('stickerMessage') and msg.stickerMessage.URL:
        has_media, media_type, msg_type = True, "sticker", "sticker"
        mime_type = msg.stickerMessage.mimetype or "image/webp"
    elif msg.HasField('reactionMessage') and msg.reactionMessage.text:
        body = msg.reactionMessage.text
        msg_type = "reaction"
    elif getattr(msg, 'contactsArrayMessage', None) and getattr(msg.contactsArrayMessage, 'contacts', None):
        arr = msg.contactsArrayMessage
        body = contacts_array_name(arr)
        msg_type = "contact"
    elif msg.HasField('contactMessage'):
        cm = msg.contactMessage
        raw_dn = getattr(cm, 'displayName', "") or ""
        raw_vc = getattr(cm, 'vcard', "") or ""
        if raw_dn or raw_vc:
            body = contact_name(cm) or "[Contact]"
            msg_type = "contact"
    elif msg.HasField('locationMessage'):
        lat = msg.locationMessage.degreesLatitude
        lon = msg.locationMessage.degreesLongitude
        body = msg.locationMessage.name or msg.locationMessage.address or f"{lat},{lon}"
        msg_type = "location"
    elif msg.HasField('liveLocationMessage'):
        lat = msg.liveLocationMessage.degreesLatitude
        lon = msg.liveLocationMessage.degreesLongitude
        body = msg.liveLocationMessage.caption or f"{lat},{lon}"
        msg_type = "location"
    elif msg.HasField('pollCreationMessage'):
        body = msg.pollCreationMessage.name or "[Poll]"
        msg_type = "poll"
    # HasField, NOT getattr.
    elif msg.HasField('viewOnceMessage') and msg.viewOnceMessage.HasField('message'):
        body = ""
        msg_type = "viewonce"
        has_media = True
    elif msg.HasField('viewOnceMessageV2') and msg.viewOnceMessageV2.HasField('message'):
        body = ""
        msg_type = "viewonce"
        has_media = True
    # THE THIRD SHAPE A VIEW-ONCE HAS BEEN SENT IN, WHICH NOTHING HERE READ BEFORE.
    elif msg.HasField('viewOnceMessageV2Extension') and msg.viewOnceMessageV2Extension.HasField('message'):
        body = ""
        msg_type = "viewonce"
        has_media = True
    elif msg.HasField('protocolMessage'):
        return None

    # A FORWARD WRAPS ITS MEDIA INSIDE contextInfo, WHERE THE PASS ABOVE CANNOT SEE IT.
    if not body and not has_media:
        try:
            ctx = getattr(msg, 'contextInfo', None)
            if ctx:
                quoted = getattr(ctx, 'quotedMessage', None)
                if quoted:
                    if getattr(quoted, 'imageMessage', None):
                        has_media, media_type, msg_type = True, "image", "image"
                        body = getattr(quoted.imageMessage, 'caption', '') or ""
                        mime_type = getattr(quoted.imageMessage, 'mimetype', None) or "image/jpeg"
                        file_size = getattr(quoted.imageMessage, 'fileLength', 0) or 0
                    elif getattr(quoted, 'videoMessage', None):
                        has_media, media_type, msg_type = True, "video", "video"
                        body = getattr(quoted.videoMessage, 'caption', '') or ""
                        mime_type = getattr(quoted.videoMessage, 'mimetype', None) or "video/mp4"
                        file_size = getattr(quoted.videoMessage, 'fileLength', 0) or 0
                    elif getattr(quoted, 'audioMessage', None):
                        has_media, media_type, msg_type = True, "audio", "audio"
                        mime_type = getattr(quoted.audioMessage, 'mimetype', None) or "audio/ogg"
                        file_size = getattr(quoted.audioMessage, 'fileLength', 0) or 0
                    elif getattr(quoted, 'documentMessage', None):
                        has_media, media_type, msg_type = True, "document", "document"
                        body = getattr(quoted.documentMessage, 'caption', '') or ""
                        filename = getattr(quoted.documentMessage, 'fileName', None)
                        mime_type = getattr(quoted.documentMessage, 'mimetype', None) or "application/octet-stream"
                        file_size = getattr(quoted.documentMessage, 'fileLength', 0) or 0
                    elif getattr(quoted, 'stickerMessage', None):
                        has_media, media_type, msg_type = True, "sticker", "sticker"
                        mime_type = getattr(quoted.stickerMessage, 'mimetype', None) or "image/webp"
        except Exception:
            pass

    elif msg.HasField('editedMessage') and msg.editedMessage.message:
        edited = msg.editedMessage.message
        if edited.conversation:
            body = edited.conversation
        elif edited.HasField('extendedTextMessage') and edited.extendedTextMessage.text:
            body = edited.extendedTextMessage.text
        elif edited.HasField('imageMessage'):
            body = edited.imageMessage.caption or ""
        msg_type = "chat"

    # A MESSAGE THE CHAIN ABOVE HAD NO BRANCH FOR IS STORED EMPTY AND READS AS NOTHING
    # HAPPENING.
    if not body and not has_media and msg_type == "chat":
        carried = ", ".join(sorted(field.name for field, _ in msg.ListFields())) or "nothing"

        # A POLL, AN EVENT, A PAYMENT OR A VIDEO NOTE, WHICH THE CHAIN ABOVE HAS NO BRANCH
        # FOR AND WHICH ARE STILL THINGS SOMEBODY SENT.
        body, kind = otherwise(msg)

        if kind == "ptv":
            has_media, media_type, msg_type = True, "video", "video"
            mime_type = getattr(msg.ptvMessage, "mimetype", None) or "video/mp4"
            file_size = getattr(msg.ptvMessage, "fileLength", 0) or 0
        elif kind:
            msg_type = kind

        # NOBODY SENT IT, SO IT IS NOT KEPT AND NOT COUNTED. None IS ALREADY WHAT THIS
        # RETURNS FOR A protocolMessage AND EVERY CALLER KNOWS TO DROP IT.
        if not body and not has_media and nobody_said_it(msg):
            return None

        if not body and not has_media:
            logger.info(f"[message] user={session.username} nothing readable in: {carried}")

    display_phone = session.phone if from_me else (phone_number if phone_number and len(phone_number) <= 15 else None)

    return {
        "id": msg_id, "from": clean(sender_name),
        "phoneNumber": display_phone, "fromJid": sender_jid,
        "fromMe": from_me, "type": msg_type, "body": clean(body),
        "timestamp": timestamp,
        "time": datetime.utcfromtimestamp(timestamp).isoformat() + "Z" if timestamp else None,
        "hasMedia": has_media, "mediaType": media_type,
        "filename": filename, "mimeType": mime_type, "fileSize": file_size,
    }


def register_events(session):
    client = session.client

    @client.event.qr
    def on_qr(c, data_qr):
        try:
            qr = segno.make_qr(data_qr)
            buf = io.BytesIO()
            qr.save(buf, kind="png", scale=8, border=2)
            b64 = base64.b64encode(buf.getvalue()).decode()
            session.qr_data = f"data:image/png;base64,{b64}"
            # WHEN, NOT JUST WHAT: THE PAGE HAS NO OTHER WAY TO TELL THAT THE
            # CODE IT IS SHOWING HAS DIED. THE FIRST OF A RUN OUTLIVES THE REST.
            session.qr_life = QR_LATER if session.qr_at else QR_FIRST
            session.qr_at = time.time()
            session.authenticated = False
            session.qr_count = getattr(session, "qr_count", 0) + 1
            logger.info(
                f"[qr] user={session.username} new code #{session.qr_count}, "
                f"good for {session.qr_life}s"
            )
        except Exception as e:
            logger.warning(f"[qr] user={session.username} code could not be drawn: {e}")

    @client.event(ConnectedEv)
    def on_connected(c, evt):
        pass
        session.connected = True
        session.authenticated = True
        session.qr_data = None
        session.reconnect_count = 0

        old_phone = session.phone
        try:
            me = c.get_me()
            j = jid_str(me.JID)
            raw_phone = j.split("@")[0] if "@" in j else None
            new_phone = raw_phone.split(":")[0] if raw_phone and ":" in raw_phone else raw_phone
            session.phone = new_phone
            session.name = me.PushName or new_phone

            if old_phone and new_phone and old_phone != new_phone:
                pass
                with session.lock:
                    session.contacts = []
                    session.chats = []
                    session.groups = []
                    session.messages = {}
                    session.media = {}
                    session.raw_messages = {}
                    session.lid_name_map = {}
                    session.lid_to_pn = {}
                    session.latest_received_message = None
                    session.latest_sent_message = None
        except Exception as e:
            pass

        session.do_sync_done = False
        session.contacts_enriched = False
        session.last_history_sync_at = 0
        session.sync_status.update({
            "syncing": True, "phase": "syncing", "error": None,
            "startedAt": datetime.utcnow().isoformat() + "Z",
            "completedAt": None, "message": "Waiting for WhatsApp data...",
        })

        try:
            c.set_passive(False)
        except Exception as e:
            pass

        def delayed_sync():
            time.sleep(5)
            do_sync(session)
        threading.Thread(target=delayed_sync, daemon=True).start()

    @client.event(DisconnectedEv)
    def on_disconnected(c, evt):
        pass
        session.connected = False
        session.qr_data = None

        if session.stop_event.is_set():
            return
        persist(session)
        if session.reconnect_count < session.max_reconnect:
            session.reconnect_count += 1
            delay = min(3 * session.reconnect_count, 30)
            pass
            threading.Timer(delay, lambda: start_session(session)).start()
        else:
            session.reconnect_count = 0
            pass
            threading.Timer(30, lambda: start_session(session)).start()

    @client.event(LoggedOutEv)
    def on_logged_out(c, evt):
        pass
        session.connected = False
        session.authenticated = False
        session.qr_data = None
        for ext in ["", "-wal", "-shm"]:
            try:
                os.remove(session.db_path + ext)
            except Exception:
                pass
        if not session.stop_event.is_set() and not session.deleted:
            pass
            session.client = None
            session.connect_thread = None
            os.execv(sys.executable, [sys.executable] + sys.argv)

    @client.event(MessageEv)
    def on_message(c, message):
        try:
            handle_message(session, message)
        except Exception as e:
            pass

    @client.event(HistorySyncEv)
    def on_history_sync(c, evt):
        try:
            handle_history_sync(session, evt)
        except Exception as e:
            pass

    @client.event(OfflineSyncPreviewEv)
    def on_offline_preview(c, evt):
        count = getattr(evt, 'Message', 0)
        session.offline_msgs_pending = count
        session.offline_msgs_received = 0
        pass

    @client.event(OfflineSyncCompletedEv)
    def on_offline_completed(c, evt):
        count = getattr(evt, 'Count', 0)
        pass
        session.offline_msgs_pending = 0
        session.offline_msgs_received = 0
        persist(session)

    @client.event(ReceiptEv)
    def on_receipt(c, evt):
        try:
            if evt.Type not in RECEIPTS_THAT_CLEAR_UNREAD:
                return
            chat_jid = resolve_lid(session, evt.MessageSource.Chat)
            with session.lock:
                cidx = next((i for i, ch in enumerate(session.chats) if ch["id"] == chat_jid), -1)
                if cidx >= 0 and session.chats[cidx].get("unreadCount", 0) > 0:
                    session.chats[cidx]["unreadCount"] = 0
        except Exception:
            pass


def handle_message(session, message):
    entry = format_message(session, message)
    if not entry:
        return
    chat_jid = resolve_lid(session, message.Info.MessageSource.Chat)
    if not chat_jid or "@broadcast" in chat_jid:
        return

    if session.offline_msgs_pending > 0:
        session.offline_msgs_received += 1
        pass

    with session.lock:
        if chat_jid not in session.messages:
            session.messages[chat_jid] = []
        if chat_jid not in session.media:
            session.media[chat_jid] = []

        if not entry["fromMe"] and entry["fromJid"]:
            existing = next((i for i, c in enumerate(session.contacts) if c["id"] == entry["fromJid"]), -1)
            if existing < 0:
                session.contacts.append({
                    "id": entry["fromJid"],
                    "name": entry["from"] if entry["from"] != "unknown" else entry["fromJid"].split("@")[0],
                    "number": entry["phoneNumber"] or entry["fromJid"].split("@")[0],
                    "status": "",
                })
            elif entry["from"] and entry["from"] != "unknown":
                # A STORED NAME THAT IS THE PHONE NUMBER WAS NEVER A REAL NAME.
                existing_name = session.contacts[existing].get("name", "")
                existing_num = session.contacts[existing].get("number", "")
                if not existing_name or existing_name == existing_num:
                    session.contacts[existing]["name"] = entry["from"]
            if entry["from"] and entry["from"] != "unknown":
                session.lid_name_map[entry["from"].lower()] = entry["fromJid"]

        is_group = "@g.us" in chat_jid
        cidx_pre = next((i for i, c in enumerate(session.chats) if c["id"] == chat_jid), -1)
        if cidx_pre < 0:
            if is_group:
                group = next((g for g in session.groups if g.get("id") == chat_jid), None)
                chat_name = group["name"] if group else chat_jid.split("@")[0]
            else:
                chat_name = entry["from"]
                if entry["fromMe"]:
                    contact = next((c for c in session.contacts if c["id"] == chat_jid), None)
                    chat_name = contact["name"] if contact else chat_jid.split("@")[0]
            session.chats.append({"id": chat_jid, "name": chat_name, "isGroup": is_group, "unreadCount": 0, "lastMessage": entry["body"], "timestamp": entry["timestamp"], "lastMessageFromMe": entry["fromMe"], "lastMessageFrom": session.name if entry["fromMe"] else entry["from"]})

        if entry["hasMedia"]:
            store = session.media[chat_jid]
            session.raw_messages[entry["id"]] = message
            # THE SAME MESSAGE MUST NEVER SIT IN BOTH STORES.
            session.messages[chat_jid] = [m for m in session.messages[chat_jid] if m["id"] != entry["id"]]
        else:
            store = session.messages[chat_jid]
            # THE TEXT COPY IS THE DEGRADED ONE, SO IT NEVER OVERWRITES MEDIA.
            if any(m["id"] == entry["id"] for m in session.media[chat_jid]):
                store = None

        if store is not None:
            eidx = next((i for i, m in enumerate(store) if m["id"] == entry["id"]), -1)
            if eidx >= 0:
                store[eidx] = entry
            else:
                store.append(entry)

        cidx = next((i for i, c in enumerate(session.chats) if c["id"] == chat_jid), -1)
        if cidx >= 0:
            # A STICKER OR A PHOTO HAS NO BODY, AND A BLANK LAST LINE TELLS HIM NOTHING.
            session.chats[cidx]["lastMessage"] = entry["body"] or SHOWN.get(entry.get("mediaType") or entry.get("type"), "")
            session.chats[cidx]["timestamp"] = entry["timestamp"]
            # THE BADGE ONLY EVER MEANT MESSAGES SOMEBODY ELSE SENT AND HE HAS NOT READ.
            if entry["fromMe"]:
                session.chats[cidx]["unreadCount"] = 0
            elif entry.get("type") != "reaction":
                session.chats[cidx]["unreadCount"] = session.chats[cidx].get("unreadCount", 0) + 1
            # WHO SENT THE LAST ONE IS THE HALF OF "LAST MESSAGE" THAT WAS MISSING.
            session.chats[cidx]["lastMessageFromMe"] = entry["fromMe"]
            session.chats[cidx]["lastMessageFrom"] = session.name if entry["fromMe"] else entry["from"]

        # KEPT CURRENT HERE SO READING THE NEWEST NEVER SCANS EVERY CHAT.
        if entry.get("type") != "reaction" and not any(x in chat_jid for x in ("@newsletter", "@broadcast")):
            ts = entry.get("timestamp", 0)
            if session.phone and chat_jid == f"{session.phone}@s.whatsapp.net":
                chat_name = session.name or "Saved Messages"
            elif "@g.us" not in chat_jid and "@lid" not in chat_jid:
                contact = next((c for c in session.contacts if c["id"] == chat_jid), None)
                if contact and contact.get("name") and contact["name"] != contact.get("number"):
                    chat_name = contact["name"]
                else:
                    chat_name = (session.chats[cidx]["name"] if cidx >= 0 else None) or entry["from"] or chat_jid.split("@")[0]
            else:
                chat_name = (session.chats[cidx]["name"] if cidx >= 0 else None) or entry["from"] or chat_jid.split("@")[0]
            if entry["fromMe"]:
                cur_ts = session.latest_sent_message.get("timestamp", 0) if session.latest_sent_message else 0
                if ts and ts > cur_ts:
                    session.latest_sent_message = {**entry, "chatName": chat_name}
                # ONE SLOT ONLY EVER HOLDS THE LAST.
                session.recent_sent = [m for m in session.recent_sent if m["id"] != entry["id"]]
                session.recent_sent.append({**entry, "chatName": chat_name, "chatJid": chat_jid})
                del session.recent_sent[:-RECENT_SENT]
            else:
                cur_ts = session.latest_received_message.get("timestamp", 0) if session.latest_received_message else 0
                if ts and ts > cur_ts:
                    session.latest_received_message = {**entry, "chatName": chat_name, "chatJid": chat_jid}

    if session.persist_timer:
        session.persist_timer.cancel()
    session.persist_timer = threading.Timer(5, persist, args=(session,))
    session.persist_timer.daemon = True
    session.persist_timer.start()

    if entry["hasMedia"]:
        threading.Thread(target=auto_download, args=(session, message, entry), daemon=True).start()



def auto_download_history(session, web_msg, entry):
    """Auto-download media from history-synced messages (WebMessageInfo objects)."""
    try:
        mid = entry.get("id", "")
        if mid in session.downloaded_media:
            return
        ext = (entry.get("mimeType") or "application/octet-stream").split("/")[-1].split(";")[0]
        fname = entry.get("filename") or f"{mid}.{ext}"
        local_path = os.path.join(session.dl_dir, fname)
        if os.path.exists(local_path):
            with session.lock:
                session.downloaded_media[mid] = {"local_path": local_path, "filename": fname, "mime": entry.get("mimeType", "application/octet-stream"), "size": os.path.getsize(local_path)}
                needs_persist = False
                for msgs in session.media.values():
                    for m in msgs:
                        if m.get("id") == mid and not m.get("filename"):
                            m["filename"] = fname
                            needs_persist = True
            if needs_persist:
                persist(session)
            return
        msg_proto = getattr(web_msg, 'message', None) or web_msg
        media_bytes = session.client.download_any(msg_proto)
        if not media_bytes:
            session.failed_downloads.add(mid)
            pass
            return
        with open(local_path, "wb") as f:
            f.write(media_bytes)
        with session.lock:
            session.downloaded_media[mid] = {"local_path": local_path, "filename": fname, "mime": entry.get("mimeType", "application/octet-stream"), "size": len(media_bytes)}
            for msgs in session.media.values():
                for m in msgs:
                    if m.get("id") == mid and not m.get("filename"):
                        m["filename"] = fname
        persist(session)
        pass
    except Exception as e:
        session.failed_downloads.add(mid)
        pass


def auto_download(session, message, entry):
    try:
        media_bytes = session.client.download_any(message.Message)
        if not media_bytes:
            return
        ext = (entry.get("mimeType") or "application/octet-stream").split("/")[-1].split(";")[0]
        fname = entry.get("filename") or f"{entry['id']}.{ext}"
        local_path = os.path.join(session.dl_dir, fname)
        with open(local_path, "wb") as f:
            f.write(media_bytes)
        mid = entry["id"]
        with session.lock:
            session.downloaded_media[mid] = {"local_path": local_path, "filename": fname, "mime": entry.get("mimeType", "application/octet-stream"), "size": len(media_bytes)}
            for msgs in session.media.values():
                for m in msgs:
                    if m.get("id") == mid and not m.get("filename"):
                        m["filename"] = fname
        persist(session)
    except Exception:
        pass




























# WHAT WHATSAPP SENDS ITSELF RATHER THAN SENDING FOR SOMEBODY: KEY HANDOVER, A VOTE ON
# SOMEONE ELSE'S POLL, A BARE CONTEXT HEADER. THESE WERE STORED AS EMPTY "chat" LINES AND
# COUNTED AS MESSAGES, SO A GROUP READ BACK AS FORTY-TWO UNREAD WITH NOTHING IN ANY OF THEM
# AND THE NEWEST ONE HAD TO BE DESCRIBED AS "an empty message". THEY ARE NOT MESSAGES.
UNSPOKEN = {"senderKeyDistributionMessage", "messageContextInfo",
            "protocolMessage", "keepInChatMessage"}


def said_something(entry):
    """TRUE WHEN A STORED LINE HAS ANYTHING IN IT FOR A PERSON TO HEAR.

    ONLY A PLAIN "chat" WITH NEITHER WORDS NOR MEDIA IS DROPPED. A viewonce, A LOCATION, A
    POLL AND THE REST ALL SAY WHAT THEY ARE IN type EVEN WHEN body IS EMPTY, AND THROWING
    ONE OF THOSE AWAY WOULD LOSE A REAL MESSAGE TO FIX A FAKE ONE."""
    if entry.get("body") or entry.get("hasMedia"):
        return True

    return entry.get("type") != "chat"


# EVERY SHAPE A POLL HAS BEEN SENT IN. WHATSAPP MADE A NEW ONE EACH TIME IT CHANGED POLLS,
# AND ONLY THE FIRST WAS EVER READ HERE, SO A POLL SENT BY A CURRENT PHONE WENT INTO THE
# STORE AS A BLANK LINE AND CAME BACK OUT AS "an empty message".
POLLS = ("pollCreationMessage", "pollCreationMessageV2", "pollCreationMessageV3",
         "pollCreationMessageV4", "pollCreationMessageV5", "pollCreationMessageV6")

# WHAT A MESSAGE NOBODY WROTE WORDS INTO IS CALLED WHEN IT IS SAID OUT LOUD. A POLL IS ITS
# QUESTION, AN EVENT ITS TITLE; THE REST HAVE NO NAME OF THEIR OWN AND ARE SAID AS WHAT THEY
# ARE, THE SAME WAY A STICKER IS.
NAMED = {
    "eventMessage": "[event: {name}]",
    "pollResultSnapshotMessage": "[poll results]",
    "pollResultSnapshotMessageV3": "[poll results]",
    "albumMessage": "[album]",
    "sendPaymentMessage": "[payment]",
    "requestPaymentMessage": "[payment request]",
    "paymentReminderMessage": "[payment reminder]",
    "paymentInviteMessage": "[payment invite]",
    "splitPaymentMessage": "[split payment]",
    "declinePaymentRequestMessage": "[payment request declined]",
    "cancelPaymentRequestMessage": "[payment request cancelled]",
    "eventInviteMessage": "[event invite]",
}


def otherwise(msg):
    """WHAT THIS MESSAGE SAYS WHEN THE MAIN CHAIN HAD NO BRANCH FOR IT, AND ITS KIND.

    A POLL, AN EVENT, A VIDEO NOTE OR A PAYMENT IS A REAL THING SOMEBODY SENT. STORING ONE
    AS AN EMPTY LINE IS WHAT MADE A GROUP READ BACK AS FORTY-TWO MESSAGES WITH NOTHING IN
    ANY OF THEM."""
    for name in POLLS:
        if msg.HasField(name):
            asked = getattr(getattr(msg, name), "name", "") or ""

            return (f"[poll: {asked}]" if asked else "[poll]"), "poll"

    if msg.HasField("pollUpdateMessage"):
        return "[a vote on a poll]", "poll"

    if msg.HasField("pollAddOptionMessage"):
        return "[an option added to a poll]", "poll"

    # A VIDEO NOTE IS THE ROUND ONE, AND IT IS MEDIA LIKE ANY OTHER VIDEO.
    if msg.HasField("ptvMessage") and getattr(msg.ptvMessage, "URL", ""):
        return getattr(msg.ptvMessage, "caption", "") or "[video note]", "ptv"

    for name, shown in NAMED.items():
        if msg.HasField(name):
            titled = getattr(getattr(msg, name), "name", "") or ""

            return shown.format(name=titled) if "{name}" in shown else shown, "event" if "event" in name else "chat"

    return "", ""


def nobody_said_it(msg):
    """TRUE WHEN EVERY FIELD ON THIS MESSAGE IS WHATSAPP'S OWN PLUMBING."""
    carried = {field.name for field, _ in msg.ListFields()}

    return bool(carried) and carried <= UNSPOKEN


# WHAT A CHAT WHOSE LAST WORD WAS A PICTURE SAYS INSTEAD OF NOTHING.
SHOWN = {
    "image": "[photo]", "video": "[video]", "audio": "[voice message]",
    "ptt": "[voice message]", "sticker": "[sticker]", "document": "[document]",
    "viewonce": "[view once]",
}


def previewed(session, chat, chat_id):
    """THE CHAT'S LAST LINE, TAKEN FROM THE NEWEST MESSAGE ACTUALLY STORED."""
    newest = None

    for message in session.messages.get(chat_id, []) + session.media.get(chat_id, []):
        if message.get("type") == "reaction":
            continue

        if newest is None or message.get("timestamp", 0) >= newest.get("timestamp", 0):
            newest = message

    if newest is None:
        return

    chat["lastMessage"] = newest.get("body") or SHOWN.get(newest.get("mediaType") or newest.get("type"), "")
    # WITHOUT THESE THE LAST LINE READS AS THEIRS EVEN WHEN HE WROTE IT HIMSELF.
    chat["lastMessageFromMe"] = bool(newest.get("fromMe"))
    chat["lastMessageFrom"] = session.name if newest.get("fromMe") else newest.get("from")

    if newest.get("timestamp", 0) > chat.get("timestamp", 0):
        chat["timestamp"] = newest["timestamp"]

    # A BADGE ON A CHAT WHOSE NEWEST LINE HE WROTE HIMSELF IS LEFT OVER FROM AN OLD
    # SYNC: HE ANSWERED, SO THERE IS NOTHING OF THEIRS LEFT UNREAD UNDER IT.
    if newest.get("fromMe") and chat.get("unreadCount", 0) > 0:
        chat["unreadCount"] = 0


def handle_history_sync(session, evt):
    data = evt.Data
    sync_type = getattr(data, 'syncType', -1)
    progress = getattr(data, 'progress', 0)
    conversations = list(getattr(data, 'conversations', []))
    pushnames = list(getattr(data, 'pushnames', []))

    # TALLIED RATHER THAN LOGGED ONE BY ONE: A BUNDLE CARRIES THOUSANDS.
    unreadable = {}

    with session.lock:
        session.last_history_sync_at = time.time()
        session.sync_status["syncing"] = True
        session.sync_status["phase"] = "syncing"
        session.sync_status["message"] = f"Receiving message history ({progress}%)..."

        for pn in pushnames:
            pn_id = getattr(pn, 'id', "")
            pn_name = getattr(pn, 'pushname', "")
            if not pn_id or not pn_name:
                continue
            jid = f"{pn_id}@s.whatsapp.net" if "@" not in pn_id else pn_id
            existing = next((i for i, c in enumerate(session.contacts) if c["id"] == jid), -1)
            if existing < 0:
                session.contacts.append({"id": jid, "name": clean(pn_name), "number": pn_id.split("@")[0], "status": ""})
            elif pn_name:
                # A STORED NAME THAT IS THE PHONE NUMBER WAS NEVER A REAL NAME.
                existing_name = session.contacts[existing].get("name", "")
                existing_num = session.contacts[existing].get("number", "")
                if not existing_name or existing_name == existing_num:
                    session.contacts[existing]["name"] = clean(pn_name)
            if pn_name:
                session.lid_name_map[pn_name.lower()] = jid

        for conv in conversations:
            raw_chat_id = getattr(conv, 'ID', "")
            if not raw_chat_id or "@broadcast" in raw_chat_id:
                continue
            chat_id = resolve_lid_str(session, raw_chat_id)
            is_group = "@g.us" in chat_id
            unread_count = getattr(conv, 'unreadCount', 0)
            conv_name = getattr(conv, 'displayName', chat_id.split("@")[0])
            archived = bool(getattr(conv, 'archived', False))

            raw_last_msg_ts = getattr(conv, 'lastMsgTimestamp', 0)
            raw_conv_ts = getattr(conv, 'conversationTimestamp', 0)
            conv_ts = int(raw_last_msg_ts or raw_conv_ts or 0)
            if not (0 < conv_ts < 4102444800):
                conv_ts = 0

            cidx = next((i for i, c in enumerate(session.chats) if c["id"] == chat_id), -1)
            if cidx < 0:
                session.chats.append({"id": chat_id, "name": clean(conv_name) or chat_id.split("@")[0], "isGroup": is_group, "unreadCount": unread_count, "lastMessage": "", "timestamp": conv_ts, "archived": archived})
                cidx = len(session.chats) - 1
            else:
                if conv_ts and conv_ts > session.chats[cidx].get("timestamp", 0):
                    session.chats[cidx]["timestamp"] = conv_ts
                session.chats[cidx]["archived"] = archived
                # THE PHONE IS THE AUTHORITY ON WHAT IS STILL UNREAD. WITHOUT THIS A COUNT
                # FROM AN OLD SYNC OUTLIVES THE MESSAGES IT WAS COUNTING.
                session.chats[cidx]["unreadCount"] = unread_count
            if chat_id not in session.messages:
                session.messages[chat_id] = []
            if chat_id not in session.media:
                session.media[chat_id] = []

            for hist_msg in list(getattr(conv, 'messages', [])):
                try:
                    web_msg = getattr(hist_msg, 'message', None)
                    if not web_msg:
                        continue
                    key = getattr(web_msg, 'key', None)
                    if not key:
                        continue
                    msg_id = getattr(key, 'ID', "")
                    from_me = getattr(key, 'fromMe', False)
                    remote_jid = str(getattr(key, 'remoteJID', ""))
                    participant = str(getattr(key, 'participant', ""))
                    web_participant = str(getattr(web_msg, 'participant', ""))
                    if is_group and not participant and web_participant:
                        participant = web_participant
                    raw_ts = int(getattr(web_msg, 'messageTimestamp', 0) or getattr(web_msg, 'messageC2STimestamp', 0) or 0)
                    ts = raw_ts if 0 < raw_ts < 4102444800 else conv_ts
                    sender_jid = participant if is_group and participant else remote_jid
                    sender_jid = resolve_lid_str(session, sender_jid) if sender_jid else sender_jid
                    # AN UNRESOLVED LID IS KEPT AS fromJid SO A LATER PASS CAN RESOLVE IT.
                    is_lid_sender = sender_jid and "@lid" in str(sender_jid)
                    phone = sender_jid.split("@")[0] if "@" in str(sender_jid) and not is_lid_sender else None

                    actual_msg = getattr(web_msg, 'message', None)
                    body, msg_type, has_media, media_type_val = "", "chat", False, None
                    fname, mime, fsize = None, None, 0
                    if actual_msg:
                        if actual_msg.conversation:
                            body = actual_msg.conversation
                        elif actual_msg.HasField('extendedTextMessage'):
                            etm = actual_msg.extendedTextMessage
                            body = (getattr(etm, 'text', '') or getattr(etm, 'matchedText', '') or getattr(etm, 'title', '') or "")
                        elif actual_msg.HasField('imageMessage'):
                            img = actual_msg.imageMessage
                            msg_type, media_type_val = "image", "image"
                            has_media = bool(getattr(img, 'URL', ""))
                            body = getattr(img, 'caption', "") or ""
                            mime = getattr(img, 'mimetype', None) or "image/jpeg"
                            fsize = getattr(img, 'fileLength', 0) or 0
                        elif actual_msg.HasField('videoMessage'):
                            vid = actual_msg.videoMessage
                            msg_type, media_type_val = "video", "video"
                            has_media = bool(getattr(vid, 'URL', ""))
                            body = getattr(vid, 'caption', "") or ""
                            mime = getattr(vid, 'mimetype', None) or "video/mp4"
                            fsize = getattr(vid, 'fileLength', 0) or 0
                        elif actual_msg.HasField('documentMessage'):
                            doc = actual_msg.documentMessage
                            msg_type, media_type_val = "document", "document"
                            has_media = bool(getattr(doc, 'URL', ""))
                            body = getattr(doc, 'caption', "") or ""
                            fname = getattr(doc, 'fileName', None)
                            mime = getattr(doc, 'mimetype', None) or "application/octet-stream"
                            fsize = getattr(doc, 'fileLength', 0) or 0
                        elif actual_msg.HasField('audioMessage'):
                            aud = actual_msg.audioMessage
                            msg_type, media_type_val = "audio", "audio"
                            has_media = bool(getattr(aud, 'URL', ""))
                            mime = getattr(aud, 'mimetype', None) or "audio/ogg"
                            fsize = getattr(aud, 'fileLength', 0) or 0
                        elif actual_msg.HasField('stickerMessage'):
                            stk = actual_msg.stickerMessage
                            msg_type, media_type_val = "sticker", "sticker"
                            has_media = bool(getattr(stk, 'URL', ""))
                            mime = getattr(stk, 'mimetype', None) or "image/webp"
                        elif actual_msg.HasField('reactionMessage') and actual_msg.reactionMessage.text:
                            body = actual_msg.reactionMessage.text; msg_type = "reaction"
                        elif getattr(actual_msg, 'contactsArrayMessage', None) and getattr(actual_msg.contactsArrayMessage, 'contacts', None):
                            body = contacts_array_name(actual_msg.contactsArrayMessage); msg_type = "contact"
                        elif actual_msg.HasField('contactMessage'):
                            cm = actual_msg.contactMessage
                            raw_dn = getattr(cm, 'displayName', "") or ""
                            raw_vc = getattr(cm, 'vcard', "") or ""
                            if raw_dn or raw_vc:
                                body = contact_name(cm) or "[Contact]"; msg_type = "contact"
                        elif actual_msg.HasField('locationMessage'):
                            lat = actual_msg.locationMessage.degreesLatitude; lon = actual_msg.locationMessage.degreesLongitude
                            body = getattr(actual_msg.locationMessage, 'name', '') or getattr(actual_msg.locationMessage, 'address', '') or f"{lat},{lon}"; msg_type = "location"
                        elif actual_msg.HasField('pollCreationMessage'):
                            body = actual_msg.pollCreationMessage.name or "[Poll]"; msg_type = "poll"
                        elif actual_msg.HasField('editedMessage') and actual_msg.editedMessage.message:
                            edited = actual_msg.editedMessage.message
                            if edited.conversation: body = edited.conversation
                            elif edited.HasField('extendedTextMessage') and edited.extendedTextMessage.text: body = edited.extendedTextMessage.text
                            elif edited.HasField('imageMessage'): body = edited.imageMessage.caption or ""
                        # A VIEW-ONCE IN SYNCED HISTORY WAS READ BY NOTHING AT ALL AND WENT
                        # IN AS A BLANK LINE, IN ALL THREE OF THE SHAPES IT IS SENT IN.
                        elif any(actual_msg.HasField(each) and getattr(actual_msg, each).HasField('message')
                                 for each in ("viewOnceMessage", "viewOnceMessageV2",
                                              "viewOnceMessageV2Extension")):
                            msg_type, has_media = "viewonce", True
                        elif actual_msg.HasField('protocolMessage'):
                            continue

                    # THE SAME BLIND SPOT AS THE LIVE PARSE, NAMED THE SAME WAY.
                    if actual_msg and not body and not has_media and msg_type == "chat":
                        carried = ", ".join(sorted(f.name for f, _ in actual_msg.ListFields())) or "nothing"

                        # THE SAME READING OF A POLL, AN EVENT OR A PAYMENT. THE FORTY-TWO
                        # UNREAD IN THE PG GROUP CAME DOWN THIS PATH, NOT THE LIVE ONE.
                        body, kind = otherwise(actual_msg)

                        if kind == "ptv":
                            has_media, media_type_val, msg_type = True, "video", "video"
                            mime = getattr(actual_msg.ptvMessage, "mimetype", None) or "video/mp4"
                            fsize = getattr(actual_msg.ptvMessage, "fileLength", 0) or 0
                        elif kind:
                            msg_type = kind

                        if not body and not has_media:
                            if nobody_said_it(actual_msg):
                                continue

                            unreadable[carried] = unreadable.get(carried, 0) + 1

                    push_name_hist = str(getattr(web_msg, 'pushName', "") or "")
                    sender_name = "unknown"
                    if from_me:
                        sender_name = session.name or session.phone or "Me"
                    elif phone and not (is_group and sender_jid == chat_id):
                        for c in session.contacts:
                            if c["id"] == str(sender_jid) or c.get("number") == phone:
                                sender_name = c.get("name", phone); break
                        if sender_name == "unknown":
                            sender_name = push_name_hist or phone
                    elif is_group and not participant and push_name_hist:
                        # NO PARTICIPANT JID, SO THE pushName IS ALL A NAME FILTER HAS.
                        sender_name = push_name_hist
                        resolved_jid = session.lid_name_map.get(push_name_hist.lower())
                        if resolved_jid:
                            sender_jid = resolved_jid
                            phone = resolved_jid.split("@")[0]

                    entry = {"id": msg_id, "from": clean(sender_name), "phoneNumber": session.phone if from_me else phone, "fromJid": str(sender_jid) if sender_jid else chat_id, "fromMe": from_me, "type": msg_type, "body": clean(body), "timestamp": ts, "time": datetime.utcfromtimestamp(ts).isoformat() + "Z" if ts else None, "hasMedia": has_media, "mediaType": media_type_val, "filename": fname, "mimeType": mime, "fileSize": fsize}
                    if has_media and msg_id:
                        session.raw_messages[msg_id] = web_msg
                        cutoff = time.time() - 14 * 86400
                        if ts and ts > cutoff:
                            threading.Thread(target=auto_download_history, args=(session, web_msg, entry), daemon=True).start()
                        store = session.media[chat_id]
                        # THE SAME MESSAGE MUST NEVER SIT IN BOTH STORES.
                        session.messages[chat_id] = [m for m in session.messages[chat_id] if m["id"] != msg_id]
                    else:
                        store = session.messages[chat_id]
                        # THE TEXT COPY IS THE DEGRADED ONE, SO IT NEVER OVERWRITES MEDIA.
                        if any(m["id"] == msg_id for m in session.media[chat_id]):
                            continue
                    eidx = next((i for i, m in enumerate(store) if m["id"] == msg_id), -1)
                    if eidx >= 0:
                        store[eidx] = entry
                    else:
                        store.append(entry)
                    if msg_type != "reaction" and ts and not any(x in chat_id for x in ("@newsletter", "@broadcast")):
                        chat_name = session.chats[cidx].get("name", chat_id.split("@")[0])
                        if from_me:
                            cur = session.latest_sent_message
                            if cur is None or ts > cur.get("timestamp", 0) or cur.get("id") == msg_id:
                                session.latest_sent_message = {**entry, "chatName": chat_name}
                        else:
                            cur = session.latest_received_message
                            if cur is None or ts > cur.get("timestamp", 0) or cur.get("id") == msg_id:
                                session.latest_received_message = {**entry, "chatName": chat_name, "chatJid": chat_id}
                except Exception:
                    continue
            session.messages[chat_id].sort(key=lambda m: m.get("timestamp", 0))
            session.media[chat_id].sort(key=lambda m: m.get("timestamp", 0))
            previewed(session, session.chats[cidx], chat_id)

        session.sync_status["contacts"] = len(session.contacts)
        session.sync_status["chats"] = len(session.chats)
        session.sync_status["groups"] = len(session.groups)

    for carried, many in sorted(unreadable.items(), key=lambda pair: -pair[1]):
        logger.info(f"[history] user={session.username} {many} with nothing readable in: {carried}")

    persist(session)


def enrich_contacts_from_store(session):
    if session.contacts_enriched or not session.client or not session.connected:
        return
    try:
        store_contacts = session.client.contact.get_all_contacts()
    except Exception as e:
        pass
        return
    with session.lock:
        existing_ids = {c["id"] for c in session.contacts}
        for sc in store_contacts:
            cid = jid_str(sc.JID)
            info = sc.Info
            # THE PHONE BOOK WINS: SOMEBODY SAVED AS "john" IS ASKED FOR AS "john",
            # NOT BY WHATEVER THEY CALL THEMSELVES ON WHATSAPP.
            phone_book_name = info.FullName or info.FirstName or ""
            name = phone_book_name or info.PushName or info.BusinessName or ""
            number = cid.split("@")[0] if "@" in cid else ""
            if cid in existing_ids:
                if name:
                    for c in session.contacts:
                        if c["id"] == cid:
                            if phone_book_name or not c.get("name") or c["name"] == c.get("number"):
                                c["name"] = clean(name)
                            break
            else:
                if not name:
                    name = number or cid
                session.contacts.append({"id": cid, "name": clean(name), "number": number, "status": ""})
                existing_ids.add(cid)
    if store_contacts:
        session.contacts_enriched = True


def bulk_resolve_group_lids(session):
    """For every @lid participant across all groups, call get_pn_from_lid and cache the result."""
    if not session.client or not session.connected:
        return
    lid_set = set()
    with session.lock:
        for g in session.groups:
            for p in g.get("participants", []):
                pid = p.get("id", "")
                if pid and "@lid" in pid and pid not in session.lid_to_pn:
                    lid_set.add(pid)
        for msgs in list(session.messages.values()) + list(session.media.values()):
            for m in msgs:
                fj = m.get("fromJid", "")
                if fj and "@lid" in fj and fj not in session.lid_to_pn:
                    lid_set.add(fj)

    if not lid_set:
        return
    pass
    resolved = 0
    for lid_jid in lid_set:
        try:
            lid_user = lid_jid.split("@")[0]
            lid_obj = build_jid(lid_user, "lid")
            pn_jid = session.client.get_pn_from_lid(lid_obj)
            pn_str = jid_str(pn_jid)
            if pn_str and "@lid" not in pn_str:
                with session.lock:
                    session.lid_to_pn[lid_jid] = pn_str
                    for g in session.groups:
                        for p in g.get("participants", []):
                            if p.get("id") == lid_jid:
                                phone = pn_str.split("@")[0] if "@" in pn_str else None
                                p["number"] = phone
                                if not p.get("name") or p["name"] == phone:
                                    for c in session.contacts:
                                        if c["id"] == pn_str:
                                            p["name"] = c.get("name", phone)
                                            break
                resolved += 1
        except Exception:
            pass
    if resolved:
        pass


def sync_archived_from_db(session):
    """Read archived status from whatsmeow_chat_settings and update session.chats."""
    try:
        import sqlite3
        if not os.path.exists(session.db_path):
            return
        conn = sqlite3.connect(session.db_path)
        cur = conn.cursor()
        cur.execute("SELECT chat_jid FROM whatsmeow_chat_settings WHERE archived=1")
        archived_jids = {row[0] for row in cur.fetchall()}
        conn.close()
        if not archived_jids:
            return
        with session.lock:
            for chat in session.chats:
                chat["archived"] = chat["id"] in archived_jids
    except Exception:
        pass


def do_sync(session):
    if not session.client or not session.connected:
        session.sync_status.update({"syncing": False, "phase": "done", "completedAt": datetime.utcnow().isoformat() + "Z", "message": "Sync complete"})
        return
    try:
        session.sync_status.update({"syncing": True, "phase": "chats", "error": None, "startedAt": datetime.utcnow().isoformat() + "Z", "completedAt": None, "message": "Syncing groups..."})
        enrich_contacts_from_store(session)
        session.sync_status["contacts"] = len(session.contacts)
        try:
            groups = session.client.get_joined_groups()
            with session.lock:
                for g in groups:
                    gid = jid_str(g.JID)
                    participants = []
                    for p in g.Participants:
                        pid = jid_str(p.JID)
                        pnum = pid.split("@")[0] if "@" in pid else None
                        is_lid = pid and ("@lid" in pid or ":" in pid)
                        pname = pnum
                        for c in session.contacts:
                            if c["id"] == pid:
                                pname = c.get("name", pnum); break
                        participants.append({"id": pid, "number": None if is_lid else pnum, "name": None if is_lid else pname, "admin": p.IsAdmin or p.IsSuperAdmin})
                        if not is_lid and "@g.us" not in pid:
                            if not any(c["id"] == pid for c in session.contacts):
                                session.contacts.append({"id": pid, "name": pnum or pid, "number": pnum or "", "status": "", "fromGroup": True})
                    group_name = g.GroupName.Name if hasattr(g, 'GroupName') and hasattr(g.GroupName, 'Name') else gid
                    description = g.GroupTopic.Topic if hasattr(g, 'GroupTopic') and hasattr(g.GroupTopic, 'Topic') else ""
                    created_at = str(g.GroupCreated) if hasattr(g, 'GroupCreated') and g.GroupCreated else None
                    gidx = next((i for i, x in enumerate(session.groups) if x["id"] == gid), -1)
                    group_entry = {"id": gid, "name": clean(group_name), "description": clean(description[:100]) if description else "", "participants": participants, "participantCount": len(participants), "createdAt": created_at}
                    if gidx >= 0:
                        session.groups[gidx] = group_entry
                    else:
                        session.groups.append(group_entry)
                    chat_idx = next((i for i, c in enumerate(session.chats) if c["id"] == gid), -1)
                    if chat_idx >= 0:
                        session.chats[chat_idx]["name"] = clean(group_name)
                    else:
                        session.chats.append({"id": gid, "name": clean(group_name), "isGroup": True, "unreadCount": 0, "lastMessage": "", "timestamp": 0, "archived": False})
                session.sync_status["chats"] = len(session.chats)
                session.sync_status["groups"] = len(session.groups)
                pass
        except Exception as e:
            pass
        for _ in range(30):
            if time.time() - session.last_history_sync_at > 5:
                break
            time.sleep(1)
        # SET BEFORE PERSISTING, SO THE PANEL LEAVES THE SYNC SCREEN AT ONCE.
        session.do_sync_done = True
        session.sync_status.update({"syncing": False, "phase": "done", "completedAt": datetime.utcnow().isoformat() + "Z", "message": "Sync complete"})
        persist(session)
        pass

        def background_post_sync(s):
            try:
                enrich_contacts_from_store(s)
                bulk_resolve_group_lids(s)
                s.rebuild_group_senders()
                s.rebuild_latest_received()
                s.rebuild_latest_sent()
                sync_archived_from_db(s)
                persist(s)
                pass
            except Exception as e:
                pass

        threading.Thread(target=background_post_sync, args=(session,), daemon=True).start()
    except Exception as e:
        pass
        session.do_sync_done = True
        session.sync_status.update({"syncing": False, "phase": "done", "completedAt": datetime.utcnow().isoformat() + "Z", "message": "Sync complete (with errors)", "error": str(e)})


def persist(session):
    """THE STORE ON DISK, BESIDE THE SESSION IT BELONGS TO."""
    if session.deleted:
        return

    with session.lock:
        state = {name: getattr(session, name) for name in KEPT}
        state["failed_downloads"] = list(session.failed_downloads)

        try:
            written = json.dumps(state, ensure_ascii=False, default=str)
        except Exception as e:
            logger.warning(f"[persist] user={session.username} could not be written: {e}")
            return

    here = Path(session.db_path).parent
    part = here / (CACHE + ".part")

    try:
        here.mkdir(parents=True, exist_ok=True)
        part.write_text(written, encoding="utf-8")
        os.replace(str(part), str(here / CACHE))
    except Exception as e:
        logger.warning(f"[persist] user={session.username} could not be saved: {e}")


def remembered(session):
    """THE LAST SNAPSHOT BACK INTO A SESSION THAT HAS ONLY JUST BEEN MADE."""
    where = Path(session.db_path).parent / CACHE

    try:
        state = json.loads(where.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return
    except Exception as e:
        logger.warning(f"[persist] user={session.username} cache unreadable: {e}")
        return

    for name in KEPT:
        if state.get(name) is not None:
            setattr(session, name, state[name])

    session.failed_downloads = set(state.get("failed_downloads") or [])

    # THE PLUMBING THAT WAS STORED AS EMPTY LINES BEFORE IT WAS RECOGNISED IS STILL IN
    # HERE, AND ONLY A RELINK WOULD BRING THE HISTORY DOWN AGAIN, SO IT IS SWEPT ON LOAD
    # INSTEAD. A LINE WITH NO WORDS, NO MEDIA AND NOTHING TO SHOW FOR ITSELF IS ONE OF THEM.
    swept = 0

    for store in (session.messages, session.media):
        for chat_id, held in list(store.items()):
            kept = [m for m in held if said_something(m)]
            swept += len(held) - len(kept)
            store[chat_id] = kept

    if swept:
        logger.info(f"[persist] user={session.username} dropped {swept} lines nobody sent")

    # A CACHE WRITTEN BEFORE previewed() EXISTED HAS A BLANK BESIDE EVERY NAME,
    # AND THE HISTORY THAT WOULD FILL THEM IN ONLY COMES AGAIN ON A RELINK.
    for chat in session.chats:
        previewed(session, chat, chat.get("id", ""))

    kept = sum(len(v) for v in session.messages.values())
    kept += sum(len(v) for v in session.media.values())
    logger.info(
        f"[persist] user={session.username} restored {len(session.chats)} chats, "
        f"{kept} messages, {len(session.contacts)} contacts"
    )


def start_session(session):
    user = session.username
    logger.info(f"[start_session] begin user={user}")
    if session.deleted:
        logger.info(f"[start_session] user={user} is deleted, skipping")
        return
    if session.client and session.connect_thread and session.connect_thread.is_alive():
        logger.info(f"[start_session] user={user} already running, skipping")
        return
    # A NEW RUN, SO THE CODE IT OPENS WITH IS A FIRST ONE AND GETS THE MINUTE.
    session.qr_at = 0
    session.qr_life = QR_FIRST
    session.qr_shut = 0
    # NO STORE MEANS NO DEVICE TO LOG BACK IN AS, SO THIS RUN PAIRS OFF A QR.
    if not os.path.exists(session.db_path):
        logger.info(f"[start_session] user={user} no store yet, this run pairs off a QR")
    session.stop_event.clear()
    try:
        import sqlite3
        conn = sqlite3.connect(session.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.close()
    except Exception as e:
        logger.warning(f"[start_session] user={user} sqlite WAL pragma failed: {e}")

    logger.info(f"[start_session] user={user} creating NewClient...")
    t0 = time.monotonic()
    session.client = NewClient(session.db_path)
    logger.info(f"[start_session] user={user} NewClient done in {time.monotonic()-t0:.2f}s")

    register_events(session)
    logger.info(f"[start_session] user={user} events registered, spawning connect thread")

    def run():
        try:
            logger.info(f"[start_session] user={user} client.connect() starting in bg thread")
            session.client.connect()
            logger.info(f"[start_session] user={user} client.connect() returned")
        except Exception as e:
            logger.warning(f"[start_session] user={user} client.connect() failed: {type(e).__name__}: {e}")
            session.connected = False

    session.connect_thread = threading.Thread(target=run, daemon=True)
    session.connect_thread.start()
    logger.info(f"[start_session] user={user} returning (connect thread running)")


def stop_session(session):
    session.stop_event.set()
    persist(session)
    if session.client:
        try:
            session.client.disconnect()
        except Exception:
            pass
    session.connected = False
    session.client = None
    session.connect_thread = None


def spoken_to(session, found):
    """OF SEVERAL CONTACTS UNDER ONE NAME, THE ONE THERE IS A CONVERSATION WITH."""
    def held(contact):
        jid = contact["id"]

        return len(session.messages.get(jid, [])) + len(session.media.get(jid, []))

    return max(found, key=held)["id"]


def resolve_recipient(session, input_str):
    if not input_str:
        raise ValueError("Recipient is required")
    if "@" in input_str:
        return input_str
    if re.match(r'^\+?\d[\d\s\-(). ]+$', input_str):
        return resolve_jid(session, input_str)
    q = input_str.strip().lower()

    # TWO PEOPLE SAVED UNDER ONE NAME IS ORDINARY, AND THE FIRST IN THE LIST IS NOT THE
    # ONE MEANT: "Athul" MATCHED A NUMBER WITH NO CHAT AT ALL WHILE THE Athul WHO HAD JUST
    # SENT SOMETHING SAT SECOND, SO A REAL UNREAD MESSAGE CAME BACK AS NONE AND WAS
    # RETRACTED TO HIM AS A MISTAKE. THE ONE HE HAS ACTUALLY TALKED TO IS THE ONE HE MEANS.
    exact = [c for c in session.contacts if c.get("name", "").lower() == q]
    loose = [c for c in session.contacts if q in c.get("name", "").lower()]

    for found in (exact, loose):
        if found:
            return spoken_to(session, found)
    for g in session.groups:
        if g["name"].lower() == q:
            return g["id"]
    for g in session.groups:
        if q in g["name"].lower():
            return g["id"]
    for c in session.chats:
        if c["name"].lower() == q:
            return c["id"]
    for c in session.chats:
        if q in c["name"].lower():
            return c["id"]
    all_stores = list(session.messages.values()) + list(session.media.values())
    for msgs in all_stores:
        for m in msgs:
            if not m.get("fromMe") and m.get("fromJid") and "@g.us" not in m.get("fromJid", ""):
                if m.get("from", "").lower() and q in m["from"].lower():
                    return m["fromJid"]
    for name, jid in session.lid_name_map.items():
        if q in name:
            return jid
    raise ValueError(f'Contact not found: "{input_str}". Provide the phone number with country code.')


def resolve_jid(session, number):
    c = re.sub(r'\D', '', number)
    if c in session.jid_cache:
        return session.jid_cache[c]
    if session.client and session.connected:
        try:
            results = session.client.is_on_whatsapp(f"+{c}")
            for r in results:
                if r.IsIn:
                    j = jid_str(r.JID); session.jid_cache[c] = j; return j
        except Exception:
            pass
    if len(c) == 10 and session.phone and len(session.phone) > 10:
        cc = session.phone[:len(session.phone) - 10]
        wc = f"{cc}{c}"
        if session.client and session.connected:
            try:
                results = session.client.is_on_whatsapp(f"+{wc}")
                for r in results:
                    if r.IsIn:
                        j = jid_str(r.JID); session.jid_cache[c] = j; return j
            except Exception:
                pass
        jid = f"{wc}@s.whatsapp.net"; session.jid_cache[c] = jid; return jid
    jid = f"{c}@s.whatsapp.net"; session.jid_cache[c] = jid; return jid


def media_type_of(filepath):
    ext = Path(filepath).suffix.lower().lstrip(".")
    if ext in ("jpg", "jpeg", "png", "gif", "webp", "bmp"): return "image"
    if ext in ("mp4", "mkv", "avi", "mov", "webm"): return "video"
    if ext in ("mp3", "ogg", "wav", "m4a", "aac", "opus"): return "audio"
    return "document"


def make_jid(jid_str_val):
    parts = jid_str_val.split("@")
    return build_jid(parts[0], parts[1] if len(parts) > 1 else "s.whatsapp.net")


def sending_jid(session, jid_val):
    """WHERE TO ACTUALLY SEND SOMETHING ADDRESSED TO A PHONE NUMBER."""
    if "@s.whatsapp.net" not in (jid_val or ""):
        return jid_val

    if jid_val in session.pn_to_lid:
        return session.pn_to_lid[jid_val]

    if not session.client:
        return jid_val

    try:
        found = jid_str(session.client.get_lid_from_pn(make_jid(jid_val)))
    except Exception:
        return jid_val

    # NO LID MEANS AN ACCOUNT THAT HAS NOT MOVED, AND THE NUMBER IS STILL RIGHT.
    if "@lid" not in (found or ""):
        return jid_val

    session.pn_to_lid[jid_val] = found

    return found


def posted(session, result, jid_val, target, **extra):
    """WHAT CAME BACK FROM A SEND, ANSWERED HONESTLY."""
    stamp = int(getattr(result, "Timestamp", 0) or 0)
    ident = getattr(result, "ID", "") or ""

    if not ident or not stamp:
        return jsonify({
            "error": "WhatsApp did not acknowledge the message, so it was not delivered. Nothing was sent.",
            "messageId": ident, "jid": jid_val, "sentTo": target, **extra,
        }), 502

    with session.lock:
        session.pushed.append({"chatJid": jid_val, "id": ident, "at": time.time()})
        del session.pushed[:-PUSHED]

    return jsonify({"success": True, "messageId": ident, "jid": jid_val, "sentTo": target,
                    "timestamp": stamp, **extra})


# ─── Flask routes ────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return jsonify({"ok": True})


@app.get("/sessions")
def list_sessions():
    result = []
    for username, s in sessions.items():
        result.append({"username": username, "connected": s.connected, "authenticated": s.authenticated, "phone": s.phone})
    return jsonify(result)


@app.get("/<username>/status")
def status(username):
    s = get_session(username)
    # THE STORE ON DISK IS THE WHOLE ANSWER TO WHETHER THIS ACCOUNT IS SET UP.
    configured = os.path.exists(s.db_path)
    return jsonify({"connected": s.connected, "authenticated": s.authenticated or configured, "configured": configured, "phone": s.phone, "name": s.name})


@app.get("/<username>/sync-status")
def sync_status(username):
    s = get_session(username)
    contacts_count = len(s.contacts)
    chats_count = len(s.chats)
    groups_count = len(s.groups)
    messages_count = sum(len(v) for v in s.messages.values()) + sum(len(v) for v in s.media.values())
    still_syncing = not s.do_sync_done

    # LIVE IS THE HALF THAT ANSWERS "ARE MESSAGES SYNCED": A SOCKET THAT IS UP
    # GETS EVERY NEW MESSAGE THE INSTANT IT IS SENT, WITH NO CATCHING UP TO DO.
    live = {"connected": s.connected, "authenticated": s.authenticated}

    if still_syncing:
        if chats_count > 0 or groups_count > 0:
            phase = "chats"
            message = f"Syncing chats and groups... ({chats_count} chats, {groups_count} groups)"
        elif contacts_count > 0:
            phase = "contacts"
            message = f"Loading contacts... ({contacts_count} contacts)"
        else:
            phase = "contacts"
            message = "Waiting for WhatsApp data..."
        return jsonify({"syncing": True, "phase": phase, "contacts": contacts_count, "chats": chats_count, "groups": groups_count, "messages": messages_count, "message": message, **live})
    elif s.sync_status.get("phase") == "idle":
        return jsonify({"syncing": False, "phase": "idle", "contacts": contacts_count, "chats": chats_count, "groups": groups_count, "messages": messages_count, "message": None, **live})
    else:
        return jsonify({"syncing": False, "phase": "done", "contacts": contacts_count, "chats": chats_count, "groups": groups_count, "messages": messages_count, "message": "Sync complete", "completedAt": s.sync_status.get("completedAt"), **live})


@app.get("/<username>/qr")
def qr(username):
    s = get_session(username)
    # THE PANEL POLLS THIS WHILE IT SAYS IT IS WAITING FOR A SCAN, WHICH IS
    # SOMEBODY WATCHING JUST AS MUCH AS THE PAGE IS.
    s.qr_seen = time.time()
    if s.authenticated or s.connected:
        return jsonify({"status": "connected", "qr": None})
    if s.qr_data and talking(s):
        # THE AGE OF WHAT WE ARE ABOUT TO HAND BACK. A CODE WHATSAPP HAS ALREADY EXPIRED ITS
        # SIDE STILL LOOKS PERFECTLY FRESH HERE, SO ITS AGE IS THE ONLY WAY TO SEE THAT COMING.
        old = time.time() - s.qr_at
        if old > s.qr_life:
            logger.warning(
                f"[qr] user={s.username} serving a code {old:.0f}s old, past its {s.qr_life}s"
            )
        return jsonify({"status": "waiting", "qr": s.qr_data})
    return jsonify({"status": "loading", "qr": None})


SCAN_PAGE = """<!doctype html><meta charset="utf-8"><title>Link WhatsApp to Happy</title>
{refresh}<style>
body{{font:16px system-ui;background:#111;color:#eee;display:flex;min-height:100vh;margin:0;
align-items:center;justify-content:center}}
main{{text-align:center;padding:2rem}}
img{{width:280px;height:280px;background:#fff;padding:12px;border-radius:12px}}
p{{color:#9a9a9a;max-width:34rem;line-height:1.5}}
</style><main>{body}</main>"""

WAITING_BODY = """<h2>Scan this with WhatsApp</h2>
<img src="{qr}" alt="QR code">
<p>On your phone: Settings, then Linked Devices, then Link a Device.
This code refreshes itself, so scan whichever one is on screen.</p>"""

STARTING_BODY = "<h2>Starting WhatsApp</h2><p>The code will appear here in a moment.</p>"

LINKED_BODY = """<h2>WhatsApp is linked</h2>
<p>You can close this tab and go back to Happy.</p>"""


def talking(session):
    """WHETHER THE SOCKET THAT HANDED OUT THE CODE ON SCREEN IS STILL OPEN."""
    client = session.client

    if client is None:
        return False

    try:
        return bool(client.is_connected)
    except Exception as e:
        # A CLIENT THAT CANNOT BE ASKED IS LEFT TO THE CLOCK IN stale(), AND SAYS
        # SO, BECAUSE FALLING BACK QUIETLY IS HOW THIS WENT UNNOTICED BEFORE.
        logger.warning(f"[qr] user={session.username} socket could not be asked: {e}")

        return True


def shut_for(session):
    """HOW LONG THE SOCKET HAS BEEN SHUT, TIMED FROM WHEN IT WAS FIRST FOUND SO."""
    if talking(session):
        session.qr_shut = 0

        return 0

    if not session.qr_shut:
        session.qr_shut = time.time()

    return time.time() - session.qr_shut


def stale(session):
    """TRUE WHEN THE CODE ON SCREEN IS ONE NOBODY CAN SCAN ANY MORE."""
    if not session.qr_data:
        return False

    # WHATSAPP SHUTS THE SOCKET THE MOMENT IT GIVES UP ON A RUN, WHICH SAYS THE
    # CODES ARE DEAD SOONER AND SURER THAN ANY GUESS OFF THE CLOCK.
    if shut_for(session) > QR_GRACE:
        return True

    return time.time() - session.qr_at > session.qr_life + QR_SLACK


def renew(session):
    """A QR SEQUENCE THAT HAS RUN OUT, BEGUN AGAIN."""
    with session.lock:
        # ANOTHER TAB MAY HAVE DONE IT IN THE TWO SECONDS SINCE WE LOOKED.
        if not stale(session):
            return

        why = "socket shut" if shut_for(session) > QR_GRACE else "code aged out"
        logger.info(f"[qr] user={session.username} codes ran out ({why}), asking for more")
        session.qr_data = None

        stop_session(session)
        start_session(session)


def scannable():
    """THE RUN KEPT ALIVE WHILE SOMEBODY IS WATCHING, WHATEVER THEIR TAB IS DOING."""
    # A BACKGROUNDED TAB HAS ITS META REFRESH THROTTLED TO A MINUTE OR MORE, AND
    # RENEWING ONLY WHEN THE PAGE ASKED LEFT A DEAD CODE UP FOR ALL OF IT.
    while True:
        time.sleep(QR_EVERY)

        for session in list(sessions.values()):
            try:
                if time.time() - session.qr_seen > QR_WATCHED:
                    continue

                if session.authenticated or session.connected:
                    continue

                if stale(session):
                    renew(session)
            except Exception as e:
                logger.warning(f"[qr] user={session.username} could not be renewed: {e}")


@app.get("/<username>/scan")
def scan(username):
    """THE QR AS A PAGE, FOR A BROWSER RATHER THAN FOR THE PANEL."""
    s = get_session(username)
    s.qr_seen = time.time()

    if s.authenticated or s.connected:
        return SCAN_PAGE.format(refresh="", body=LINKED_BODY)

    if stale(s):
        renew(s)
    elif not (s.client and s.connect_thread and s.connect_thread.is_alive()):
        start_session(s)

    # A CODE WHOSE SOCKET HAS GONE IS TAKEN OFF THE PAGE THE SECOND IT DIES,
    # RATHER THAN LEFT UP FOR THE GRACE renew() SPENDS MAKING SURE.
    body = WAITING_BODY.format(qr=s.qr_data) if s.qr_data and talking(s) else STARTING_BODY

    return SCAN_PAGE.format(refresh='<meta http-equiv="refresh" content="2">', body=body)


@app.post("/<username>/start")
def start(username):
    s = get_session(username)
    if s.client and s.connect_thread and s.connect_thread.is_alive():
        return jsonify({"started": True, "already_running": True})
    start_session(s)
    return jsonify({"started": True})


@app.post("/<username>/stop")
def stop(username):
    with sessions_lock:
        s = sessions.get(username)
    if s:
        stop_session(s)
    return jsonify({"stopped": True})


@app.post("/<username>/disconnect")
def disconnect(username):
    with sessions_lock:
        s = sessions.pop(username, None)
    if s:
        s.deleted = True  # STOPS A RECONNECT TIMER FROM STARTING IT BACK UP.
        s.stop_event.set()
        s.connected = False
        s.authenticated = False
        if s.persist_timer:
            s.persist_timer.cancel()
        client = s.client
        s.client = None
        s.connect_thread = None
        s.qr_data = None; s.phone = None; s.name = None
        s.contacts = []; s.chats = []; s.groups = []; s.messages = {}; s.media = {}
        if client:
            try:
                client.logout()
            except Exception:
                pass
            try:
                client.disconnect()
            except Exception:
                pass
    user_dir = DATA_DIR / username
    if user_dir.exists():
        try:
            shutil.rmtree(str(user_dir))
        except Exception:
            pass
    return jsonify({"success": True})


@app.post("/<username>/sync")
def sync(username):
    s = get_session(username)
    if not s.connected:
        return jsonify({"error": "Not connected"}), 503
    threading.Thread(target=do_sync, args=(s,), daemon=True).start()
    return jsonify({"success": True, "message": "Sync started"})


@app.get("/<username>/contacts")
def contacts(username):
    s = get_session(username)
    enrich_contacts_from_store(s)
    filtered = [c for c in s.contacts if not (c["id"] and ("@lid" in c["id"] or ":" in c["id"]) and (not c.get("name") or c["name"] == c.get("number") or c["name"] == "unknown"))]
    return jsonify(clean(filtered))


@app.get("/<username>/search-contacts")
def search_contacts(username):
    q = (request.args.get("q") or "").strip().lower()
    if not q:
        return jsonify({"error": "q parameter required"}), 400
    s = get_session(username)
    enrich_contacts_from_store(s)
    results = {}
    for c in s.contacts:
        if (c.get("name") and q in c["name"].lower()) or (c.get("number") and q in c["number"]):
            results[c["id"]] = {"id": c["id"], "name": c.get("name"), "number": c.get("number")}
    for g in s.groups:
        for p in g.get("participants", []):
            if (p.get("name") and q in (p["name"] or "").lower()) or (p.get("number") and q in (p["number"] or "")):
                if p["id"] not in results:
                    results[p["id"]] = {"id": p["id"], "name": p.get("name") or p.get("number"), "number": p.get("number")}
    for c in s.chats:
        if not c.get("isGroup") and c.get("name") and q in c["name"].lower():
            if c["id"] not in results:
                results[c["id"]] = {"id": c["id"], "name": c["name"], "number": c["id"].split("@")[0]}
    for store in list(s.messages.values()) + list(s.media.values()):
        for m in store:
            if not m.get("fromMe") and m.get("from") and q in m["from"].lower() and m.get("fromJid"):
                if m["fromJid"] not in results:
                    results[m["fromJid"]] = {"id": m["fromJid"], "name": m["from"], "number": m.get("phoneNumber") or m["fromJid"].split("@")[0]}
    enriched = []
    for contact in results.values():
        member_groups = [{"id": g["id"], "name": g["name"]} for g in s.groups if any(p["id"] == contact["id"] for p in g.get("participants", []))]
        enriched.append({**contact, "groups": member_groups})
    return jsonify(clean(enriched))


@app.get("/<username>/chats")
def chats(username):
    s = get_session(username)
    jid_to_name = s.build_jid_to_name()
    result = []
    for chat in s.chats:
        cid = chat.get("id", "")
        if "@g.us" not in cid and "@lid" not in cid:
            resolved = jid_to_name.get(cid)
            if resolved:
                chat = {**chat, "name": resolved}

        # THE PHONE SENDS A COUNT, THE BODIES ARRIVE SEPARATELY, AND HISTORY SYNC
        # CAN LEAVE A COUNT WITH NOTHING BEHIND IT. SAYING HOW MANY RECEIVED LINES
        # ARE ACTUALLY HELD STOPS AN EMPTY READ BEING TAKEN FOR "NOTHING UNREAD".
        stored = s.messages.get(cid, []) + s.media.get(cid, [])
        held = [m for m in stored if not m.get("fromMe")]
        # THE BADGE CAN ONLY MEAN MESSAGES SINCE HE LAST WROTE: ANYTHING OLDER THAN
        # HIS OWN LAST LINE HE HAD ALREADY OPENED THE CHAT TO SEND.
        mine = max((m.get("timestamp", 0) for m in stored if m.get("fromMe")), default=0)
        since = [
            m
            for m in held
            if m.get("timestamp", 0) > mine and m.get("type") != "reaction"
        ]
        chat = {**chat, "receivedHeld": len(held), "heldSinceMine": len(since)}
        result.append(chat)

    # NEWEST FIRST, EVERY TIME IT IS ASKED.
    result.sort(key=lambda chat: chat.get("timestamp", 0), reverse=True)

    return jsonify(clean(result))


@app.get("/<username>/groups")
def groups(username):
    s = get_session(username)
    result = [{"id": g["id"], "name": g["name"], "description": g.get("description", "")[:100], "participantCount": g.get("participantCount", 0), "createdAt": g.get("createdAt"), "archived": next((c.get("archived", False) for c in s.chats if c["id"] == g["id"]), False)} for g in s.groups]
    return jsonify(clean(result))


# HOW LONG WHATSAPP'S OWN SERVERS KEEP MEDIA FETCHABLE AFTER IT WAS SENT.
CDN_SECONDS = 14 * 86400


def with_media(s, entry):
    """A MESSAGE WITH localPath ON IT WHEN ITS MEDIA IS ALREADY ON THIS DISK."""
    if not entry.get("hasMedia"):
        return entry

    # A STICKER OR A VOICE NOTE CARRIES NO WORDS, SO ITS body IS "" AND A READER TAKES THAT
    # FOR AN EMPTY MESSAGE: THE CHAT LIST SAID "[sticker]" FROM Athul AND get_messages SAID
    # NOTHING, SO A REAL STICKER WAS RETRACTED AS A MISTAKE. WHAT THE LIST SAYS IS WHAT THE
    # MESSAGE SAYS.
    if not entry.get("body"):
        entry = {**entry, "body": SHOWN.get(entry.get("mediaType") or entry.get("type"), "")}

    mid = entry.get("id", "")
    name = entry.get("filename", "")
    cached = (s.downloaded_media.get(mid) or {}).get("local_path") or ""
    beside = os.path.join(s.dl_dir, name) if name else ""

    local = next((p for p in (cached, beside) if p and os.path.exists(p)), "")

    kept = dict(entry)

    if local:
        kept["localPath"] = local

    cached_only = mid in s.downloaded_media
    fresh = entry.get("timestamp", 0) > time.time() - CDN_SECONDS and mid not in s.failed_downloads
    viewonce = entry.get("type") == "viewonce"

    kept["downloadable"] = not viewonce and (bool(local) or cached_only or fresh)

    return kept


@app.get("/<username>/messages/<path:jid>")
def messages(username, jid):
    s = get_session(username)
    limit = int(request.args.get("limit", 20))
    media_only = request.args.get("media") == "true"
    received_only = request.args.get("received") == "true"
    order = request.args.get("order", "newest")

    if media_only:
        msgs = s.media.get(jid, [])
    else:
        text_msgs = s.messages.get(jid, [])
        media_msgs = s.media.get(jid, [])
        msgs = sorted(text_msgs + media_msgs, key=lambda m: m.get("timestamp", 0))

    if received_only:
        msgs = [m for m in msgs if not m.get("fromMe")]
    sliced = msgs[:limit] if order == "oldest" else msgs[-limit:]
    return jsonify(clean([with_media(s, m) for m in sliced]))


@app.get("/<username>/resolve-contact")
def resolve_contact(username):
    q = request.args.get("q", "")
    if not q:
        return jsonify({"error": "q parameter required"}), 400
    s = get_session(username)
    try:
        jid = resolve_recipient(s, q)
        contact = next((c for c in s.contacts if c["id"] == jid), None)
        return jsonify({"jid": jid, "name": contact["name"] if contact else q, "number": contact["number"] if contact else jid.split("@")[0]})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404








@app.post("/<username>/send")
def send(username):
    body = request.json
    to, message = body.get("to", ""), body.get("message", "")
    s = get_session(username)
    if not s.client or not s.connected:
        return jsonify({"error": "Not connected"}), 503
    try:
        jid_val = resolve_recipient(s, to)
        target = sending_jid(s, jid_val)
        result = s.client.send_message(make_jid(target), message)
        return posted(s, result, jid_val, target)
    except ValueError as e:
        return jsonify({"error": str(e), "contact_not_found": True}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/<username>/send-group")
def send_group(username):
    body = request.json
    group_id, message = body.get("groupId", ""), body.get("message", "")
    s = get_session(username)
    if not s.client or not s.connected:
        return jsonify({"error": "Not connected"}), 503
    try:
        jid_val = resolve_recipient(s, group_id)
        parts = jid_val.split("@")
        result = s.client.send_message(build_jid(parts[0], parts[1] if len(parts) > 1 else "g.us"), message)
        return posted(s, result, jid_val, jid_val)
    except ValueError as e:
        return jsonify({"error": str(e), "contact_not_found": True}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/<username>/send-media")
def send_media(username):
    body = request.json
    to, url = body.get("to", ""), body.get("url", "")
    caption, filename = body.get("caption", ""), body.get("filename", "")
    s = get_session(username)
    if not s.client or not s.connected:
        return jsonify({"error": "Not connected"}), 503
    try:
        jid_val = resolve_recipient(s, to)
        target = sending_jid(s, jid_val)
        jid = make_jid(target)
        mt = media_type_of(filename or url)
        if mt == "image":
            result = s.client.send_image(jid, file=url, caption=caption)
        elif mt == "video":
            result = s.client.send_video(jid, file=url, caption=caption)
        elif mt == "audio":
            result = s.client.send_audio(jid, file=url)
        else:
            result = s.client.send_document(jid, file=url, caption=caption, filename=filename or Path(url).name)
        return posted(s, result, jid_val, target, mediaType=mt)
    except ValueError as e:
        return jsonify({"error": str(e), "contact_not_found": True}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/<username>/media/<message_id>")
def media(username, message_id):
    s = get_session(username)
    m = s.downloaded_media.get(message_id)
    if not m:
        return jsonify({"error": "Media not found"}), 404
    return jsonify(m)


@app.post("/<username>/download-media")
def download_media(username):
    body = request.json
    message_id, chat_id = body.get("messageId", ""), body.get("chatId", "")
    s = get_session(username)
    if not s.client or not s.connected:
        return jsonify({"error": "Not connected"}), 503
    if message_id in s.downloaded_media:
        return jsonify({"success": True, **s.downloaded_media[message_id]})
    # A VIEW ONCE HAS ALREADY SELF DESTRUCTED, SO THERE IS NOTHING TO FETCH.
    for msgs in s.media.values():
        cached = next((m for m in msgs if m["id"] == message_id), None)
        if cached and cached.get("type") == "viewonce":
            return jsonify({"error": "View-once messages cannot be downloaded"}), 400

    # A HISTORY SYNC MESSAGE IS NOT IN raw_messages, BUT AUTO DOWNLOAD MAY HAVE
    # PUT ITS FILE ON DISK ALREADY.
    cached_entry = None
    if chat_id:
        cached_entry = next((m for m in s.media.get(chat_id, []) if m["id"] == message_id), None)
    if not cached_entry:
        for msgs in s.media.values():
            cached_entry = next((m for m in msgs if m["id"] == message_id), None)
            if cached_entry:
                break
    if cached_entry and cached_entry.get("filename"):
        fname = cached_entry["filename"]
        local_path = os.path.join(s.dl_dir, fname)
        mime = cached_entry.get("mimeType") or "application/octet-stream"
        if os.path.exists(local_path):
            size = os.path.getsize(local_path)
            result = {"local_path": local_path, "filename": fname, "mime": mime, "size": size}
            s.downloaded_media[message_id] = result
            return jsonify({"success": True, **result})

    # NO filename MEANS THE DOWNLOAD FAILED, OR THE BRIDGE RESTARTED AND TOOK
    # raw_messages WITH IT. THE NAME IS GUESSABLE FROM THE MIME TYPE.
    if cached_entry and not cached_entry.get("filename") and s.client and s.connected:
        mime = cached_entry.get("mimeType") or "application/octet-stream"
        ext = mime.split("/")[-1].split(";")[0]
        guessed_fname = f"{message_id}.{ext}"
        guessed_local = os.path.join(s.dl_dir, guessed_fname)
        if os.path.exists(guessed_local):
            size = os.path.getsize(guessed_local)
            result = {"local_path": guessed_local, "filename": guessed_fname, "mime": mime, "size": size}
            s.downloaded_media[message_id] = result
            with s.lock:
                for msgs in s.media.values():
                    for m in msgs:
                        if m.get("id") == message_id:
                            m["filename"] = guessed_fname
            return jsonify({"success": True, **result})

    raw_msg = s.raw_messages.get(message_id)
    msg_proto = None
    if raw_msg:
        # A LIVE MESSAGE CARRIES .Message, A HISTORY SYNCED ONE .message.
        msg_proto = getattr(raw_msg, 'Message', None) or getattr(raw_msg, 'message', None)
        if msg_proto is None:
            # SOME NEONIZE VERSIONS TAKE THE WebMessageInfo WHOLE.
            msg_proto = raw_msg
    if not msg_proto and s.client:
        try:
            me = s.client.get_me()
            chat_jid = make_jid(chat_id) if chat_id else None
            if not chat_jid:
                for cid, msgs in s.media.items():
                    if any(m["id"] == message_id for m in msgs):
                        chat_jid = make_jid(cid)
                        break
            if chat_jid:
                retry_msg = s.client.get_message_for_retry(me.JID, chat_jid, message_id)
                if retry_msg:
                    msg_proto = retry_msg
        except Exception as e:
            pass
    if not msg_proto:
        return jsonify({"error": f"Message not found or media expired. ID: {message_id}"}), 404
    try:
        media_bytes = s.client.download_any(msg_proto)
        if not media_bytes:
            if raw_msg and msg_proto is not raw_msg:
                media_bytes = s.client.download_any(raw_msg)
        if not media_bytes:
            return jsonify({"error": "Failed to download media - neonize returned empty bytes"}), 500
        cached = None
        cached_filename = None
        for chat_msgs in ([s.media.get(chat_id, [])] if chat_id else s.media.values()):
            cached = next((m for m in chat_msgs if m["id"] == message_id), None)
            if cached:
                cached_filename = cached.get("filename")
                break
        mime = (cached.get("mimeType") if cached else None) or "application/octet-stream"
        ext = mime.split("/")[-1].split(";")[0]
        fname = cached_filename or f"{message_id.replace('/', '_').replace(':', '_')}.{ext}"
        local_path = os.path.join(s.dl_dir, fname)
        with open(local_path, "wb") as f:
            f.write(media_bytes)
        result = {"local_path": local_path, "filename": fname, "mime": mime, "size": len(media_bytes)}
        s.downloaded_media[message_id] = result
        return jsonify({"success": True, **result})
    except Exception as e:
        import traceback
        err_detail = traceback.format_exc()
        pass
        return jsonify({"error": str(e) or repr(e), "detail": err_detail.splitlines()[-1]}), 500






@app.get("/<username>/group-participants/<path:group_id>")
def group_participants(username, group_id):
    s = get_session(username)
    group = next((g for g in s.groups if g["id"] == group_id), None)
    if not group:
        return jsonify({"error": "Group not found", "group_id": group_id}), 404
    enriched = []
    for p in group.get("participants", []):
        contact = next((c for c in s.contacts if c["id"] == p["id"]), None)
        name = (contact["name"] if contact and contact.get("name") and contact["name"] != contact.get("number") else p.get("number")) or p.get("name")
        enriched.append({**p, "name": name})
    return jsonify({"id": group["id"], "name": group["name"], "participantCount": group.get("participantCount", 0), "participants": enriched})


@app.get("/<username>/search-groups-by-contacts")
def search_groups_by_contacts(username):
    contacts_param = request.args.get("contacts", "")
    if not contacts_param:
        return jsonify({"error": "contacts parameter required"}), 400
    s = get_session(username)
    queries = [q.strip().lower() for q in contacts_param.split(",") if q.strip()]
    resolved = []
    for q in queries:
        if q in ("me", "self"):
            resolved.append({"query": q, "jid": f"{s.phone}@s.whatsapp.net" if s.phone else None, "name": "Me"}); continue
        by_name = next((c for c in s.contacts if c.get("name") and c["name"].lower() == q and "@c.us" in c["id"]), None) or next((c for c in s.contacts if c.get("name") and c["name"].lower() == q), None)
        if by_name:
            resolved.append({"query": q, "jid": by_name["id"], "name": by_name["name"]}); continue
        by_partial = next((c for c in s.contacts if c.get("name") and q in c["name"].lower() and "@c.us" in c["id"]), None) or next((c for c in s.contacts if c.get("name") and q in c["name"].lower()), None)
        if by_partial:
            resolved.append({"query": q, "jid": by_partial["id"], "name": by_partial["name"]}); continue
        by_number = next((c for c in s.contacts if c.get("number") and q in c["number"]), None)
        if by_number:
            resolved.append({"query": q, "jid": by_number["id"], "name": by_number["name"]}); continue
        if s.phone and q in s.phone:
            resolved.append({"query": q, "jid": f"{s.phone}@s.whatsapp.net", "name": "Me"}); continue
        resolved.append({"query": q, "jid": None, "name": q})

    results = []
    for group in s.groups:
        participants = group.get("participants", [])
        matched = 0
        for r in resolved:
            if r["jid"]:
                found = any(p["id"] == r["jid"] for p in participants)
            else:
                found = any((p.get("number") and r["query"] in (p["number"] or "")) or (p.get("name") and r["query"] in (p["name"] or "").lower()) for p in participants)
            if found:
                matched += 1
        if matched == len(resolved):
            results.append({"id": group["id"], "name": group["name"], "participantCount": group.get("participantCount", 0)})
    return jsonify(clean({"queries": [{"query": r["query"], "resolved": r["name"]} for r in resolved], "commonGroups": results, "totalGroups": len(s.groups)}))


@app.get("/<username>/latest-received-message")
def latest_received_message(username):
    s = get_session(username)
    include_groups = request.args.get("groups", "").lower() == "true"

    if s.latest_received_message is not None:
        msg = s.latest_received_message
        chat_jid = msg.get("chatJid", msg.get("fromJid", ""))
        if include_groups or "@g.us" not in chat_jid:
            return jsonify(clean(with_media(s, msg)))

    # NOTHING LIVE YET, SO FALL BACK ON THE HISTORY SYNC TIMESTAMPS.
    with s.lock:
        chats = [c for c in s.chats if c.get("timestamp", 0) > 0 and "@broadcast" not in c.get("id", "") and "@newsletter" not in c.get("id", "")]
        if not include_groups:
            chats = [c for c in chats if not c.get("isGroup")]
        if chats:
            most_recent = max(chats, key=lambda c: c.get("timestamp", 0))
            body = most_recent.get("lastMessage") or ""
            return jsonify(clean({
                "chatName": most_recent.get("name", ""),
                "jid": most_recent.get("id", ""),
                "isGroup": most_recent.get("isGroup", False),
                "timestamp": most_recent.get("timestamp", 0),
                "body": body if body else "(message content not yet synced - history is still loading)",
                "from": None,
                "fromJid": None,
                "note": "Showing most recently active chat from sync metadata; full message history is still loading in the background.",
            }))

    return jsonify({"error": "No received messages found"}), 404


@app.get("/<username>/latest-sent-message")
def latest_sent_message(username):
    s = get_session(username)
    if s.latest_sent_message is None:
        return jsonify({"error": "No sent messages found"}), 404
    return jsonify(clean(s.latest_sent_message))


@app.post("/<username>/create-group")
def create_group(username):
    """Start a new group with nobody else in it yet, and hand back its id."""
    name = (request.json or {}).get("name", "").strip()
    s = get_session(username)

    if not name:
        return jsonify({"error": "name is required"}), 400

    if not s.client or not s.connected:
        return jsonify({"error": "Not connected"}), 503

    try:
        made = s.client.create_group(name)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    gid = jid_str(made.JID)

    with s.lock:
        if not any(g["id"] == gid for g in s.groups):
            s.groups.append({"id": gid, "name": clean(name), "description": "", "participants": [], "participantCount": 0, "createdAt": None})
        if not any(c["id"] == gid for c in s.chats):
            s.chats.append({"id": gid, "name": clean(name), "isGroup": True, "unreadCount": 0, "lastMessage": "", "timestamp": 0, "archived": False})

    persist(s)

    return jsonify({"id": gid, "name": clean(name)})


@app.post("/<username>/set-group-photo")
def set_group_photo(username):
    """Put a picture on a group. The photo comes as base64 of a JPEG."""
    body = request.json or {}
    group = (body.get("group") or "").strip()
    photo = body.get("photo") or ""
    s = get_session(username)

    if not group or not photo:
        return jsonify({"error": "group and photo are required"}), 400

    if not s.client or not s.connected:
        return jsonify({"error": "Not connected"}), 503

    try:
        s.client.set_group_photo(make_jid(group), base64.b64decode(photo))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"id": group})


@app.get("/<username>/pushed")
def pushed(username):
    """The chats this device has sent something into since a given moment."""
    s = get_session(username)
    since = float(request.args.get("since", 0))

    with s.lock:
        found = [m for m in s.pushed if m["at"] >= since]

    return jsonify(found)


@app.get("/<username>/recent-sent")
def recent_sent(username):
    """The owner's own last few messages across every chat, oldest first, each one carrying the
    chat it was written in."""
    s = get_session(username)
    limit = int(request.args.get("limit", 25))

    with s.lock:
        found = list(s.recent_sent)[-limit:]

    return jsonify(clean([with_media(s, m) for m in found]))


@app.post("/<username>/rebuild-senders")
def rebuild_senders(username):
    """Re-run group sender resolution after fresh participant data is available."""
    s = get_session(username)
    bulk_resolve_group_lids(s)
    with s.lock:
        s.rebuild_group_senders()
        s.rebuild_latest_received()
        s.rebuild_latest_sent()
    persist(s)
    return jsonify({"success": True})


@app.get("/<username>/query-messages")
def query_messages(username):
    s = get_session(username)
    chat_q = (request.args.get("chat") or "").strip().lower()
    sender_q = (request.args.get("sender") or "").strip().lower()
    raw_limit = int(request.args.get("limit", 5))
    # A SENDER QUERY SCANS EVERYTHING BEFORE IT CUTS, SO IT NEEDS THE HIGHER CAP.
    max_limit = 200 if sender_q else 50
    limit = min(raw_limit, max_limit)
    from_me_arg = request.args.get("fromMe", "").lower()
    date_q = (request.args.get("date") or "").strip().lower()  # "today", "yesterday" OR "YYYY-MM-DD".
    order = (request.args.get("order") or "newest").strip().lower()

    day_start = day_end = None
    if date_q:
        from datetime import timezone
        now_utc = datetime.utcnow()
        if date_q == "today":
            target_date = now_utc.date()
        elif date_q == "yesterday":
            from datetime import timedelta
            target_date = (now_utc - timedelta(days=1)).date()
        else:
            try:
                from datetime import date as dt_date
                target_date = dt_date.fromisoformat(date_q)
            except ValueError:
                return jsonify({"error": f"Invalid date '{date_q}'. Use 'today', 'yesterday', or 'YYYY-MM-DD'"}), 400
        day_start = int(datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc).timestamp())
        day_end = day_start + 86400

    # SNAPSHOTTED WHOLE: A HISTORY SYNC IS ADDING TO THESE ON ANOTHER THREAD.
    with s.lock:
        messages_snap = {k: list(v) for k, v in s.messages.items()}
        media_snap = {k: list(v) for k, v in s.media.items()}
        chats_snap = list(s.chats)
        groups_snap = list(s.groups)
        contacts_snap = list(s.contacts)
        user_phone = s.phone
        user_name = s.name

    # EXACT FIRST, THEN SUBSTRING, THEN EMOJI STRIPPED.
    target_jid = None
    target_name = None
    if chat_q:
        all_chats = {c["id"]: c.get("name", c["id"].split("@")[0]) for c in chats_snap}
        for g in groups_snap:
            all_chats.setdefault(g["id"], g.get("name", g["id"].split("@")[0]))
        # CONTACTS TOO: A DIRECT CHAT'S DISPLAY NAME IS OFTEN THE PHONE NUMBER.
        for c in contacts_snap:
            cname = c.get("name")
            if cname and cname != c.get("number"):
                all_chats[c["id"]] = cname
        # THE AGENT APPENDS FILLER, SO "the boys group" HAS TO REACH "The boys".
        chat_q_clean = re.sub(r'\s+(group|chat|bhai)\s*$', '', chat_q, flags=re.IGNORECASE).strip() or chat_q
        match = next((jid for jid, name in all_chats.items() if name.lower() == chat_q_clean), None)
        if not match and chat_q_clean != chat_q:
            match = next((jid for jid, name in all_chats.items() if name.lower() == chat_q), None)
        if not match:
            match = next((jid for jid, name in all_chats.items() if name_match(chat_q_clean, name)), None)
        if not match and chat_q_clean != chat_q:
            match = next((jid for jid, name in all_chats.items() if name_match(chat_q, name)), None)
        if match:
            target_jid, target_name = match, all_chats[match]
        else:
            return jsonify({"error": f"Chat '{chat_q}' not found"}), 404

    # BOTH PHONE NUMBERS AND LID IDS: STORED MESSAGES USE EITHER.
    sender_phones = set()
    if sender_q:
        for c in contacts_snap:
            name = (c.get("name") or "")
            number = (c.get("number") or "")
            cid = c.get("id", "")
            if name_match(sender_q, name) or sender_q in number:
                if number:
                    sender_phones.add(number)
                if "@lid" in cid:
                    sender_phones.add(cid.split("@")[0])
        # GROUP PARTICIPANTS ARE NOT ALWAYS IN CONTACTS.
        for g in groups_snap:
            for p in g.get("participants", []):
                pname = (p.get("name") or "")
                pnum = (p.get("number") or "")
                pid = p.get("id", "")
                if name_match(sender_q, pname) or (pnum and sender_q in pnum):
                    if pnum:
                        sender_phones.add(pnum)
                    if pid and "@lid" in pid:
                        sender_phones.add(pid.split("@")[0])

    # phone/LID → SAVED NAME, FOR THE NUMERIC `from` FIELDS IN THE RESULTS.
    phone_to_name = {}
    for c in contacts_snap:
        cname = c.get("name")
        cnum = c.get("number")
        cid = c.get("id", "")
        if cname and cnum and cname != cnum:
            phone_to_name[cnum] = cname
        if cname and "@" in cid and cname != cnum:
            phone_to_name[cid.split("@")[0]] = cname

    def resolve_from(m):
        """Replace `from` with the saved contact name when one is available."""
        from_jid = (m.get("fromJid") or "")
        from_jid_phone = from_jid.split("@")[0] if "@" in from_jid else ""
        if not from_jid_phone:
            return m
        saved_name = phone_to_name.get(from_jid_phone)
        if saved_name:
            return {**m, "from": saved_name}
        from_val = (m.get("from") or "").strip()
        if from_val and from_val.lstrip("+").isdigit():
            saved_name = phone_to_name.get(from_val)
            if saved_name:
                return {**m, "from": saved_name}
        return m

    jids = [target_jid] if target_jid else list(set(messages_snap.keys()) | set(media_snap.keys()))
    chat_name_map = {c["id"]: c.get("name", c["id"].split("@")[0]) for c in chats_snap}
    for g in groups_snap:
        chat_name_map.setdefault(g["id"], g.get("name", g["id"].split("@")[0]))
    # A DIRECT CHAT HAS NO DISPLAY NAME, SO THE CONTACT BEATS THE PHONE NUMBER.
    for c in contacts_snap:
        cname = c.get("name")
        if cname and cname != c.get("number"):
            chat_name_map[c["id"]] = cname
    if user_phone:
        chat_name_map[f"{user_phone}@s.whatsapp.net"] = user_name or "Saved Messages"

    def passes_filters(m, jid):
        if from_me_arg == "true" and not m.get("fromMe"):
            return False
        if from_me_arg == "false" and m.get("fromMe"):
            return False
        if day_start is not None:
            if not (day_start <= m.get("timestamp", 0) < day_end):
                return False
        if sender_q:
            if m.get("fromMe"):
                return False
            stored_name = (m.get("from") or "")
            from_jid_phone = (m.get("fromJid") or "").split("@")[0]
            # A STORED pushName IS OFTEN THE SHORT ONE: "Rasool", NOT "Rasool Khan".
            resolved_name = phone_to_name.get(from_jid_phone, stored_name)
            if (not name_match(sender_q, stored_name)
                    and not name_match(sender_q, resolved_name)
                    and from_jid_phone not in sender_phones):
                return False
        return True

    if target_jid:
        chat_name = target_name or chat_name_map.get(target_jid, target_jid.split("@")[0])
        all_msgs = messages_snap.get(target_jid, []) + media_snap.get(target_jid, [])
        filtered = [{**resolve_from(m), "chatName": chat_name} for m in all_msgs if passes_filters(m, target_jid)]
        filtered.sort(key=lambda m: m.get("timestamp", 0), reverse=(order != "oldest"))
        results = filtered[:limit]
    else:
        candidates = []

        if sender_q:
            # A SENDER WITH NO CHAT MEANS THE DIRECT CHAT, NEVER A GROUP: A GROUP
            # HAS TO BE NAMED OUTRIGHT.
            direct_jid = None
            # THE CONTACT'S OWN id, NOT A JID REBUILT FROM THE NUMBER: THE FORMATS DIFFER.
            for c in contacts_snap:
                cname = (c.get("name") or "")
                cid = c.get("id", "")
                if "@s.whatsapp.net" in cid and name_match(sender_q, cname):
                    if cid in messages_snap or cid in media_snap:
                        direct_jid = cid
                        break
            if not direct_jid and sender_phones:
                for phone in sorted(sender_phones):
                    cjid = f"{phone}@s.whatsapp.net"
                    if cjid in messages_snap or cjid in media_snap:
                        direct_jid = cjid
                        break
            if not direct_jid:
                if not sender_phones and not any(
                    "@s.whatsapp.net" in c.get("id", "") and name_match(sender_q, c.get("name") or "")
                    for c in contacts_snap
                ):
                    return jsonify({"error": f"Could not resolve sender '{sender_q}' to a contact"}), 404
                return jsonify({"error": f"No direct chat found for '{sender_q}'. If you meant a group message, specify the group name too."}), 404
            # IN A DIRECT CHAT EVERY INCOMING MESSAGE IS THEIRS, SO NO SENDER FILTER.
            chat_name = chat_name_map.get(direct_jid, direct_jid.split("@")[0])
            for m in messages_snap.get(direct_jid, []) + media_snap.get(direct_jid, []):
                if not m.get("fromMe"):
                    if from_me_arg == "true":
                        continue
                    candidates.append({**resolve_from(m), "chatName": chat_name})
                else:
                    if from_me_arg == "false":
                        continue
                    candidates.append({**resolve_from(m), "chatName": chat_name})
        else:
            for jid in jids:
                if "@newsletter" in jid or "@broadcast" in jid:
                    continue
                chat_name = chat_name_map.get(jid, jid.split("@")[0])
                for m in messages_snap.get(jid, []) + media_snap.get(jid, []):
                    if passes_filters(m, jid):
                        candidates.append({**resolve_from(m), "chatName": chat_name})

        candidates.sort(key=lambda m: m.get("timestamp", 0), reverse=(order != "oldest"))
        results = candidates[:limit]

    if not results:
        return jsonify({"error": "No matching messages found"}), 404
    return jsonify(clean([with_media(s, m) for m in results]))




def periodic_persist():
    while True:
        try:
            time.sleep(60)
            for s in list(sessions.values()):
                try:
                    if s.connected:
                        persist(s)
                except Exception as e:
                    pass
        except Exception as e:
            pass




def cleanup_stale_files():
    if not DATA_DIR.exists():
        return
    
    for user_dir in DATA_DIR.iterdir():
        if not user_dir.is_dir():
            continue
        # A HALF WRITTEN UPLOAD IS RUBBISH.
        for f in user_dir.glob("*.upload"):
            try:
                f.unlink()
            except Exception:
                pass


def flush_all_sessions():
    """Drain all pending uploads and wait for completion before process exit."""
    active = list(sessions.values())
    for s in active:
        try:
            if s.persist_timer:
                s.persist_timer.cancel()
                s.persist_timer = None
            persist(s)
        except Exception as e:
            pass


def handle_shutdown(signum, frame):
    # WHO ASKED. A BRIDGE THAT WENT DOWN BECAUSE HAPPY EXITED AND ONE THAT DIED ON ITS OWN LOOK
    # THE SAME IN THIS LOG OTHERWISE, AND THEY ARE NOT THE SAME PROBLEM.
    logger.info(f"[shutdown] signal {signum}, writing everything out and going down")
    flush_all_sessions()
    sys.exit(0)


if __name__ == "__main__":
    import atexit
    import signal

    atexit.register(flush_all_sessions)
    signal.signal(signal.SIGTERM, handle_shutdown)
    try:
        signal.signal(signal.SIGINT, handle_shutdown)
    except (OSError, ValueError):
        pass

    cleanup_stale_files()
    threading.Thread(target=periodic_persist, daemon=True).start()
    threading.Thread(target=scannable, daemon=True).start()
    pass
    app.run(host="127.0.0.1", port=PORT, threaded=True)
