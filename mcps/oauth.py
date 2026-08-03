"""THE BROWSER SIGN IN: A CONSENT SCREEN, SOMEBODY SAYING YES, AND A TOKEN BACK.

THERE IS NOTHING TO DISCOVER HERE ANY MORE. THE SERVERS ARE OURS AND THE ONE
SERVICE THAT NEEDS A CONSENT SCREEN IS NAMED IN mcps/registry.py ALONG WITH THE
TWO ADDRESSES ITS SIGN IN USES, SO A CONNECTION IS ONE ROUND TRIP RATHER THAN
FOUR WELL KNOWN DOCUMENTS AND A GUESS.

KEEPING THE TOKEN ALIVE AFTERWARDS IS NOT HERE EITHER. THE SERVER HOLDS THE
CREDENTIALS AND REFRESHES THEM ITSELF THE MOMENT IT NEEDS TO, WHICH IS WHY THIS
FILE ENDS THE INSTANT THE FIRST TOKEN IS WRITTEN DOWN.

NOTHING IN HERE IS EVER REACHED BY A TOOL. A BROWSER WINDOW THAT APPEARS BECAUSE
THE MODEL WANTED IT TO IS NOT AN ANSWER TO ANYTHING SOMEBODY ASKED OUT LOUD.
"""

import base64
import hashlib
import secrets
import time
from urllib.parse import urlencode

import httpx

from mcps import registry, tokens

PATIENCE = 30

# WITHOUT THESE, GOOGLE WITHHOLDS THE REFRESH TOKEN AND THE SIGN IN DIES IN AN HOUR.
LASTING = {"access_type": "offline", "prompt": "consent"}

BRING_ONE = "{label} needs an app of your own. Add its client ID and secret first."

WRONG_WAY = "That sign in came back wrong. Try connecting again."


def sign_in(name, doorway):
    """THE WHOLE SIGN IN. BLOCKS THE THREAD THAT ASKED FOR IT, WHICH IS THE PANEL'S
    OWN AND NOT THE ONE ANYBODY IS TALKING TO."""
    known = registry.find(name)
    client = tokens.client(name)

    if not client.get("client_id"):
        raise PermissionError(BRING_ONE.format(label=known["label"]))

    verifier = secrets.token_urlsafe(96)
    state = secrets.token_urlsafe(32)

    doorway.show(f"{known['authorize']}?{urlencode(asking(known, client, doorway, verifier, state))}")

    code, back = doorway.waited()

    if back != state:
        raise PermissionError(WRONG_WAY)

    held = traded(
        known["token"],
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": doorway.address,
            "code_verifier": verifier,
        },
        client,
    )

    tokens.put(name, tokens=held)

    return held


def asking(known, client, doorway, verifier, state):
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .decode()
        .rstrip("=")
    )

    return {
        "response_type": "code",
        "client_id": client["client_id"],
        "redirect_uri": doorway.address,
        "state": state,
        "scope": " ".join(known.get("scopes") or []),
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        **LASTING,
    }


def traded(where, asked, client):
    """SWAP THE CODE FOR A TOKEN, AND WORK OUT WHEN THAT TOKEN DIES."""
    asked = {**asked, "client_id": client["client_id"]}

    if client.get("client_secret"):
        asked["client_secret"] = client["client_secret"]

    answer = httpx.post(
        where, data=asked, timeout=PATIENCE, headers={"Accept": "application/json"}
    )

    if answer.status_code not in (200, 201):
        raise PermissionError(complaint(answer))

    return dated(answer.json())


def complaint(answer):
    try:
        said = answer.json()
    except ValueError:
        return f"{answer.status_code}: {answer.text[:120]}"

    return said.get("error_description") or said.get("error") or str(said)[:120]


def dated(held):
    """expires_in IS ONLY TRUE THE SECOND IT ARRIVES, SO IT IS TURNED INTO A TIME."""
    seconds = held.pop("expires_in", None)

    if seconds:
        held["expires_at"] = time.time() + float(seconds)

    return held
