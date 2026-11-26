"""Each way a brain says no is told in plain words with the one thing that fixes it, the same for every provider."""

from happy.agent.health import explain

OPENAI = "https://api.openai.com/v1"
OPENROUTER = "https://openrouter.ai/api/v1"


def test_claude_signed_out_offers_a_sign_in():
    told = explain("Not logged in · Please run /login")
    assert told.state == "signed_out"
    assert told.action["do"] == "claude_login"


def test_claude_out_of_credits_and_at_its_limit_are_told_apart():
    assert explain("Credit balance is too low").state == "no_credits"
    limit = explain("Claude AI usage limit reached|1795700000")
    assert limit.state == "limit"
    assert "resets" in limit.text


def test_a_rejected_key_points_to_that_service_s_keys():
    told = explain("401 Incorrect API key provided: sk-abc. You can find your API key at ...", "openai", OPENAI)
    assert told.state == "bad_key"
    assert told.text.startswith("OpenAI")
    assert told.action["url"] == "https://platform.openai.com/api-keys"


def test_an_empty_account_points_to_that_service_s_billing():
    told = explain("429 You exceeded your current quota, please check your plan and billing details. insufficient_quota", "openai", OPENAI)
    assert told.state == "no_credits"
    assert told.action["url"].startswith("https://platform.openai.com/")
    assert explain("402 Insufficient credits", "openai", OPENROUTER).text.startswith("OpenRouter is out of credits")


def test_a_rate_limit_is_not_mistaken_for_no_credits():
    assert explain("429 Rate limit reached for requests", "openai", OPENAI).state == "limit"


def test_a_missing_model_asks_for_another():
    assert explain("404 The model `gpt-9` does not exist", "openai", OPENAI).state == "no_model"


def test_a_local_server_that_is_off_says_which_app_to_open():
    told = explain("connection failed: [Errno 61] Connection refused", "openai", "http://localhost:11434/v1")
    assert told.state == "unreachable"
    assert "Ollama" in told.text
    assert "LM Studio" in explain("Connection error.", "openai", "http://127.0.0.1:1234/v1").text


def test_anything_else_still_names_the_brain_and_keeps_the_reason():
    told = explain("something odd happened", "openai", OPENAI)
    assert told.state == "failed"
    assert told.text.startswith("OpenAI didn't answer: something odd happened")
