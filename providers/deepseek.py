"""DeepSeek provider.

Wraps the OpenAI-compatible chat-completions API at
`https://api.deepseek.com/v1`. Uses the `_OpenAICompatibleProvider` base
class for the wire format; DeepSeek-specific bits are just the endpoint,
model field names, and the flash/pro split (per PROJECT_DECISIONS.md C3).
"""
from __future__ import annotations

from ._openai_compatible import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    name = "deepseek"
    display_name = "DeepSeek"

    _key_field = "deepseek_api_key"
    _endpoint_field = "deepseek_endpoint"
    _model_field = "deepseek_model_flash"

    _default_endpoint = "https://api.deepseek.com/v1"
    _default_model = "deepseek-v4-flash"

    # Two-tier: flash for short batches, pro above the threshold.
    _pro_model_field = "deepseek_model_pro"
    _pro_threshold_field = "deepseek_pro_threshold"
    _default_pro_model = "deepseek-v4-pro"
    _default_pro_threshold = 5
