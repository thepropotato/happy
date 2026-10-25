from happy.agent.deeds import unbacked


def test_a_save_no_tool_made_is_caught():
    reply = "The PDF is a test page. The file has been saved as “Summary.txt” on your desktop."
    assert unbacked(reply, {"read_tab"}) == "The file has been saved as “Summary.txt” on your desktop."


def test_a_save_write_file_made_passes():
    assert unbacked("I’ve saved it to your desktop.", {"read_tab", "write_file"}) is None


def test_someone_else_sending_is_not_a_claim():
    assert unbacked("John Doe sent you a photo yesterday.", {"whatsapp_read"}) is None


def test_a_bare_deed_opening_a_sentence_is_a_claim():
    assert unbacked("Sent. Anything else?", set()) == "Sent."


def test_a_connected_service_can_back_any_deed():
    assert unbacked("I've sent the email.", {"gmail__send_message"}) is None


class Stream:
    def __init__(self, parts):
        self.parts = parts

    def __aiter__(self):
        return self.chunks()

    async def chunks(self):
        from types import SimpleNamespace as N

        for text, call in self.parts:
            calls = [N(index=0, id="c1", function=N(name=call[0], arguments=call[1]))] if call else None
            yield N(choices=[N(delta=N(content=text, tool_calls=calls))])

    async def close(self):
        pass


def test_an_unbacked_claim_is_never_said_and_goes_back_to_the_model(monkeypatch):
    import asyncio

    from happy.agent import Text
    from happy.agent import openai_compatible
    from happy.config import Config

    openai_compatible.tools.load()
    rounds = iter([
        [("It is a test page. ", None), ("The file has been saved on your desktop.", None)],
        [("", ("write_file", '{"name": "summary.txt", "text": "A test page."}'))],
        [("I saved summary.txt on your desktop.", None)],
    ])
    sent = []

    async def create(**kwargs):
        sent.append(kwargs["messages"][-1])
        return Stream(next(rounds))

    async def fake(name, args):
        return "Wrote /Users/johndoe/Desktop/summary.txt and opened it."

    backend = openai_compatible.OpenAICompatible(Config(), "http://localhost:1/v1", "test")
    backend.system, backend.schemas = {"role": "system", "content": ""}, []
    backend.client.chat.completions.create = create
    monkeypatch.setattr(openai_compatible.tools, "call", fake)
    said = []
    asyncio.run(backend.turn("summarise this and save it", lambda e: said.append(e.delta) if isinstance(e, Text) else None))
    assert "".join(said) == "It is a test page. I saved summary.txt on your desktop."
    assert "no tool did that" in sent[1]["content"]
