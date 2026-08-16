"""SENDING SOMEBODY TO A SERVICE TO SIGN IN, AND CATCHING THEM ON THE WAY BACK."""

import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

HERE = "127.0.0.1"

PATH = "/callback"

# THE ONLY PORT: IT IS REGISTERED WITH GOOGLE AND SLACK BY HAND, AND A DIFFERENT
# NUMBER IS A SIGN IN THAT GETS TURNED AWAY.
PREFERRED = 8765

BUSY = (
    f"Something else on this computer is using port {PREFERRED}, which is where "
    "signing in has to come back to. Close it and try again."
)

WAITING_SECONDS = 300

NOBODY = "Nobody finished signing in."

# A SERVICE THAT TURNS SOMEBODY AWAY SENDS THEM BACK HERE WITH A REASON AND NO CODE, AND THE
# REASON IS THE ONLY THING THAT TELLS A REFUSAL APART FROM A TAB SOMEBODY WALKED AWAY FROM.
SAID = "That sign in came back refused: {trouble}. Try connecting again."

REFUSED = {
    "access_denied": "That sign in was refused. Either the consent screen was cancelled, or "
    "the app is still in testing and this account is not on its list of test users.",
    "admin_policy_enforced": "The Google account's administrator does not allow this app.",
    "org_internal": "That app only admits accounts inside the organisation that owns it.",
    "invalid_scope": "The app is asking for something it has not been allowed to ask for.",
}

# THE SAME PAGE THE WHATSAPP SCAN ENDS ON, SO EVERY SERVICE FINISHES THE SAME WAY.
LANDED_PAGE = """<!doctype html><meta charset="utf-8"><title>Signing in to Happy</title>
<style>
body{font:16px system-ui;background:#111;color:#eee;display:flex;min-height:100vh;margin:0;
align-items:center;justify-content:center}
main{text-align:center;padding:2rem}
p{color:#9a9a9a;max-width:34rem;line-height:1.5}
</style><main>%s</main>"""

DONE = (
    LANDED_PAGE
    % "<h2>You are signed in</h2><p>You can close this tab and go back to Happy.</p>"
).encode()

WRONG = (
    LANDED_PAGE
    % "<h2>That sign in came back empty</h2><p>It did not carry a code. Try connecting again from the panel.</p>"
).encode()


class Landing(BaseHTTPRequestHandler):
    """WHERE THE SERVICE SENDS THE PERSON BACK TO. IT ANSWERS EXACTLY ONCE."""

    def do_GET(self):
        where = urlparse(self.path)

        # A BROWSER ASKS FOR A FAVICON AS SOON AS IT DRAWS A PAGE, AND ANYTHING
        # ANSWERED HERE THAT IS NOT THE WAY BACK ENDS THE SIGN IN CARRYING NO CODE.
        if where.path != PATH:
            self.send_response(404)
            self.end_headers()

            return

        found = parse_qs(where.query)
        code = (found.get("code") or [None])[0]
        trouble = (found.get("error") or [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(DONE if code else WRONG)

        # THE FIRST TRIP BACK IS THE ONE THAT COUNTS, SO A RELOAD OF THIS PAGE CANNOT
        # WIPE THE CODE THE FIRST ONE BROUGHT.
        if self.server.landed.is_set():
            return

        self.server.caught = (code, (found.get("state") or [None])[0])
        self.server.trouble = trouble
        self.server.landed.set()

    def log_message(self, *ignored):
        """THE TERMINAL BELONGS TO HAPPY, NOT TO A ONE SHOT WEB SERVER."""


def refusal(trouble):
    """WHY THE TRIP BACK CARRIED NO CODE, IN WORDS RATHER THAN IN A SERVICE'S SHORTHAND."""
    if not trouble:
        return NOBODY

    return REFUSED.get(trouble) or SAID.format(trouble=trouble)


def bound():
    """THE ONE PORT A SERVICE IS ALLOWED TO SEND SOMEBODY BACK TO."""
    try:
        return HTTPServer((HERE, PREFERRED), Landing)
    except OSError:
        raise PermissionError(BUSY) from None


def expected():
    """THE ADDRESS TO REGISTER WITH A SERVICE THAT WANTS ONE IN ADVANCE."""
    return f"http://{HERE}:{PREFERRED}{PATH}"


class Doorway:
    """THE LOOPBACK ADDRESS A SERVICE IS ALLOWED TO SEND SOMEBODY BACK TO."""

    def __init__(self):
        # BOUND FIRST, BECAUSE THE PORT IT LANDS ON IS PART OF THE ADDRESS THE
        # SERVICE IS TOLD TO SEND SOMEBODY BACK TO.
        self.server = bound()
        self.server.caught = (None, None)
        self.server.trouble = None
        self.server.landed = threading.Event()

        self.port = self.server.server_address[1]
        self.serving = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.serving.start()

    @property
    def address(self):
        return f"http://{HERE}:{self.port}{PATH}"

    def show(self, where):
        """SHOW THE PERSON THE SIGN IN PAGE, OR TELL THEM WHERE IT IS."""
        if not webbrowser.open(where):
            print(f"\n  Open this to sign in:\n    {where}\n")

    def waited(self):
        """THE CODE THE SERVICE SENT BACK, ONCE SOMEBODY HAS SAID YES."""
        try:
            self.server.landed.wait(WAITING_SECONDS)
        finally:
            self.close()

        code, state = self.server.caught

        if not code:
            raise PermissionError(refusal(self.server.trouble))

        return code, state

    def close(self):
        try:
            self.server.shutdown()
            self.server.server_close()
        except Exception:
            pass
