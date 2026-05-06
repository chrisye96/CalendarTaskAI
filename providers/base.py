"""Provider-agnostic LLM contract.

Every concrete provider (Gemini, DeepSeek, ...) subclasses `LLMProvider` and
implements `analyze(...)`. Higher layers (ai_client, ui) only know about this
abstract interface, so the rest of the codebase doesn't change when a new
provider is added.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class NotConfigured(Exception):
    """Raised when a provider is selected but its credentials are missing.

    Lets the UI show a targeted error like "Configure your DeepSeek API key
    first" instead of a generic stack trace.
    """


class LLMProvider(ABC):
    """Abstract base class for an LLM-backed task scheduler.

    Subclass contract:
      * `name`           - short identifier matching the `llm_provider` config
                           value (e.g. "gemini", "deepseek").
      * `display_name`   - human-readable name shown in UI.
      * `analyze(...)`   - run the LLM on `(system_prompt, user_message)`,
                           return parsed task allocations.
      * `analyze_high_quality(...)` (optional) - higher-quality variant for
                           providers that have a tier system. Default falls
                           back to plain `analyze`.
      * `supports_quality_override()` - True iff the provider exposes a
                           "use the smarter model" toggle.
    """

    name: str = ""
    display_name: str = ""

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def analyze(self, system_prompt: str, user_message: str) -> list[dict]:
        """Run the model and return [{"date": "YYYY-MM-DD", "task": "..."}].

        Raises:
            NotConfigured: when the provider is selected but unconfigured.
            Exception: on API/network/parse errors.
        """

    def analyze_high_quality(self, system_prompt: str, user_message: str) -> list[dict]:
        """Higher-quality variant. Default forwards to analyze().

        Providers with a flash/pro split override this to force the pro tier.
        """
        return self.analyze(system_prompt, user_message)

    def supports_quality_override(self) -> bool:
        """Override and return True if this provider has a smarter alternative
        the user can opt into (e.g. DeepSeek pro vs flash).
        """
        return False

    def test_connection(self) -> tuple[bool, str]:
        """Quick liveness check used by the setup wizard.

        Default impl just calls `analyze` with a tiny dummy prompt. Concrete
        providers can override with something cheaper (e.g. listing models).

        Returns (ok, message).
        """
        try:
            result = self.analyze(
                "You are a test. Respond with a JSON array containing one task "
                "for tomorrow.",
                "ping",
            )
            if not isinstance(result, list):
                return False, "Unexpected response shape"
            return True, f"OK ({self.display_name})"
        except NotConfigured as e:
            return False, str(e)
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"
