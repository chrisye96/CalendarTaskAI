"""Provider registry + factory.

Adding a new provider:
  1. Create providers/<name>.py with a subclass of LLMProvider.
  2. Add it to `_REGISTRY` below.
  3. Update DEFAULT_CONFIG in constants.py with any new keys.
"""
from __future__ import annotations

from .base import LLMProvider
from .claude import ClaudeProvider
from .deepseek import DeepSeekProvider
from .gemini import GeminiProvider
from .kimi import KimiProvider
from .openai import OpenAIProvider

# Order matters: this is the order shown in the setup wizard radio list
# and in `list_providers()`. Free-tier-first ordering nudges new users
# toward providers they can sign up for without a credit card.
_REGISTRY: dict[str, type[LLMProvider]] = {
    GeminiProvider.name:   GeminiProvider,    # Google, free tier available
    OpenAIProvider.name:   OpenAIProvider,    # paid only, but most well-known
    ClaudeProvider.name:   ClaudeProvider,    # paid only, strongest at long context
    DeepSeekProvider.name: DeepSeekProvider,  # cheap, mainland China-friendly
    KimiProvider.name:     KimiProvider,      # mainland China-friendly, free tier
}


def list_providers() -> list[tuple[str, str]]:
    """Return [(name, display_name), ...] for use in the setup wizard."""
    return [(p.name, p.display_name) for p in _REGISTRY.values()]


def get_provider(config: dict) -> LLMProvider:
    """Instantiate the provider configured by `config["llm_provider"]`.

    Raises ValueError if the configured provider name isn't registered.
    """
    name = config.get("llm_provider", "gemini")
    cls = _REGISTRY.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown llm_provider: {name!r}. "
            f"Known: {', '.join(sorted(_REGISTRY))}"
        )
    return cls(config)
