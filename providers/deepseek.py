"""DeepSeek provider.

Phase 1 stub. The wire format is the OpenAI-compatible chat-completions API
that DeepSeek serves at `https://api.deepseek.com/v1`. The implementation is
written but exercised against real keys only after the user supplies one;
until then `analyze()` simply raises `NotConfigured` with an actionable
message, and the setup wizard / UI handle that gracefully.

Tier selection (per PROJECT_DECISIONS.md C3, option D):
  * Auto: if the user message has more than `deepseek_pro_threshold`
    newline-separated tasks, use the pro model; else flash.
  * Manual override: `analyze_high_quality()` always forces pro. The UI
    surfaces this as a "Re-run with Pro" button when the provider's
    `supports_quality_override()` is True.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from logger import get_logger

from .base import LLMProvider, NotConfigured

log = get_logger(__name__)


class DeepSeekProvider(LLMProvider):
    name = "deepseek"
    display_name = "DeepSeek"

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get("deepseek_api_key", "").strip()
        self.endpoint = config.get("deepseek_endpoint", "https://api.deepseek.com/v1").rstrip("/")
        self.model_flash = config.get("deepseek_model_flash", "deepseek-v4-flash")
        self.model_pro = config.get("deepseek_model_pro", "deepseek-v4-pro")
        self.pro_threshold = int(config.get("deepseek_pro_threshold", 5))
        self.timeout = int(config.get("request_timeout_sec", 30))

    def supports_quality_override(self) -> bool:
        return True

    def _pick_model(self, user_message: str, *, force_pro: bool) -> str:
        if force_pro:
            return self.model_pro
        # Newline-separated unresolved tasks come in via ai_client. Above
        # the threshold we want the smarter tier.
        task_count = sum(1 for line in user_message.splitlines() if line.strip())
        return self.model_pro if task_count > self.pro_threshold else self.model_flash

    def analyze(self, system_prompt: str, user_message: str) -> list[dict]:
        return self._call(system_prompt, user_message, force_pro=False)

    def analyze_high_quality(self, system_prompt: str, user_message: str) -> list[dict]:
        return self._call(system_prompt, user_message, force_pro=True)

    def _call(self, system_prompt: str, user_message: str, *, force_pro: bool) -> list[dict]:
        if not self.api_key:
            raise NotConfigured(
                "DeepSeek API key not configured. Add it via the tray menu -> Config "
                "or run: python main.py config setup"
            )

        from ai_client import parse_response

        model = self._pick_model(user_message, force_pro=force_pro)
        log.info("DeepSeek call: model=%s timeout=%ss force_pro=%s",
                 model, self.timeout, force_pro)

        body = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.4,
            "stream": False,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self.endpoint}/chat/completions",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # Read body for diagnostics, then re-raise as a clean RuntimeError
            # so callers don't have to know about urllib types.
            try:
                detail = e.read().decode("utf-8", errors="replace")
            except Exception:
                detail = ""
            log.error("DeepSeek HTTP %s: %s", e.code, detail[:500])
            raise RuntimeError(f"DeepSeek API HTTP {e.code}: {detail[:200]}") from e

        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Unexpected DeepSeek response shape: {payload}") from e

        return parse_response(content)
