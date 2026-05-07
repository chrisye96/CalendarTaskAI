"""Shared base for providers speaking the OpenAI chat-completions wire format.

DeepSeek, OpenAI itself, and Moonshot AI's Kimi all expose
`POST {endpoint}/chat/completions` with the same JSON shape:

    request  : {"model": ..., "messages": [{"role": "system"|"user", ...}], ...}
    response : {"choices": [{"message": {"content": "..."}}], ...}

This base class encapsulates the HTTP call and JSON shape so each concrete
provider only needs to declare its endpoint, default model, and key field.

We use `urllib` directly rather than the `openai` SDK to avoid pulling in a
~1 MB dependency for what is otherwise a single POST request.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from logger import get_logger

from .base import LLMProvider, NotConfigured

log = get_logger(__name__)


class OpenAICompatibleProvider(LLMProvider):
    """Base class for any provider speaking OpenAI chat-completions.

    Subclasses set:
      * `name` / `display_name` from LLMProvider
      * `_key_field`     - config key holding the API key
      * `_endpoint_field`- config key holding the base endpoint URL
      * `_model_field`   - config key holding the model name
      * `_default_endpoint` and `_default_model` - sensible defaults

    The two-tier `analyze` / `analyze_high_quality` split that DeepSeek uses
    is also covered here: subclasses can declare `_pro_model_field` and
    `_pro_threshold_field` to opt into the same flash/pro switching logic.
    """

    # --- subclass declares these ------------------------------------------
    _key_field: str = ""
    _endpoint_field: str = ""
    _model_field: str = ""
    _default_endpoint: str = ""
    _default_model: str = ""

    # Optional second tier ("pro" model). If both fields are set, the
    # provider opts into supports_quality_override and tier-by-task-count.
    _pro_model_field: str | None = None
    _pro_threshold_field: str | None = None
    _default_pro_model: str | None = None
    _default_pro_threshold: int = 5

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.api_key = config.get(self._key_field, "").strip()
        self.endpoint = config.get(self._endpoint_field, self._default_endpoint).rstrip("/")
        self.model = config.get(self._model_field, self._default_model)
        # Subclass opts into the flash/pro tier split by setting BOTH
        # `_pro_model_field` AND `_pro_threshold_field`. Without both,
        # `config.get(None, ...)` would crash later in `_pick_model`.
        if (
            self._pro_model_field
            and self._pro_threshold_field
            and self._default_pro_model
        ):
            self.pro_model = config.get(self._pro_model_field, self._default_pro_model)
            self.pro_threshold = int(
                config.get(self._pro_threshold_field, self._default_pro_threshold)
            )
        else:
            self.pro_model = None
            self.pro_threshold = 0
        self.timeout = int(config.get("request_timeout_sec", 30))

    # --- LLMProvider hooks ------------------------------------------------

    def supports_quality_override(self) -> bool:
        return self.pro_model is not None

    def analyze(self, system_prompt: str, user_message: str) -> list[dict]:
        return self._call(system_prompt, user_message, force_pro=False)

    def analyze_high_quality(self, system_prompt: str, user_message: str) -> list[dict]:
        return self._call(system_prompt, user_message, force_pro=True)

    # --- core ------------------------------------------------------------

    def _pick_model(self, user_message: str, *, force_pro: bool) -> str:
        """Auto-pick model: pro if forced, or above the task-count threshold."""
        if not self.pro_model:
            return self.model
        if force_pro:
            return self.pro_model
        task_count = sum(1 for line in user_message.splitlines() if line.strip())
        return self.pro_model if task_count > self.pro_threshold else self.model

    def _call(self, system_prompt: str, user_message: str, *, force_pro: bool) -> list[dict]:
        if not self.api_key:
            raise NotConfigured(
                f"{self.display_name} API key not configured. Add it via the "
                f"tray menu -> Config or run: python main.py config setup"
            )

        # parse_response is shared across providers; lazy import dodges a
        # circular import at module load time.
        from ai_client import parse_response

        model = self._pick_model(user_message, force_pro=force_pro)
        log.info(
            "%s call: model=%s timeout=%ss force_pro=%s",
            self.display_name, model, self.timeout, force_pro,
        )

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
            try:
                detail = e.read().decode("utf-8", errors="replace")
            except Exception:
                detail = ""
            log.error("%s HTTP %s: %s", self.display_name, e.code, detail[:500])
            raise RuntimeError(
                f"{self.display_name} API HTTP {e.code}: {detail[:200]}"
            ) from e

        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(
                f"Unexpected {self.display_name} response shape: {payload}"
            ) from e

        return parse_response(content)
