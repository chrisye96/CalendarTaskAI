"""Mistral AI provider.

Targets `https://api.mistral.ai/v1`, OpenAI chat-completions wire format.
Useful for EU users wanting GDPR-friendly hosting and for users who like
Mistral's open-weight flagship lineage (Mistral Large 3, Small 4).

Single-tier. Mistral's `-latest` aliases auto-track the current Large /
Small generation, so users don't need to bump the model field on every
release.
"""
from __future__ import annotations

from ._openai_compatible import OpenAICompatibleProvider


class MistralProvider(OpenAICompatibleProvider):
    name = "mistral"
    display_name = "Mistral AI"

    _key_field = "mistral_api_key"
    _endpoint_field = "mistral_endpoint"
    _model_field = "mistral_model"

    _default_endpoint = "https://api.mistral.ai/v1"
    # `mistral-large-latest` is the documented alias for the current
    # flagship (Mistral Large 3 as of May 2026, 675B MoE). Users on a
    # tighter budget can override to `mistral-small-latest`.
    _default_model = "mistral-large-latest"
