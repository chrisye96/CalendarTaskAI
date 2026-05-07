"""Tests for the LLM provider abstraction.

These cover only pure logic (factory, tier selection, NotConfigured guards).
End-to-end calls against real APIs are out of scope until we wire up CI with
recorded HTTP fixtures.
"""
import pytest

from providers import LLMProvider, NotConfigured, get_provider, list_providers
from providers.claude import ClaudeProvider
from providers.deepseek import DeepSeekProvider
from providers.gemini import GeminiProvider
from providers.kimi import KimiProvider
from providers.openai import OpenAIProvider


# ---------------------------------------------------------------------------
# Registry / factory
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_lists_all_known_providers(self):
        names = [name for name, _ in list_providers()]
        # Five providers ship in v1.0.0; this list is an explicit assertion
        # rather than a `>=` so adding/removing one fails the test loud.
        assert names == ["gemini", "openai", "claude", "deepseek", "kimi"]

    @pytest.mark.parametrize("name, klass", [
        ("gemini", GeminiProvider),
        ("openai", OpenAIProvider),
        ("claude", ClaudeProvider),
        ("deepseek", DeepSeekProvider),
        ("kimi", KimiProvider),
    ])
    def test_get_returns_correct_class(self, name, klass):
        p = get_provider({"llm_provider": name})
        assert isinstance(p, klass)
        assert p.name == name

    def test_default_provider_is_gemini(self):
        p = get_provider({})  # no llm_provider key
        assert p.name == "gemini"

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown llm_provider"):
            get_provider({"llm_provider": "bogus"})


# ---------------------------------------------------------------------------
# NotConfigured guards
# ---------------------------------------------------------------------------

class TestNotConfigured:
    """Every provider must raise NotConfigured (not crash) when its API key
    field is empty. The setup wizard relies on this to show an actionable
    error instead of an opaque traceback."""

    @pytest.mark.parametrize("klass, key_field", [
        (GeminiProvider, "gemini_api_key"),
        (OpenAIProvider, "openai_api_key"),
        (ClaudeProvider, "claude_api_key"),
        (DeepSeekProvider, "deepseek_api_key"),
        (KimiProvider, "kimi_api_key"),
    ])
    def test_provider_without_key_raises(self, klass, key_field):
        p = klass({key_field: ""})
        with pytest.raises(NotConfigured):
            p.analyze("sys", "msg")

    def test_deepseek_high_quality_without_key_raises(self):
        p = DeepSeekProvider({"deepseek_api_key": ""})
        with pytest.raises(NotConfigured):
            p.analyze_high_quality("sys", "msg")


# ---------------------------------------------------------------------------
# DeepSeek tier selection (pure logic)
# ---------------------------------------------------------------------------

class TestDeepSeekTierSelection:
    def _provider(self, threshold: int = 5) -> DeepSeekProvider:
        return DeepSeekProvider({
            "deepseek_api_key": "test",
            "deepseek_pro_threshold": threshold,
        })

    def test_below_threshold_picks_flash(self):
        p = self._provider(threshold=5)
        assert p._pick_model("a\nb\nc", force_pro=False) == "deepseek-v4-flash"

    def test_at_threshold_picks_flash(self):
        # 5 tasks; threshold is "more than 5", so 5 stays flash
        p = self._provider(threshold=5)
        assert p._pick_model("\n".join("abcde"), force_pro=False) == "deepseek-v4-flash"

    def test_above_threshold_picks_pro(self):
        p = self._provider(threshold=5)
        assert p._pick_model("\n".join("abcdef"), force_pro=False) == "deepseek-v4-pro"

    def test_force_pro_always_pro(self):
        p = self._provider(threshold=5)
        assert p._pick_model("just one", force_pro=True) == "deepseek-v4-pro"

    def test_blank_lines_dont_count(self):
        # Empty lines from formatting noise shouldn't push us into pro tier
        p = self._provider(threshold=5)
        msg = "task1\n\ntask2\n\n\ntask3"
        assert p._pick_model(msg, force_pro=False) == "deepseek-v4-flash"

    def test_threshold_is_configurable(self):
        p = self._provider(threshold=2)
        assert p._pick_model("a\nb", force_pro=False) == "deepseek-v4-flash"
        assert p._pick_model("a\nb\nc", force_pro=False) == "deepseek-v4-pro"


