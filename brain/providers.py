"""THE BACKENDS THAT DO THE INFERENCE, AND NOTHING ELSE ABOUT THEM.

TWO THINGS ACTUALLY DIFFER BETWEEN THEM: WHERE THE CONTEXT LENGTH GOES, AND WHAT
THE THINKING KNOB IS CALLED. A BACKEND THAT CANNOT TAKE ONE SAYS SO PLAINLY
RATHER THAN ACCEPTING IT AND DROPPING IT.

THE CLIENT PACKAGES ARE IMPORTED WHEN A BACKEND IS BUILT, SO ONLY THE PROVIDER
YOU USE HAS TO BE INSTALLED. TO ADD ONE: WRITE THE BUILDER, PUT IT IN PROVIDERS.
"""

import importlib
import json
import urllib.request

OLLAMA = "ollama"
OPENAI = "openai"

# THE OPENAI SHAPE POINTS AT THE SAME LOCAL SERVER: IT IS THE FALLBACK FOR
# LM STUDIO, VLLM AND LLAMA.CPP TOO.
URLS = {
    OLLAMA: "http://localhost:11434",
    OPENAI: "http://localhost:11434/v1",
}

# OLLAMA STARTS AT 4096 AND TRUNCATES IN SILENCE. THE OPENAI REQUEST HAS NO FIELD.
SETS_CONTEXT = {OLLAMA: True, OPENAI: False}

# PATH, THE FIELD HOLDING THE LIST, AND WHAT A MODEL'S NAME IS CALLED IN IT.
LISTING = {
    OLLAMA: ("/api/tags", "models", "name"),
    OPENAI: ("/models", "data", "id"),
}

LISTING_TIMEOUT = 2

INSTALL = {
    OLLAMA: "ollama pull {model}",
    OPENAI: "load {model} in whatever is serving {url}",
}

UNKNOWN = "THERE IS NO PROVIDER CALLED {name}. THERE IS: {known}."
MISSING = "THE {name} PROVIDER NEEDS {package}. INSTALL IT WITH:\n  pip install {package}"

NO_CONTEXT = (
    "{name} cannot be told a context length per request, so {model} will use "
    "whatever the server was started with. Start it with the window you want."
)


class ProviderError(Exception):
    pass


def ollama(model, url, key, temperature, context, effort, timeout):
    """OLLAMA'S OWN /api/chat. IT TAKES num_ctx PER REQUEST, WHICH IS THE WHOLE
    REASON IT IS THE DEFAULT. key IS UNUSED, THE SIGNATURE IS SHARED."""
    chat = client("langchain_ollama", "ChatOllama", OLLAMA)

    return chat(
        base_url=url,
        model=model,
        temperature=temperature,
        num_ctx=context,
        reasoning=effort,  # SENT AS think.
        client_kwargs={"timeout": timeout},
    )


def openai(model, url, key, temperature, context, effort, timeout):
    """THE OPENAI REQUEST SHAPE, WHICH IS ALSO LM STUDIO'S AND VLLM'S.

    context IS ACCEPTED AND CANNOT BE SENT. SEE SETS_CONTEXT ABOVE.
    """
    chat = client("langchain_openai", "ChatOpenAI", OPENAI)

    return chat(
        base_url=url,
        model=model,
        api_key=key,
        temperature=temperature,
        timeout=timeout,
        **({"reasoning_effort": effort} if effort else {}),
    )


PROVIDERS = {OLLAMA: ollama, OPENAI: openai}


def client(package, name, provider):
    """THE CHAT CLASS OUT OF A CLIENT PACKAGE, OR A COMPLAINT NAMING THE INSTALL."""
    try:
        module = importlib.import_module(package)
    except ImportError:
        raise ProviderError(MISSING.format(name=provider, package=package.replace("_", "-")))

    return getattr(module, name)


def build(name, model, url=None, key=None, temperature=None, context=None, effort=None, timeout=None):
    """THE MODEL FROM WHICHEVER BACKEND WAS ASKED FOR, READY TO BE HANDED TOOLS."""
    if name not in PROVIDERS:
        raise ProviderError(UNKNOWN.format(name=name, known=", ".join(names())))

    return PROVIDERS[name](model, address(name, url), key, temperature, context, effort, timeout)


def address(name, url=None):
    """WHAT WAS ASKED FOR, OR THE PROVIDER'S OWN DEFAULT."""
    return url or URLS.get(name)


def sets_context(name):
    return SETS_CONTEXT.get(name, False)


def offered(name, url=None):
    """EVERY MODEL THIS BACKEND ALREADY HAS, OR NOTHING IF IT WILL NOT SAY."""
    where = LISTING.get(name)

    if not where:
        return []

    path, holds, called = where

    try:
        with urllib.request.urlopen(address(name, url) + path, timeout=LISTING_TIMEOUT) as answer:
            found = json.load(answer)
    except Exception:
        return []

    return sorted(each.get(called) for each in found.get(holds, []) if each.get(called))


def install(name, model, url=None):
    """HOW TO GET A MODEL THIS BACKEND DOES NOT HAVE."""
    return INSTALL.get(name, "").format(model=model, url=address(name, url))


def caveat(name, model):
    """WHAT THIS BACKEND CANNOT DO, IN ONE SENTENCE, OR None."""
    if sets_context(name):
        return None

    return NO_CONTEXT.format(name=name, model=model)


def names():
    return sorted(PROVIDERS)


if __name__ == "__main__":
    for each in names():
        print(f"{each:8} {address(each):32} context per request: {sets_context(each)}")
