"""Sharing is off until switched on, and a shared turn carries counts, never what anyone said or which file or person was involved."""

import json
import types

from happy import config, usage

SECRET = "tell Mom the code is 4417 and send resume.pdf"
STEPS = [
    {"tool": "whatsapp_send", "label": "Message to Mom", "args": {"to": "Mom", "text": SECRET}, "result": "Sent to Mom", "ok": True},
    {"tool": "Gmail__search_threads", "label": "Searching Gmail", "args": {"query": "bank"}, "result": "2 threads", "ok": False},
]


def sharing(on):
    return types.SimpleNamespace(get=lambda key, default=None: on if key == "share_usage" else default)


def caught(monkeypatch, tmp_path):
    sent = []
    monkeypatch.setattr(usage, "LAST", tmp_path / "last.json")
    monkeypatch.setattr(usage, "ID", tmp_path / "id")
    monkeypatch.setattr(usage, "send", sent.append)
    monkeypatch.setattr(usage.threading, "Thread", lambda target, args, **_: types.SimpleNamespace(start=lambda: target(*args)))
    return sent


def test_sharing_is_off_unless_switched_on(monkeypatch, tmp_path):
    sent = caught(monkeypatch, tmp_path)
    assert config.DEFAULTS["share_usage"] is False
    usage.turn(sharing(False), how="key", path="model", steps=STEPS, seconds=3.2, failed=False, silent=False, model="gpt-oss:20b")
    assert sent == [] and not (tmp_path / "last.json").exists()


def test_a_shared_turn_holds_no_words_args_or_names(monkeypatch, tmp_path):
    sent = caught(monkeypatch, tmp_path)
    usage.turn(sharing(True), how="wake", path="model", steps=STEPS, seconds=3.24, failed=False, silent=True, model="gpt-oss:20b")
    body = sent[0]
    props = body["properties"]
    assert props["tools"] == ["whatsapp_send", "mcp"]
    assert (props["tool_count"], props["tools_failed"], props["seconds"], props["silent"]) == (2, 1, 3.2, True)
    assert props["$process_person_profile"] is False
    flat = json.dumps(body)
    for leak in ("Mom", "4417", "resume", "bank", "Gmail", "Sent to"):
        assert leak not in flat
    assert json.loads((tmp_path / "last.json").read_text()) == props


def test_the_id_is_random_and_kept(monkeypatch, tmp_path):
    caught(monkeypatch, tmp_path)
    first = usage.install_id()
    assert len(first) == 32 and usage.install_id() == first
