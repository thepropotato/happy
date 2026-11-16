"""A slow tool is first named as it is ("Checking the latest email."), and only after that heard as "Still …"."""

import asyncio
import types

from happy import app


class Voice:
    def __init__(self):
        self.said = []

    def idle(self):
        return True

    def say(self, text):
        self.said.append(text)
        return True


def happy():
    one = app.Happy(types.SimpleNamespace(get=lambda key, default=None: default), types.SimpleNamespace())
    one.speaker = Voice()
    one.said_for = None
    one.narrated = set()
    one.saying, one.activity = "Checking the latest email.", "Checking email"
    return one


def silence(one, started, seconds):
    async def inside():
        task = asyncio.create_task(one.keep_talking(started))
        await asyncio.sleep(seconds)
        task.cancel()

    asyncio.run(inside())


def test_the_first_line_in_a_long_silence_has_no_still(monkeypatch):
    monkeypatch.setattr(app, "STILL_EVERY", 0.0)
    one = happy()
    silence(one, 0.0, 1.0)
    assert one.speaker.said == ["Checking the latest email.", "Still checking the latest email."]


def test_still_follows_a_line_already_heard(monkeypatch):
    monkeypatch.setattr(app, "STILL_EVERY", 0.0)
    one = happy()
    one.narrate("Checking the latest email.")
    silence(one, 0.0, 0.6)
    assert one.speaker.said == ["Checking the latest email.", "Still checking the latest email."]
