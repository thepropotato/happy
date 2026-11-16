import pytest


@pytest.fixture(autouse=True)
def throwaway_history(tmp_path, monkeypatch):
    """Every test gets its own history and secrets files, so nothing reaches the person's real ones."""
    from happy import history, paths

    monkeypatch.setattr(history, "FILE", tmp_path / "history.db")
    monkeypatch.setattr(paths, "SECRETS", tmp_path / "secrets.toml")
