"""GOOGLE CALENDAR: WHAT IS COMING UP, WHEN SOMEBODY IS FREE, AND CHANGING IT."""

from datetime import datetime, timedelta, timezone

from servers.google import account, mcp
from servers.shared.answering import ok, some

HERE = "primary"

MOST = 25


@mcp.tool()
def list_events(days: int = 7, calendar_id: str = "primary") -> str:
    """List what is in the calendar over the next few days, soonest first.

    Days counts forward from now, so 1 is the rest of today and tomorrow. Each
    event comes back with an id, which is what update_event and delete_event want.
    """
    service = account.calendar()
    found = (
        service.events()
        .list(
            calendarId=calendar_id or HERE,
            timeMin=stamped(0),
            timeMax=stamped(max(1, int(days))),
            singleEvents=True,
            orderBy="startTime",
            maxResults=MOST,
        )
        .execute()
    )

    return ok([outlined(each) for each in found.get("items", [])])


@mcp.tool()
def find_free_time(days: int = 3, minutes: int = 30) -> str:
    """Find the gaps in the calendar long enough for a meeting of this length.

    Use this before offering somebody a time, rather than reading the whole
    calendar and working it out.
    """
    service = account.calendar()
    asked = {
        "timeMin": stamped(0),
        "timeMax": stamped(max(1, int(days))),
        "items": [{"id": HERE}],
    }
    busy = (
        service.freebusy().query(body=asked).execute().get("calendars", {}).get(HERE, {})
    )

    return ok(gaps(busy.get("busy", []), max(5, int(minutes))))


@mcp.tool()
def create_event(
    summary: str,
    start: str,
    end: str,
    description: str = "",
    attendees: str = "",
    calendar_id: str = "primary",
) -> str:
    """Put something in the calendar.

    start and end are whole times like 2026-08-04T15:00:00. Attendees are email
    addresses separated by commas, and inviting somebody sends them a mail.
    """
    made = (
        account.calendar()
        .events()
        .insert(calendarId=calendar_id or HERE, body=laid(summary, start, end, description, attendees))
        .execute()
    )

    return ok({"created": True, "id": made.get("id"), "summary": summary, "start": start})


@mcp.tool()
def update_event(
    event_id: str,
    summary: str = "",
    start: str = "",
    end: str = "",
    description: str = "",
    calendar_id: str = "primary",
) -> str:
    """Change an event that is already in the calendar. Anything left empty stays as it is."""
    service = account.calendar()
    held = service.events().get(calendarId=calendar_id or HERE, eventId=event_id).execute()

    if summary:
        held["summary"] = summary
    if description:
        held["description"] = description
    if start:
        held["start"] = {"dateTime": start}
    if end:
        held["end"] = {"dateTime": end}

    changed = (
        service.events()
        .update(calendarId=calendar_id or HERE, eventId=event_id, body=held)
        .execute()
    )

    return ok({"updated": True, "id": changed.get("id"), "summary": changed.get("summary")})


@mcp.tool()
def delete_event(event_id: str, calendar_id: str = "primary") -> str:
    """Take an event out of the calendar. Anybody invited is told it is off."""
    account.calendar().events().delete(calendarId=calendar_id or HERE, eventId=event_id).execute()

    return ok({"deleted": True, "id": event_id})


def outlined(event):
    when = event.get("start") or {}

    return {
        "id": event.get("id"),
        "summary": some(event.get("summary", ""), 120),
        "start": when.get("dateTime") or when.get("date"),
        "end": (event.get("end") or {}).get("dateTime") or (event.get("end") or {}).get("date"),
        "where": some(event.get("location", ""), 80),
        "with": [each.get("email") for each in (event.get("attendees") or [])][:8],
    }


def laid(summary, start, end, description, attendees):
    body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start},
        "end": {"dateTime": end},
    }

    asked = [each.strip() for each in (attendees or "").split(",") if each.strip()]

    if asked:
        body["attendees"] = [{"email": each} for each in asked]

    return body


def gaps(busy, minutes):
    """THE FREE STRETCHES BETWEEN THE BUSY ONES, AND ONLY THE USEFULLY LONG ONES."""
    wanted = timedelta(minutes=minutes)
    edge = datetime.now(timezone.utc)
    free = []

    for each in busy:
        began = read(each["start"])

        if began - edge >= wanted:
            free.append({"from": edge.isoformat(), "to": began.isoformat()})

        edge = max(edge, read(each["end"]))

    return free[:MOST]


def read(when):
    return datetime.fromisoformat(when.replace("Z", "+00:00"))


def stamped(days):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
