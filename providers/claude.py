"""Anthropic Claude provider.

Anthropic uses its own `/v1/messages` API, NOT the OpenAI chat-completions
shape. The differences worth calling out:

  * Auth header is `x-api-key` (not `Authorization: Bearer`).
  * `system` is a top-level field, NOT a `messages[0]` entry.
  * `max_tokens` is required.
  * Response body has `content: [{"type": "text", "text": ...}, ...]`,
    not `choices[0].message.content`.
  * `anthropic-version` header is required.

Implemented with `urllib` to avoid a dependency on the `anthropic` SDK.
The SDK adds streaming, retries, and a few conveniences we don't need
for a single non-streaming call.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from logger import get_logger

from .base import LLMProvider, NotConfigured

log = get_logger(__name__)


class ClaudeProvider(LLMProvider):
    name = "claude"
    display_name = "Anthropic Claude"

    # Pinned to a stable Claude version that's known to exist. The model
    # name format on Anthropic's side is `claude-<gen>-<size>-<rev>` and
    # has rotated a few times; users can override `claude_model` if a
    # newer one is preferred.
    _DEFAULT_ENDPOINT = "https://api.anthropic.com/v1"
    _DEFAULT_MODEL = "claude-sonnet-4-6"
    _ANTHROPIC_VERSION = "2023-06-01"
    _DEFAULT_MAX_TOKENS = 2048

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.api_key = config.get("claude_api_key", "").strip()
        self.endpoint = config.get("claude_endpoint", self._DEFAULT_ENDPOINT).rstrip("/")
        self.model = config.get("claude_model", self._DEFAULT_MODEL)
        self.max_tokens = int(config.get("claude_max_tokens", self._DEFAULT_MAX_TOKENS))
        self.timeout = int(config.get("request_timeout_sec", 30))

    def analyze(self, system_prompt: str, user_message: str) -> list[dict]:
        if not self.api_key:
            raise NotConfigured(
                "Claude API key not configured. Add it via the tray menu -> "
                "Config or run: python main.py config setup"
            )

        from ai_client import parse_response

        log.info("Claude call: model=%s timeout=%ss", self.model, self.timeout)

        body = json.dumps({
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
            "temperature": 0.4,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self.endpoint}/messages",
            data=body,
            method="POST",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": self._ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode("utf-8", errors="replace")
            except Exception:
                detail = ""
            log.error("Claude HTTP %s: %s", e.code, detail[:500])
            raise RuntimeError(f"Claude API HTTP {e.code}: {detail[:200]}") from e

        # Response: {"content": [{"type": "text", "text": "..."}, ...], ...}
        # Concatenate every text block; the LLM sometimes splits its answer
        # into multiple blocks even for a single-shot prompt.
        try:
            blocks = payload["content"]
            text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        except (KeyError, TypeError) as e:
            raise RuntimeError(f"Unexpected Claude response shape: {payload}") from e

        if not text:
            raise RuntimeError("Claude returned empty content")

        return parse_response(text)
