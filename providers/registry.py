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
from .glm import GLMProvider
from .grok import GrokProvider
from .kimi import KimiProvider
from .mistral import MistralProvider
from .openai import OpenAIProvider
from .openrouter import OpenRouterProvider
from .qwen import QwenProvider

# Order matters: this is the order shown in the setup wizard radio list
# and in `list_providers()`. We group by region/style so the wizard reads
# top-to-bottom: free-tier-first Western providers, then paid Western,
# then the China cluster (Kimi/Qwen/GLM share an audience), then the
# OpenRouter aggregator at the bottom for users who want everything else.
_REGISTRY: dict[str, type[LLMProvider]] = {
    GeminiProvider.name:     GeminiProvider,      # Google, free tier available
    OpenAIProvider.name:     OpenAIProvider,      # ChatGPT, paid only, most well-known
    ClaudeProvider.name:     ClaudeProvider,      # Anthropic, paid only, strong long context
    GrokProvider.name:       GrokProvider,        # xAI, paid; SuperGrok-aligned audience
    MistralProvider.name:    MistralProvider,     # EU-hosted; open-weight lineage
    DeepSeekProvider.name:   DeepSeekProvider,    # cheap, mainland-China-friendly
    KimiProvider.name:       KimiProvider,        # Moonshot, free tier, mainland-friendly
    QwenProvider.name:       QwenProvider,        # Alibaba DashScope, mainland-friendly
    GLMProvider.name:        GLMProvider,         # Zhipu, mainland-friendly
    OpenRouterProvider.name: OpenRouterProvider,  # 300+ models behind one key
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
