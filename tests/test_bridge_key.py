import os
import sys

import pytest

from happy import paths
from happy.integrations import whatsapp
from whatsapp_server import key as bridge_key


def test_the_key_is_made_once_and_kept_with_the_secrets(monkeypatch):
    made = whatsapp.key()
    assert len(made) >= 40
    assert whatsapp.key() == made
    assert whatsapp.headers() == {"X-Bridge-Key": made}
    monkeypatch.setenv("HAPPY_SECRETS", str(paths.SECRETS))
    assert bridge_key.read() == made


def test_the_environment_names_the_secrets_but_never_holds_the_key():
    env = whatsapp.environment()
    assert env["HAPPY_SECRETS"] == str(paths.SECRETS)
    assert whatsapp.key() not in env.values()


def test_no_secrets_file_reads_as_no_key(monkeypatch, tmp_path):
    monkeypatch.setenv("HAPPY_SECRETS", str(tmp_path / "missing.toml"))
    assert bridge_key.read() == ""


@pytest.mark.skipif(sys.platform == "win32", reason="Windows folders are private to the account already")
def test_happys_folder_is_readable_by_its_owner_alone(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir(mode=0o755)
    monkeypatch.setattr(paths, "HOME", home)
    paths.keep_private()
    assert os.stat(home).st_mode & 0o777 == 0o700
