"""WHERE THE THINKING HAPPENS."""

from brain.model import LLMError
from brain.thinking import Happy, troubles, watches

__all__ = ["Happy", "LLMError", "caveat", "create", "troubles", "watches"]


def create(**kwargs):
    return Happy(**kwargs)


def caveat():
    """WHAT THE BACKEND IN USE CANNOT DO, OR None."""
    from brain import model

    return model.caveat()
