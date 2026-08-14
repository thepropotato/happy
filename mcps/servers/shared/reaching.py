"""A SERVICE'S HTTP API, ASKED THE SAME WAY BY EVERY SERVER THAT HAS ONE."""

import httpx

PATIENCE = 30

MOST_COMPLAINT = 200


class Service:
    """ONE SERVICE'S API, WITH ITS SIGN IN ALREADY ON EVERY REQUEST."""

    def __init__(self, base, headers, name):
        self.base = base.rstrip("/")
        self.headers = headers
        self.name = name

    def get(self, path, params=None):
        return self.sent("GET", path, params=params)

    def post(self, path, body=None, params=None):
        return self.sent("POST", path, json=body, params=params)

    def patch(self, path, body=None):
        return self.sent("PATCH", path, json=body)

    def sent(self, way, path, **asked):
        answer = httpx.request(
            way,
            f"{self.base}/{path.lstrip('/')}",
            headers=self.headers,
            timeout=PATIENCE,
            follow_redirects=True,
            **asked,
        )

        if answer.status_code >= 400:
            raise PermissionError(f"{self.name} said no. {complaint(answer)}")

        return answer.json() if answer.text else {}


def complaint(answer):
    """THE SERVICE'S OWN REASON, HOWEVER IT HAPPENS TO WORD IT."""
    try:
        said = answer.json()
    except ValueError:
        return f"{answer.status_code}: {answer.text[:MOST_COMPLAINT]}"

    if not isinstance(said, dict):
        return str(said)[:MOST_COMPLAINT]

    found = (
        said.get("message")
        or said.get("error_description")
        or said.get("error")
        or said.get("detail")
    )

    return str(found or said)[:MOST_COMPLAINT]
