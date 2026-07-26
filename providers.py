"""
THE BACKENDS THAT DO THE INFERENCE, AND NOTHING ELSE ABOUT THEM.

THE FLOW BELONGS TO LANGGRAPH, THE TOOLS BELONG TO agents/, THE PROMPT BELONGS
TO llm.py. A PROVIDER IS ASKED A QUESTION AND ANSWERS IT, AND THAT IS THE WHOLE
JOB. SO WHICH ONE ANSWERS HAS TO STAY A NAME IN A DICT RATHER THAN A REWRITE,
AND EVERY HABIT OF A PARTICULAR SERVER BELONGS IN THIS FILE INSTEAD OF LEAKING
OUT INTO THE ASSISTANT.

TWO THINGS ACTUALLY DIFFER BETWEEN THEM, AND BOTH ARE NAMED BELOW: WHERE THE
CONTEXT LENGTH GOES, AND WHAT THE THINKING KNOB IS CALLED. A BACKEND THAT CANNOT
TAKE ONE SAYS SO PLAINLY RATHER THAN ACCEPTING IT AND DROPPING IT, WHICH IS THE
FAILURE THAT COSTS AN AFTERNOON: THE ANSWERS GET WORSE AND NOTHING SAYS WHY.

THE CLIENT PACKAGES ARE IMPORTED WHEN A BACKEND IS ACTUALLY BUILT, NOT UP HERE,
SO ONLY THE PROVIDER YOU USE HAS TO BE INSTALLED.

TO ADD ONE: WRITE THE BUILDER, PUT IT IN PROVIDERS. NOTHING ELSE MOVES.
"""

import importlib

OLLAMA = "ollama"
OPENAI = "openai"

# WHERE EACH ONE LISTENS WHEN NOBODY SAYS OTHERWISE. THE OPENAI SHAPE POINTS AT
# THE SAME LOCAL SERVER ON PURPOSE: IT IS THE FALLBACK FOR ANYTHING THAT SPEAKS
# THAT REQUEST, LM STUDIO AND VLLM AND LLAMA.CPP INCLUDED, AND A HOSTED ONE IS
# THE SAME LINE WITH A DIFFERENT ADDRESS.
URLS = {
    OLLAMA: "http://localhost:11434",  # NATIVE. NO /v1, THE CLIENT ADDS /api/chat.
    OPENAI: "http://localhost:11434/v1",  # THE CLIENT ADDS /chat/completions.
}

# WHICH ONES WILL TAKE A CONTEXT LENGTH PER REQUEST. THE OPENAI REQUEST HAS NO
# FIELD FOR IT, SO A SERVER BEHIND IT SERVES WHATEVER IT WAS STARTED WITH, AND
# OLLAMA STARTS AT 4096 AND THEN TRUNCATES IN SILENCE. llm.caveat() SAYS THIS
# OUT LOUD AT STARTUP RATHER THAN LEAVING IT TO BE DISCOVERED.
SETS_CONTEXT = {OLLAMA: True, OPENAI: False}

# HOW TO GET A MODEL THAT IS NOT THERE. PRINTED FOR A PERSON, NEVER RUN.
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
    """OLLAMA'S OWN /api/chat.

    IT TAKES num_ctx PER REQUEST, WHICH IS THE WHOLE REASON IT IS THE DEFAULT:
    NOTHING TO BUILD BEFOREHAND, NO COPY OF THE WEIGHTS UNDER ANOTHER NAME, AND
    NO STEP IN THE SETUP THAT CAN BE FORGOTTEN. THE MODEL IS THE ONE YOU PULLED.

    key IS UNUSED. A LOCAL SERVER ASKS FOR NONE, AND THE SIGNATURE IS THE SAME
    FOR EVERY BACKEND ON PURPOSE.
    """
    chat = client("langchain_ollama", "ChatOllama", OLLAMA)

    return chat(
        base_url=url,
        model=model,
        temperature=temperature,
        num_ctx=context,
        reasoning=effort,  # SENT AS think. A LEVEL, OR None FOR THE MODEL'S OWN.
        client_kwargs={"timeout": timeout},
    )


def openai(model, url, key, temperature, context, effort, timeout):
    """THE OPENAI REQUEST SHAPE, WHICH IS ALSO LM STUDIO'S, VLLM'S, LLAMA.CPP'S
    AND EVERY HOSTED PROVIDER'S.

    context IS ACCEPTED AND CANNOT BE SENT, BECAUSE THE REQUEST HAS NOWHERE TO
    PUT IT. SEE SETS_CONTEXT ABOVE, WHICH IS WHAT MAKES THAT SAYABLE INSTEAD OF
    SILENT.
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
    """WHERE TO POST TO: WHAT WAS ASKED FOR, OR THE PROVIDER'S OWN DEFAULT."""
    return url or URLS.get(name)


def sets_context(name):
    return SETS_CONTEXT.get(name, False)


def install(name, model, url=None):
    """HOW TO GET A MODEL THIS BACKEND DOES NOT HAVE."""
    return INSTALL.get(name, "").format(model=model, url=address(name, url))


def caveat(name, model):
    """WHAT THIS BACKEND CANNOT DO, IN ONE SENTENCE, OR None WHEN IT CAN DO IT ALL."""
    if sets_context(name):
        return None

    return NO_CONTEXT.format(name=name, model=model)


def names():
    return sorted(PROVIDERS)


if __name__ == "__main__":  # WHAT IS ON OFFER, AND WHAT EACH ONE WILL AND WILL NOT TAKE.
    for each in names():
        print(f"{each:8} {address(each):32} context per request: {sets_context(each)}")
