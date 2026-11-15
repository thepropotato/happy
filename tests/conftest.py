import pytest


@pytest.fixture(autouse=True)
def throwaway_history(tmp_path, monkeypatch):
    """Every test gets its own history file, so nothing reaches the person's real one."""
    from happy import history

    monkeypatch.setattr(history, "FILE", tmp_path / "history.db")
