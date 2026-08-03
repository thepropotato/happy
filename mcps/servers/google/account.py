"""THE ONE GOOGLE ACCOUNT MAIL, CALENDAR AND DRIVE ALL RUN AS.

ONE SIGN IN COVERS ALL THREE, SO THERE IS ONE SET OF CREDENTIALS AND ONE PLACE
THAT KEEPS THEM ALIVE. A REFRESHED TOKEN GOES STRAIGHT BACK INTO THE DATABASE,
BECAUSE THE PANEL READS THAT SAME ROW TO SAY WHETHER GOOGLE IS SIGNED IN.
"""

from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from servers.shared import credentials

NAME = "google"

WHERE = "https://oauth2.googleapis.com/token"

MISSING = "Google is not signed in. Connect it in Happy's connections panel."


def signed():
    """LIVE CREDENTIALS, RENEWED AND WRITTEN BACK IF THE OLD ONES HAD RUN OUT."""
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

    if creds.valid:
        return creds

    if not creds.refresh_token:
        raise PermissionError(MISSING)

    creds.refresh(Request())
    credentials.put(NAME, tokens={**tokens, **renewed(creds)})

    return creds


def renewed(creds):
    """WHAT A REFRESH CHANGED, AND ONLY THAT. THE REFRESH TOKEN ITSELF IS RARELY
    SENT BACK AND MEANS KEEP THE ONE YOU ALREADY HAVE."""
    kept = {"access_token": creds.token}

    if creds.expiry:
        kept["expires_at"] = creds.expiry.replace(tzinfo=timezone.utc).timestamp()

    return kept


def ending(when):
    """GOOGLE WANTS THE EXPIRY AS A NAIVE UTC TIME. WITHOUT ONE IT BELIEVES A DEAD
    TOKEN IS STILL GOOD AND NEVER REFRESHES."""
    if not when:
        return None

    return datetime.fromtimestamp(float(when), timezone.utc).replace(tzinfo=None)


def mail():
    return build("gmail", "v1", credentials=signed(), cache_discovery=False)


def calendar():
    return build("calendar", "v3", credentials=signed(), cache_discovery=False)


def drive():
    return build("drive", "v3", credentials=signed(), cache_discovery=False)
