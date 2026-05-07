"""Kimi (Moonshot AI) provider.

Targets `https://api.moonshot.cn/v1`, which speaks the OpenAI
chat-completions wire format. Useful for users in mainland China who
have stable access to Moonshot but not to OpenAI / Gemini.

Single-tier (no flash/pro split). Moonshot's three context-length tiers
(`moonshot-v1-8k` / `-32k` / `-128k`) trade off price against context
window rather than reasoning quality, so we default to 32k as a sane
middle and let users override.
"""
from __future__ import annotations

from ._openai_compatible import OpenAICompatibleProvider


class KimiProvider(OpenAICompatibleProvider):
    name = "kimi"
    display_name = "Kimi (Moonshot)"

    _key_field = "kimi_api_key"
    _endpoint_field = "kimi_endpoint"
    _model_field = "kimi_model"

    _default_endpoint = "https://api.moonshot.cn/v1"
    _default_model = "moonshot-v1-32k"
