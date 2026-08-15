"""THE ONE GOOGLE ACCOUNT MAIL, CALENDAR AND DRIVE ALL RUN AS."""

from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from servers.google import mcp
from servers.shared import credentials

NAME = "google"

WHERE = "https://oauth2.googleapis.com/token"

MISSING = "Google is not signed in. Connect it in Happy's connections panel."


def signed():
    """LIVE CREDENTIALS, CHECKED ON THE WAY INTO EVERY CALL AND RENEWED IN PLACE IF SPENT."""
    held = credentials.kept(NAME)
    tokens, client = held["tokens"], held["client"]

    if not tokens.get("refresh_token") and not tokens.get("access_token"):
        raise PermissionError(MISSING)

    creds = Credentials(
        token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token"),
        token_uri=WHERE,
        client_id=client.get("client_id"),
        client_secret=client.get("client_secret"),
        expiry=ending(tokens.get("expires_at")),
    )

    if creds.valid and not credentials.spent(tokens):
        return creds

    if not creds.refresh_token:
        raise PermissionError(MISSING)

    try:
        creds.refresh(Request())
    except Exception as error:
        # THE REFRESH TOKEN ITSELF HAS GONE, WHICH NO AMOUNT OF REFRESHING MENDS: GOOGLE DROPS
        # ONE WEEKLY FOR AN APP LEFT UNPUBLISHED. SAY THE ONE THING THAT FIXES IT.
        raise PermissionError(credentials.STALE.format(service="Google")) from error

    credentials.put(NAME, tokens={**tokens, **renewed(creds)})

    return creds


def renewed(creds):
    """WHAT A REFRESH CHANGED, AND ONLY THAT."""
    kept = {"access_token": creds.token}

    if creds.expiry:
        kept["expires_at"] = creds.expiry.replace(tzinfo=timezone.utc).timestamp()

    return kept


def ending(when):
    """GOOGLE WANTS THE EXPIRY AS A NAIVE UTC TIME."""
    if not when:
        return None

    return datetime.fromtimestamp(float(when), timezone.utc).replace(tzinfo=None)


@mcp.tool()
def who_signed_in() -> str:
    """THE NAME ON THIS ACCOUNT. HAPPY ASKS IT HIMSELF; IT IS NEVER OFFERED TO THE MODEL."""
    inbox = mail().users()

    try:
        found = inbox.settings().sendAs().list(userId="me").execute()

        for entry in found.get("sendAs") or []:
            if entry.get("isPrimary") and entry.get("displayName"):
                return str(entry["displayName"]).strip()
    except Exception:
        pass  # THE SIGN IN MAY NOT REACH THE SETTINGS, AND THE ADDRESS BELOW ALWAYS DOES.

    return str(inbox.getProfile(userId="me").execute().get("emailAddress") or "").strip()


def mail():
    return build("gmail", "v1", credentials=signed(), cache_discovery=False)


def calendar():
    return build("calendar", "v3", credentials=signed(), cache_discovery=False)


def drive():
    return build("drive", "v3", credentials=signed(), cache_discovery=False)
