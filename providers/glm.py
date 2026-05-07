"""Zhipu GLM provider.

Targets `https://open.bigmodel.cn/api/paas/v4`, the Z.ai (Zhipu AI)
OpenAI-compatible endpoint. Mainland-China-friendly; tops the BenchLM
Chinese leaderboard.

Single-tier. Zhipu releases new flagships frequently (GLM-4.6, GLM-4.7,
GLM-5, GLM-5.1) and lets the model name pick generation, so we expose a
single `glm_model` field rather than baking a flash/pro split.
"""
from __future__ import annotations

from ._openai_compatible import OpenAICompatibleProvider


class GLMProvider(OpenAICompatibleProvider):
    name = "glm"
    display_name = "Zhipu GLM"

    _key_field = "glm_api_key"
    _endpoint_field = "glm_endpoint"
    _model_field = "glm_model"

    _default_endpoint = "https://open.bigmodel.cn/api/paas/v4"
    # glm-4.6 is the proven stable flagship (355B MoE / 32B active, 200K
    # context). GLM-5 (745B) and GLM-5.1 are newer; users can opt in via
    # config once they've confirmed account access.
    _default_model = "glm-4.6"