# ---------------------------------------------------------------------------
# Capability flags
# ---------------------------------------------------------------------------

class TestQualityOverrideFlags:
    def test_gemini_no_quality_override(self):
        p = GeminiProvider({"gemini_api_key": "x"})
        assert p.supports_quality_override() is False

    def test_deepseek_has_quality_override(self):
        p = DeepSeekProvider({"deepseek_api_key": "x"})
        assert p.supports_quality_override() is True

    @pytest.mark.parametrize("klass, key_field", [
        (OpenAIProvider, "openai_api_key"),
        (ClaudeProvider, "claude_api_key"),
        (KimiProvider, "kimi_api_key"),
    ])
    def test_single_tier_providers_have_no_quality_override(self, klass, key_field):
        # OpenAI / Claude / Kimi all use a single configured model. Surfacing a
        # "Re-run with Pro" button would be misleading because there's no
        # second tier to escalate to. DeepSeek is the only provider with a
        # built-in flash/pro split.
        p = klass({key_field: "x"})
        assert p.supports_quality_override() is False


# ---------------------------------------------------------------------------
# OpenAI-compatible base: shared shape across DeepSeek / OpenAI / Kimi
# ---------------------------------------------------------------------------

class TestOpenAICompatibleConfig:
    """The three OpenAI-compatible providers all read endpoint + model from
    config but use different field names. Verify each one wires its fields
    correctly so a user editing config.json gets the expected target."""

    def test_openai_endpoint_and_model_defaults(self):
        p = OpenAIProvider({})
        assert p.endpoint == "https://api.openai.com/v1"
        assert p.model == "gpt-4o"

    def test_openai_endpoint_override(self):
        # Useful for users routing through a corporate gateway.
        p = OpenAIProvider({"openai_endpoint": "https://gw.example.com/v1/"})
        # Trailing slash should be stripped (the base class does .rstrip("/")).
        assert p.endpoint == "https://gw.example.com/v1"

    def test_kimi_endpoint_and_model_defaults(self):
        p = KimiProvider({})
        assert p.endpoint == "https://api.moonshot.cn/v1"
        assert p.model == "moonshot-v1-32k"

    def test_kimi_model_override(self):
        p = KimiProvider({"kimi_model": "moonshot-v1-128k"})
        assert p.model == "moonshot-v1-128k"

    def test_deepseek_still_has_two_tier_fields(self):
        # Existing flash/pro behavior must keep working after the refactor.
        p = DeepSeekProvider({})
        assert p.model == "deepseek-v4-flash"
        assert p.pro_model == "deepseek-v4-pro"


# ---------------------------------------------------------------------------
# Claude: distinct API shape
# ---------------------------------------------------------------------------

class TestClaudeConfig:
    def test_endpoint_and_model_defaults(self):
        p = ClaudeProvider({})
        assert p.endpoint == "https://api.anthropic.com/v1"
        assert p.model == "claude-sonnet-4-6"
        assert p.max_tokens == 2048

    def test_max_tokens_override(self):
        p = ClaudeProvider({"claude_max_tokens": 8000})
        assert p.max_tokens == 8000

    def test_anthropic_version_pinned(self):
        # Anthropic's API requires the `anthropic-version` header; pin it
        # at a known-compatible value so a future SDK shift doesn't silently
        # break us.
        assert ClaudeProvider._ANTHROPIC_VERSION == "2023-06-01"


class TestDefault:
    def test_default_high_quality_falls_through(self):
        # A custom provider that doesn't override analyze_high_quality should
        # delegate to analyze; the abstract base provides this contract.
        class Dummy(LLMProvider):
            name = "dummy"
            display_name = "Dummy"
            calls: list[str] = []

            def analyze(self, system_prompt, user_message):
                self.calls.append("analyze")
                return [{"date": "2026-01-01", "task": "x"}]

        p = Dummy({})
        result = p.analyze_high_quality("s", "m")
        assert result == [{"date": "2026-01-01", "task": "x"}]
        assert p.calls == ["analyze"]
