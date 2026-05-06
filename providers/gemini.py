"""Google Gemini provider.

Wraps the google-genai SDK. Honors:
  * `gemini_api_key`           - required
  * `gemini_model`             - exact model name; no silent fallback (per
                                 project decision: surface 404s so users
                                 fix their config)
  * `request_timeout_sec`      - HTTP timeout
"""
from __future__ import annotations

from logger import get_logger

from .base import LLMProvider, NotConfigured

log = get_logger(__name__)


class GeminiProvider(LLMProvider):
    name = "gemini"
    display_name = "Google Gemini"

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get("gemini_api_key", "").strip()
        self.model = config.get("gemini_model", "gemini-3.1-flash-lite-preview")
        self.timeout = int(config.get("request_timeout_sec", 30))

    def analyze(self, system_prompt: str, user_message: str) -> list[dict]:
        if not self.api_key:
            raise NotConfigured("Gemini API key not configured")

        # Imported lazily so the wizard can render even if google-genai
        # isn't installed (rare, but better diagnostics that way).
        from google import genai

        # parse_response stays in ai_client because the JSON-array contract
        # is shared with future providers; importing here avoids a circular
        # import at module load time.
        from ai_client import parse_response

        client = genai.Client(api_key=self.api_key)

        try:
            gen_config = genai.types.GenerateContentConfig(
                system_instruction=system_prompt,
                http_options=genai.types.HttpOptions(timeout=self.timeout * 1000),
            )
        except (TypeError, AttributeError):
            log.debug("HttpOptions not supported by installed google-genai; no timeout")
            gen_config = genai.types.GenerateContentConfig(system_instruction=system_prompt)

        log.info("Gemini call: model=%s timeout=%ss", self.model, self.timeout)
        response = client.models.generate_content(
            model=self.model,
            contents=user_message,
            config=gen_config,
        )
        return parse_response(response.text)
