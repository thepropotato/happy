"""A way of talking typed or pasted: kept as typed when short, learned into short notes when long, never the paste itself."""

import time

import pytest

from happy import persona


class Settings:
    def get(self, key, default=None):
        return default

    def set(self, key, value):
        pass

    def save(self):
        pass


@pytest.fixture
def asked(tmp_path, monkeypatch):
    monkeypatch.setattr(persona, "FILE", tmp_path / "persona.md")
    monkeypatch.setattr(persona, "Config", Settings)
    seen = []

    async def complete(cfg, prompt):
        seen.append(prompt)
        return "Formal and grand. Calls them my lord.\n1. It is done, my lord."

    monkeypatch.setattr(persona, "complete", complete)
    return seen


def test_a_typed_style_is_kept_as_it_is(asked):
    assert persona.adopt("Talk like a knight from Game of Thrones.") == "Talk like a knight from Game of Thrones."
    assert asked == []


def test_a_huge_paste_is_learned_from_a_sample_and_never_kept(asked):
    paste = "\n".join(f"Line {n}: winter is coming, my lord, and the north remembers." for n in range(200_000))
    assert len(paste) > 10_000_000
    started = time.monotonic()
    kept = persona.adopt(paste)
    assert time.monotonic() - started < 10
    assert kept.startswith("Formal and grand.")
    assert len(asked) == 1 and len(asked[0]) < persona.SAMPLE_CHARACTERS + 2000


def test_prose_with_no_line_breaks_is_sampled_by_sentence(asked):
    persona.adopt("I will not yield. " * 5000)
    assert asked[0].count("I will not yield.") > 100


def test_with_no_model_a_few_of_its_own_lines_stand_in(asked, monkeypatch):
    async def down(cfg, prompt):
        raise ConnectionError("no model")

    monkeypatch.setattr(persona, "complete", down)
    kept = persona.adopt("\n".join(f"Hold the door, number {n}." for n in range(5000)))
    assert kept.startswith("Talk the way these lines do:")
    assert len(kept) <= persona.LONGEST


def test_empty_goes_back_to_happys_own_way(asked):
    persona.adopt("Talk like a pirate.")
    persona.adopt("")
    assert persona.read() == ""


@pytest.mark.parametrize("said", ["", "normal", "normally", "Talk normally.", "your usual way", "default"])
def test_going_back_to_normal_clears_it_however_the_model_says_it(asked, said):
    from happy.tools.notes import personality

    persona.adopt("Talk like a pirate.")
    personality(said)
    assert persona.read() == ""


def test_a_style_by_voice_is_kept_as_a_sentence(asked):
    from happy.tools.notes import personality

    personality("like a knight from Game of Thrones")
    assert persona.read() == "Talk like a knight from Game of Thrones."
