"""LLM provider abstraction.

Public API:
    LLMProvider     - base class new providers subclass
    NotConfigured   - raised when a provider is selected but its credentials
                      / endpoint are missing
    get_provider()  - factory that returns the right provider instance for a
                      given config dict
"""
from .base import LLMProvider, NotConfigured
from .registry import get_provider, list_providers

__all__ = ["LLMProvider", "NotConfigured", "get_provider", "list_providers"]
