"""A model that collapses into dots and question marks is cut off, and only what it said in words is kept."""

from happy.agent.openai_compatible import babbling, sense

COLLAPSE = "It has had messages recently.?\n\n(Note … ? … … … ? … ? ? ? ?? … .. .. ……………… … … ……………… … ………"


def test_a_collapse_into_punctuation_is_noticed():
    assert babbling(COLLAPSE)


def test_a_table_rule_or_an_ellipsis_is_not_a_collapse():
    assert not babbling("| --- | --- | --- | --- | --- | --- | --- |")
    assert not babbling("Well... I think so.")


def test_only_the_words_before_it_are_kept():
    assert sense(COLLAPSE) == "It has had messages recently.?"
    assert sense('He said "hi." ……') == 'He said "hi."'
    assert sense("…… ? ……") == ""
