"""Shared PostHog AI Observability setup for Happy's production model clients."""

import logging
import os
import uuid
from urllib.parse import urlparse

from dotenv import load_dotenv
from posthog import Posthog

log = logging.getLogger("happy")

load_dotenv()


def create_posthog_client():
    """Create Happy's process-wide client when analytics is configured."""
    token = os.environ.get("POSTHOG_PROJECT_TOKEN")
    host = os.environ.get("POSTHOG_HOST")
    if not token or not host:
        if os.environ.get("HAPPY_ENV") != "production":
            variable = "POSTHOG_PROJECT_TOKEN" if not token else "POSTHOG_HOST"
            raise RuntimeError(
                f"{variable} variable required by PostHog is missing or un-configured, "
                f"this causes events to be silently missed. This error stops appearing once "
                f"{variable} is configured"
            )
        return None
    try:
        return Posthog(
            api_key=token,
            host=host,
            privacy_mode=False,
            enable_exception_autocapture=False,
        )
    except Exception as error:
        log.warning("PostHog AI Observability is unavailable: %s", type(error).__name__)
        return None


def new_session_id(prefix):
    """Return an ID that groups one process-run conversation in AI Observability."""
    return f"{prefix}-{uuid.uuid4()}"


def new_trace_id():
    """Return an ID that groups model and tool work in one user turn."""
    return str(uuid.uuid4())


def provider_for(base_url):
    """Name known OpenAI-compatible providers for accurate model-cost attribution."""
    host = urlparse(str(base_url)).hostname or ""
    if host == "api.openai.com":
        return "openai"
    if "openrouter" in host:
        return "openrouter"
    if "groq" in host:
        return "groq"
    if "generativelanguage" in host or "google" in host:
        return "google"
    if "ollama" in host or host in ("localhost", "127.0.0.1") and ":11434" in str(base_url):
        return "ollama"
    if host in ("localhost", "127.0.0.1") and ":1234" in str(base_url):
        return "lmstudio"
    return None
