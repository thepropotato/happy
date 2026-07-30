"""GETTING A SIGN IN OUT OF A SERVICE, AND KEEPING IT ALIVE AFTERWARDS.

THE PROTOCOL'S OWN SIGN IN IS SPRUNG BY A 401, WHICH ASSUMES EVERY SERVER TURNS
A STRANGER AWAY. GOOGLE'S DO NOT. gmailmcp AND ITS SIBLINGS HAND THEIR WHOLE
TOOL LIST TO ANYBODY AND ONLY REFUSE WHEN A TOOL IS ACTUALLY CALLED, SO NOTHING
EVER SPRANG IT: NO CONSENT PAGE EVER OPENED, CONNECTING LOOKED LIKE IT HAD
WORKED, AND EVERY TOOL FAILED THE FIRST TIME THE MODEL REACHED FOR ONE.

SO THE SIGN IN HAPPENS HERE INSTEAD, IN THE OPEN, THE MOMENT A PERSON PRESSES
CONNECT — AND ONCE FOR A WHOLE FAMILY, BECAUSE ONE GOOGLE ACCOUNT SAYING YES TO
MAIL, CALENDAR AND DRIVE IS ONE QUESTION AND NOT THREE.

NOTHING IN HERE IS EVER REACHED BY A TOOL. A BROWSER WINDOW THAT APPEARS BECAUSE
THE MODEL WANTED IT TO IS NOT AN ANSWER TO ANYTHING SOMEBODY ASKED OUT LOUD.
"""

import asyncio
import base64
import hashlib
import secrets
import time
from urllib.parse import urlencode, urlparse

import httpx

from mcps import directory, tokens

PATIENCE = 30

# RENEW THIS LONG BEFORE IT DIES, SO NOTHING EXPIRES BETWEEN BEING CHECKED AND USED.
EARLY = 60

GOOGLE = "accounts.google.com"

# GOOGLE HANDS OVER A REFRESH TOKEN ONLY TO SOMEBODY WHO ASKS IN THESE WORDS, AND
# ONLY WHEN THE CONSENT IS ACTUALLY SHOWN. WITHOUT THEM THE SIGN IN DIES IN AN HOUR.
OFFLINE = {"access_type": "offline", "prompt": "consent"}

MINE = {
    "client_name": "Happy",
    "grant_types": ["authorization_code", "refresh_token"],
    "response_types": ["code"],
    "token_endpoint_auth_method": "none",
}

BRING_ONE = "{label} will not register Happy. Add a client of your own first."

WRONG_WAY = "That sign in came back wrong. Try connecting again."


def signed(name):
    """TRUE WHEN THIS SERVICE HAS A SIGN IN, WHOEVER IN ITS FAMILY DID IT."""
    return bool((tokens.kept(name).get("tokens") or {}).get("access_token"))


def sign_in(row, doorway):
    """THE WHOLE SIGN IN: A BROWSER, A PERSON SAYING YES, AND A TOKEN BACK.

    BLOCKS THE THREAD THAT ASKED FOR IT, WHICH IS THE PANEL'S OWN AND NOT THE
    ONE ANYBODY IS TALKING TO.
    """
    name = row["name"]
    where = endpoints(name, row["address"])
    known = client(row, where, doorway)

    verifier = secrets.token_urlsafe(96)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).decode().rstrip("=")
    state = secrets.token_urlsafe(32)

    asked = {
        "response_type": "code",
        "client_id": known["client_id"],
        "redirect_uri": doorway.address,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }

    scopes = directory.wants(name) or where.get("scopes") or []

    if scopes:
        asked["scope"] = " ".join(scopes)

    if GOOGLE in where["authorization_endpoint"]:
        asked.update(OFFLINE)

    doorway.show(f"{where['authorization_endpoint']}?{urlencode(asked)}")

    code, back = doorway.waited()

    if back != state:
        raise PermissionError(WRONG_WAY)

    held = traded(
        where["token_endpoint"],
        {"grant_type": "authorization_code", "code": code,
         "redirect_uri": doorway.address, "code_verifier": verifier},
        known,
    )

    tokens.put(name, tokens=held)

    return held


def client(row, where, doorway):
    """THE CLIENT TO SIGN IN AS: THE ONE SOMEBODY BROUGHT, OR ONE REGISTERED NOW.

    A SERVICE THAT REGISTERS US ITSELF IS ONE BUTTON. ONE THAT WILL NOT IS WHY
    THE PANEL ASKS FOR A CLIENT ID AND SAYS PLAINLY WHY.
    """
    from mcps import signing

    known = signing.client(row["name"])

    if known.get("client_id"):
        return known

    if not where.get("registration_endpoint"):
        raise PermissionError(BRING_ONE.format(label=row["label"]))

    got = answered(
        httpx.post(
            where["registration_endpoint"],
            json={**MINE, "redirect_uris": [doorway.address]},
            timeout=PATIENCE,
        )
    )

    if not got.get("client_id"):
        raise PermissionError(BRING_ONE.format(label=row["label"]))

    known = {
        "client_id": got["client_id"],
        "client_secret": got.get("client_secret"),
    }

    tokens.put(row["name"], client=known)

    return known


def endpoints(name, address):
    """WHERE THIS SERVER'S SIGN IN LIVES. ASKED ONCE AND THEN REMEMBERED.

    REMEMBERED BECAUSE RENEWING A TOKEN NEEDS THE SAME ANSWER, AND TWO EXTRA
    ROUND TRIPS IN FRONT OF A TOOL CALL WOULD BE HEARD AS A PAUSE.
    """
    held = tokens.kept(name).get("auth") or {}

    if held.get("token_endpoint"):
        return held

    found = discovered(address)

    tokens.put(name, auth=found)

    return found


