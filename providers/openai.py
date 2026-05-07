"""OpenAI / ChatGPT provider.

Targets the standard OpenAI chat-completions endpoint
(`https://api.openai.com/v1`). Same wire format as DeepSeek and Kimi, so
we just configure the base class.

Single-tier: OpenAI's tiers (e.g. gpt-5 vs gpt-4o-mini) differ in cost
more than in quality for short scheduling prompts, and a flash/pro split
mostly clutters the UI. Users who want the cheaper model can change
`openai_model` directly; users who want the smarter model also change it
directly. No second tier exposed.
"""
from __future__ import annotations

from ._openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    name = "openai"
    display_name = "OpenAI (ChatGPT)"

    _key_field = "openai_api_key"
    _endpoint_field = "openai_endpoint"
    _model_field = "openai_model"

    _default_endpoint = "https://api.openai.com/v1"
    # gpt-4o is the safest default: widely available, cheap, fast, plenty
    # smart for date-allocation prompts. Users can override to gpt-5 /
    # gpt-4o-mini / o4-mini etc. via config.
    _default_model = "gpt-4o"
