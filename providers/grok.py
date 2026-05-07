"""xAI Grok provider.

Targets `https://api.x.ai/v1`, which speaks the OpenAI chat-completions
wire format. Useful for users who already have an X / SuperGrok account
and want to route scheduling prompts through Grok rather than a separate
LLM.

Single-tier (no flash/pro split). xAI's tier names change frequently
(grok-4, grok-4-fast, grok-4.3 beta, etc.) so we expose the model name
as a single config field and let users pick.
"""
from __future__ import annotations

from ._openai_compatible import OpenAICompatibleProvider


class GrokProvider(OpenAICompatibleProvider):
    name = "grok"
    display_name = "xAI Grok"

    _key_field = "grok_api_key"
    _endpoint_field = "grok_endpoint"
    _model_field = "grok_model"

    _default_endpoint = "https://api.x.ai/v1"
    # grok-4 is the broadly-available stable flagship as of May 2026.
    # grok-4.3 beta is restricted to SuperGrok Heavy subscribers, so it's
    # not a safe default; users with access can override via config.
    _default_model = "grok-4"