def discovered(address):
    """WHAT THE SERVER SAYS ABOUT SIGNING INTO IT, AND WHAT ITS DOORMAN SAYS BACK."""
    parts = urlparse(address)
    root = f"{parts.scheme}://{parts.netloc}"

    resource = fetched(
        f"{root}/.well-known/oauth-protected-resource{parts.path}"
    ) or fetched(f"{root}/.well-known/oauth-protected-resource") or {}

    servers = resource.get("authorization_servers") or []
    meta = doorman(servers[0] if servers else root)

    return {
        "authorization_endpoint": meta.get("authorization_endpoint") or f"{root}/authorize",
        "token_endpoint": meta.get("token_endpoint") or f"{root}/token",
        "registration_endpoint": meta.get("registration_endpoint"),
        "scopes": resource.get("scopes_supported") or [],
    }


def doorman(where):
    """THE AUTHORIZATION SERVER'S OWN DESCRIPTION OF ITSELF, HOWEVER IT PUBLISHES IT."""
    parts = urlparse(where.rstrip("/"))
    root = f"{parts.scheme}://{parts.netloc}"
    path = parts.path.rstrip("/")

    for url in (
        f"{root}/.well-known/oauth-authorization-server{path}",
        f"{root}/.well-known/openid-configuration{path}",
        f"{root}{path}/.well-known/openid-configuration",
    ):
        found = fetched(url)

        if found:
            return found

    return {}


def fetched(url):
    try:
        answer = httpx.get(url, timeout=PATIENCE, follow_redirects=True)
    except Exception:
        return None

    if answer.status_code != 200:
        return None

    try:
        return answer.json()
    except ValueError:
        return None


def traded(where, asked, known):
    """SWAP A CODE OR A REFRESH TOKEN FOR A LIVE ONE."""
    asked = {**asked, "client_id": known["client_id"]}

    if known.get("client_secret"):
        asked["client_secret"] = known["client_secret"]

    return dated(
        answered(
            httpx.post(
                where,
                data=asked,
                timeout=PATIENCE,
                headers={"Accept": "application/json"},
            )
        )
    )


def answered(answer):
    """THE JSON, OR THE SERVICE'S OWN COMPLAINT AS SOMETHING A PERSON CAN READ."""
    if answer.status_code not in (200, 201):
        raise PermissionError(complaint(answer))

    return answer.json()


def complaint(answer):
    try:
        said = answer.json()
    except ValueError:
        return f"{answer.status_code}: {answer.text[:120]}"

    return said.get("error_description") or said.get("error") or str(said)[:120]


def dated(held):
    """WHEN IT DIES, WORKED OUT NOW. expires_in IS ONLY TRUE THE SECOND IT ARRIVES."""
    seconds = held.pop("expires_in", None)

    if seconds:
        held["expires_at"] = time.time() + float(seconds)

    return held


def dying(held):
    ends = held.get("expires_at")

    return bool(ends) and time.time() + EARLY >= float(ends)


def bearer(name):
    """A LIVING ACCESS TOKEN FOR THIS SERVICE, RENEWED IF IT IS ABOUT TO DIE."""
    held = tokens.kept(name).get("tokens") or {}

    if not held.get("access_token") or not dying(held):
        return held.get("access_token")

    if not held.get("refresh_token"):
        return held["access_token"]  # LET THE SERVER BE THE ONE THAT SAYS NO.

    return renewed(name, held).get("access_token")


def renewed(name, held):
    """A NEW ACCESS TOKEN OUT OF THE REFRESH ONE. THE OLD ONE IF THAT FAILS.

    THE OLD ONE, BECAUSE THE SERVER REFUSING IS A SENTENCE THE PANEL CAN SHOW,
    AND A CALL THAT WENT OUT WITH NO HEADER AT ALL IS ONE NOBODY CAN EXPLAIN.
    """
    from mcps import signing

    where = (tokens.kept(name).get("auth") or {}).get("token_endpoint")
    known = signing.client(name)

    if not where or not known.get("client_id"):
        return held

    try:
        got = traded(
            where,
            {"grant_type": "refresh_token", "refresh_token": held["refresh_token"]},
            known,
        )
    except Exception:
        return held

    # A REFRESH USUALLY ANSWERS WITHOUT A REFRESH TOKEN AND MEANS KEEP THE ONE YOU
    # HAVE, SO THE OLD SIGN IN IS UPDATED RATHER THAN REPLACED.
    fresh = {**held, **got}

    if "expires_at" not in got:
        fresh.pop("expires_at", None)

    tokens.put(name, tokens=fresh)

    return fresh


class Proving(httpx.Auth):
    """THE BEARER HEADER, PUT ON EVERY REQUEST AND ALWAYS A LIVE ONE.

    LOOKED UP PER REQUEST RATHER THAN HELD, SO A TOKEN RENEWED FOR ONE SERVICE
    IS THE ONE ITS RELATIVES USE ON THEIR VERY NEXT CALL.
    """

    def __init__(self, name):
        self.name = name

    def auth_flow(self, request):
        yield carrying(request, bearer(self.name))

    async def async_auth_flow(self, request):
        # RENEWING IS AN ORDINARY BLOCKING REQUEST, AND THE LOOP IT WOULD BLOCK IS
        # THE ONE EVERY OTHER CONNECTION IS WAITING ON.
        yield carrying(request, await asyncio.to_thread(bearer, self.name))


def carrying(request, token):
    if token:
        request.headers["Authorization"] = f"Bearer {token}"

    return request
