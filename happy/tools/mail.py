"""Email over IMAP and SMTP, so any provider with an app password works without signing up for anything."""

import email
import email.policy
import email.utils
import imaplib
import re
import smtplib
import ssl
from email.message import EmailMessage
from typing import Annotated

from happy.config import Config, secrets
from happy.tools import tool
from happy.tools.browser import text_of

HOSTS = {
    "gmail.com": ("imap.gmail.com", "smtp.gmail.com"), "googlemail.com": ("imap.gmail.com", "smtp.gmail.com"),
    "outlook.com": ("outlook.office365.com", "smtp.office365.com"), "hotmail.com": ("outlook.office365.com", "smtp.office365.com"),
    "live.com": ("outlook.office365.com", "smtp.office365.com"), "icloud.com": ("imap.mail.me.com", "smtp.mail.me.com"),
    "me.com": ("imap.mail.me.com", "smtp.mail.me.com"), "yahoo.com": ("imap.mail.yahoo.com", "smtp.mail.yahoo.com"),
    "zoho.com": ("imap.zoho.com", "smtp.zoho.com"), "proton.me": ("127.0.0.1", "127.0.0.1"),
}


def account():
    cfg = Config()
    address = cfg.get("mail.address") or ""
    password = secrets().get("mail_password", "")
    if not address or not password:
        return None
    domain = address.rsplit("@", 1)[-1].lower()
    imap_host, smtp_host = HOSTS.get(domain, (f"imap.{domain}", f"smtp.{domain}"))
    return address, password, cfg.get("mail.imap_host") or imap_host, cfg.get("mail.smtp_host") or smtp_host


def connected():
    return account() is not None


def inbox():
    address, password, host, _ = account()
    box = imaplib.IMAP4_SSL(host, ssl_context=ssl.create_default_context(), timeout=20)
    box.login(address, password)
    box.select("INBOX")
    return box


def body_of(message):
    if message.is_multipart():
        plain = message.get_body(preferencelist=("plain",))
        if plain:
            return plain.get_content()
        rich = message.get_body(preferencelist=("html",))
        return text_of(rich.get_content()) if rich else ""
    content = message.get_content()
    return text_of(content) if message.get_content_type() == "text/html" else content


def summary(uid, message):
    sender = email.utils.parseaddr(message.get("From", ""))
    when = message.get("Date", "")
    try:
        when = email.utils.parsedate_to_datetime(when).strftime("%a %d %b, %I:%M %p")
    except (TypeError, ValueError):
        pass
    snippet = re.sub(r"\s+", " ", body_of(message))[:160]
    return f"#{uid} from {sender[0] or sender[1]} <{sender[1]}>, {when}: {message.get('Subject', '(no subject)')} — {snippet}"


def fetch(box, uid, peek=True):
    kind = "(BODY.PEEK[])" if peek else "(RFC822)"
    status, data = box.uid("FETCH", uid, kind)
    if status != "OK" or not data or not data[0]:
        return None
    return email.message_from_bytes(data[0][1], policy=email.policy.default)


@tool(say="Checking your mail.", label="Checking your mail")
def check_mail(
    unread_only: bool = True,
    count: Annotated[int, "how many, newest first"] = 5,
    sender: Annotated[str, "only mail from this name or address"] = "",
    words: Annotated[str, "only mail containing these words"] = "",
):
    """List recent emails in the inbox, newest first, with who sent them and what they are about."""
    if not connected():
        return "Email is not set up, so there is no mail to read. It can be added in Setup with an app password."
    box = inbox()
    try:
        criteria = ["UNSEEN" if unread_only else "ALL"]
        if sender:
            criteria += ["FROM", f'"{sender}"']
        if words:
            criteria += ["TEXT", f'"{words}"']
        status, data = box.uid("SEARCH", None, *criteria)
        uids = data[0].split()[-max(1, min(count, 20)):][::-1] if status == "OK" and data[0] else []
        if not uids:
            return "No unread mail." if unread_only and not (sender or words) else "No matching mail."
        rows = [summary(u.decode(), m) for u in uids if (m := fetch(box, u))]
        return "\n".join(rows)
    finally:
        box.logout()


@tool(say="Opening it.", label="Reading the email", needs=connected)
def read_mail(number: Annotated[str, "the # number from check_mail"]):
    """Read one email in full. Marks it as read."""
    box = inbox()
    try:
        message = fetch(box, number.lstrip("#"), peek=False)
        if not message:
            return f"There is no email #{number}."
        return f"From: {message.get('From')}\nDate: {message.get('Date')}\nSubject: {message.get('Subject')}\n\n{body_of(message)[:6000]}"
    finally:
        box.logout()


def address_for(name, box):
    status, data = box.uid("SEARCH", None, "FROM", f'"{name}"')
    if status == "OK" and data[0]:
        message = fetch(box, data[0].split()[-1])
        if message:
            return email.utils.parseaddr(message.get("From", ""))[1]
    return None


@tool(say="Sending the email.", label="Emailing {to}", needs=connected)
def send_mail(
    to: Annotated[str, "an email address, or the name of someone who has emailed before"],
    subject: str,
    body: Annotated[str, "the whole message, ready to send"],
    reply_to: Annotated[str, "the # number of the email being answered, if this is a reply"] = "",
):
    """Send an email, or reply to one."""
    address, password, _, smtp_host = account()
    outgoing = EmailMessage()
    outgoing["From"] = address
    outgoing["Subject"] = subject
    box = inbox()
    try:
        recipient = to if "@" in to else address_for(to, box)
        if not recipient:
            return f"I don't have an email address for {to}."
        if reply_to:
            original = fetch(box, reply_to.lstrip("#"))
            if original:
                outgoing["In-Reply-To"] = original.get("Message-ID", "")
                outgoing["References"] = f"{original.get('References', '')} {original.get('Message-ID', '')}".strip()
                if not subject.lower().startswith("re:"):
                    outgoing.replace_header("Subject", f"Re: {original.get('Subject', subject)}")
    finally:
        box.logout()
    outgoing["To"] = recipient
    outgoing.set_content(body)
    with smtplib.SMTP(smtp_host, 587, timeout=30) as server:
        server.starttls(context=ssl.create_default_context())
        server.login(address, password)
        server.send_message(outgoing)
    return f"Sent to {recipient}."
