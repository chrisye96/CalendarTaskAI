"""OpenRouter provider.

Targets `https://openrouter.ai/api/v1`. OpenRouter is an aggregator that
proxies 300+ models (Claude, GPT, Gemini, Llama, Qwen, DeepSeek, Grok,
Mistral, etc.) behind a single OpenAI-compatible endpoint and a single
key.

Why ship this as its own provider rather than telling users to override
`openai_endpoint`: the tagline and key URL differ enough that surfacing
it as a first-class option in the wizard removes friction. Users who
want to try multiple frontier models without managing N keys gravitate
here.

Default model is `openrouter/auto`, which routes each prompt to a
"reasonable" model OpenRouter picks. Users who want a specific model
override `openrouter_model` to the OpenRouter model id, e.g.
`anthropic/claude-opus-4-7`, `meta-llama/llama-4-maverick`,
`deepseek/deepseek-v4-flash`.
"""
from __future__ import annotations

from ._openai_compatible import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    name = "openrouter"
    display_name = "OpenRouter (aggregator)"

    _key_field = "openrouter_api_key"
    _endpoint_field = "openrouter_endpoint"
    _model_field = "openrouter_model"

    _default_endpoint = "https://openrouter.ai/api/v1"
    # `openrouter/auto` is OpenRouter's prompt-aware router. No extra fee
    # vs picking a specific model; it just delegates to whatever fits.
    _default_model = "openrouter/auto"
