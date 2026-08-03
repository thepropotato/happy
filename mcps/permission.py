"""SENDING SOMEBODY TO A SERVICE TO SIGN IN, AND CATCHING THEM ON THE WAY BACK.

THE SERVICE SENDS THE PERSON BACK TO AN ADDRESS, SO THERE HAS TO BE SOMETHING
LISTENING ON THIS MACHINE TO BE SENT BACK TO. IT IS BOUND BEFORE ANYTHING ELSE
HAPPENS, BECAUSE THE PORT IT LANDS ON IS PART OF WHAT THE SERVICE IS TOLD.

NOTHING IN HERE IS EVER REACHED BY A TOOL. THE MODEL MUST NOT BE ABLE TO MAKE A
BROWSER WINDOW APPEAR, SO SIGNING IN IS ALWAYS SOMETHING A PERSON STARTED.
"""

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

DONE = b"<html><body style='font:16px system-ui;padding:3rem'>Signed in. You can close this tab and go back to Happy.</body></html>"

WRONG = b"<html><body style='font:16px system-ui;padding:3rem'>That did not carry a code. Try connecting again from the panel.</body></html>"


class Landing(BaseHTTPRequestHandler):
    """WHERE THE SERVICE SENDS THE PERSON BACK TO. IT ANSWERS EXACTLY ONCE."""

    def do_GET(self):
        found = parse_qs(urlparse(self.path).query)
        code = (found.get("code") or [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(DONE if code else WRONG)

        self.server.caught = (code, (found.get("state") or [None])[0])
        self.server.landed.set()

    def log_message(self, *ignored):
        """THE TERMINAL BELONGS TO HAPPY, NOT TO A ONE SHOT WEB SERVER."""


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
        """THE CODE THE SERVICE SENT BACK, ONCE SOMEBODY HAS SAID YES.

        THE THREAD THAT ASKED FOR IT WAITS HERE, WHICH IS THE PANEL'S OWN AND
        NOT THE ONE ANYBODY IS TALKING TO.
        """
        try:
            self.server.landed.wait(WAITING_SECONDS)
        finally:
            self.close()

        code, state = self.server.caught

        if not code:
            raise PermissionError("Nobody finished signing in.")

        return code, state

    def close(self):
        try:
            self.server.shutdown()
            self.server.server_close()
        except Exception:
            pass
