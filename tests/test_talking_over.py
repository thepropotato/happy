"""What Happy does with words said over him: carry on, hold, stop keeping the rest, or take a new request."""

import asyncio
import time
import types

from happy import app


class Voice:
    def __init__(self, unheard=("The rest of it.", "And more.")):
        self.unheard = list(unheard)
        self.held = False
        self.speaking = True
        self.recent = []

    def pause(self):
        self.held = True

    def paused(self):
        return self.held

    def resume(self):
        self.held = False

    def stop(self):
        unheard, self.unheard = self.unheard, []
        return unheard


class Face:
    def __init__(self):
        self.states, self.unsaid_from = [], []

    def state(self, name):
        self.states.append(name)

    def unsaid(self, sentence):
        self.unsaid_from.append(sentence)


def happy(**voice):
    cfg = types.SimpleNamespace(get=lambda key, default=None: default)
    one = app.Happy(cfg, Face())
    one.speaker = Voice(**voice)
    one.listener = types.SimpleNamespace(holding=False)
    one.begun = []
    one.begin = lambda text, how, shown=None: one.begun.append((text, how))
    one.said_for = None
    return one


def run(test):
    async def inside():
        test(asyncio.get_running_loop())

    asyncio.run(inside())


def test_a_nod_carries_him_on():
    def test(loop):
        one = happy()
        one.loop = loop
        one.barged()
        one.cut_in("Yeah, okay.")
        assert not one.speaker.held and one.face.states[-1] == "speaking" and one.leftover == ([], 0.0)

    run(test)


def test_wait_holds_him_until_go_on():
    def test(loop):
        one = happy()
        one.loop = loop
        one.barged()
        one.cut_in("Hold on.")
        assert one.speaker.held and one.listener.holding and one.hold_timer
        one.cut_in("Okay, go on.")
        assert not one.speaker.held and not one.listener.holding and one.hold_timer is None

    run(test)


def test_stop_keeps_what_was_not_heard_and_fades_it():
    def test(loop):
        one = happy()
        one.loop = loop
        one.barged()
        one.cut_in("Stop.")
        assert one.leftover[0] == ["The rest of it.", "And more."] and one.face.unsaid_from == ["The rest of it."]
        assert not one.begun

    run(test)


def test_a_question_cuts_him_off_and_is_asked():
    def test(loop):
        one = happy()
        one.loop = loop
        one.barged()
        one.cut_in("What does crore mean?")
        assert one.begun == [("What does crore mean?", "barge")] and one.leftover[0]

    run(test)


def test_go_on_hands_back_the_rest_once():
    one = happy()
    one.leftover = (["The rest of it."], time.monotonic())
    assert one.picked_up("what time is it") == []
    assert one.picked_up("Okay, go on.") == ["The rest of it."]
    assert one.picked_up("go on") == []


def test_the_model_hears_about_the_rest_once_and_not_after_a_while():
    one = happy()
    one.leftover = (["The rest of it."], time.monotonic())
    assert '"The rest of it."' in one.leftover_note() and one.leftover_note() == ""
    one.leftover = (["The rest of it."], time.monotonic() - app.LEFTOVER_SECONDS - 1)
    assert one.leftover_note() == "" and one.picked_up("go on") == []
