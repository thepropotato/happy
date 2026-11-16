"""Everyone a name could mean when sending, so a send never settles on the first match."""

from whatsapp_server import nearing


def looks_saved(contact):
    """Whether the phone book holds them; a name that is not their own profile name was typed by the person."""
    if "saved" in contact:
        return contact["saved"]
    return contact.get("name", "") not in ("", contact.get("number"), contact.get("profile"), contact.get("business"))


def has_written_to(session, jid):
    return any(m.get("fromMe") for store in (session.messages, session.media) for m in store.get(jid, []))


def rank(asked, name, profile):
    """(0 for the saved name or 1 for the profile, 0 for the whole word or 1 for a start of one), or None."""
    for field, text in enumerate((name, profile)):
        how = nearing.alike(asked, text)
        if how is not None:
            return field, how
    return None


def one_each(people):
    """One entry a person: the same someone is often held under a phone number and a @lid nobody has mapped yet."""
    by_jid = {}
    for person in people:
        by_jid.setdefault(person["jid"], person)
    numbers = {p["name"].lower() for p in by_jid.values() if p["jid"].endswith("@s.whatsapp.net")}
    return [p for p in by_jid.values() if not (p["jid"].endswith("@lid") and p["name"].lower() in numbers)]


def matching(session, asked, chat_of, fallback):
    """Everyone asked could mean, closest kind of match only; a stranger counts only when nobody known matches."""
    entry = lambda jid, name, number, saved, group=False: {
        "jid": jid, "name": name, "number": number, "saved": saved, "talked": group or has_written_to(session, jid), "group": group}
    found = []
    if not asked[:1].isdigit() and not asked.startswith("+") and "@" not in asked:
        for contact in session.contacts:
            order = rank(asked, contact.get("name", ""), contact.get("profile", ""))
            if order is not None:
                person = entry(chat_of(session, contact["id"]), contact.get("name", ""), contact.get("number", ""), looks_saved(contact))
                found.append(((0 if person["saved"] or person["talked"] else 1, *order), person))
        for group in session.groups:
            how = nearing.alike(asked, group.get("name", ""))
            if how is not None:
                found.append(((0, 0, how), entry(group["id"], group["name"], "", True, group=True)))
    if found:
        best = min(order for order, _ in found)
        return one_each([person for order, person in found if order == best])
    try:
        jid = fallback(session, asked)
    except ValueError:
        return []
    contact = next((c for c in session.contacts if chat_of(session, c["id"]) == jid or c["id"] == jid), {})
    number = contact.get("number") or jid.split("@")[0]
    return [entry(jid, contact.get("name") or asked, number, looks_saved(contact) if contact else jid.endswith("@g.us"), group=jid.endswith("@g.us"))]
