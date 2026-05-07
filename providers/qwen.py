"""Alibaba Qwen (DashScope) provider.

Targets DashScope's OpenAI-compatible endpoint
(`https://dashscope.aliyuncs.com/compatible-mode/v1`). Mainland-China
users with an Alibaba Cloud account get free quota and stable access to
the Qwen3 family.

Single-tier. Qwen has a mature flash/plus/max ladder that mirrors our
DeepSeek flash/pro pattern, but the "right" tier is task-shape-dependent
in ways CalendarTaskAI can't predict, so we expose `qwen_model` as a
single field and default to the balanced middle tier.

Region note: international users can swap `qwen_endpoint` to
`https://dashscope-intl.aliyuncs.com/compatible-mode/v1` (Singapore) or
`https://dashscope-us.aliyuncs.com/compatible-mode/v1` (US Virginia).
"""
from __future__ import annotations

from ._openai_compatible import OpenAICompatibleProvider


class QwenProvider(OpenAICompatibleProvider):
    name = "qwen"
    display_name = "Alibaba Qwen"

    _key_field = "qwen_api_key"
    _endpoint_field = "qwen_endpoint"
    _model_field = "qwen_model"

    _default_endpoint = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    # qwen-plus is the balanced mid-tier: cheaper than qwen3-max, faster
    # than qwen-turbo for the prompt sizes CalendarTaskAI sends. Users
    # can override to qwen3-max (flagship) or qwen3.5-flash (cheapest).
    _default_model = "qwen-plus"
