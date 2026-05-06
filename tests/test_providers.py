"""Tests for the LLM provider abstraction.

These cover only pure logic (factory, tier selection, NotConfigured guards).
End-to-end calls against real APIs are out of scope until we wire up CI with
recorded HTTP fixtures.
"""
import pytest

from providers import LLMProvider, NotConfigured, get_provider, list_providers
from providers.deepseek import DeepSeekProvider
from providers.gemini import GeminiProvider


# ---------------------------------------------------------------------------
# Registry / factory
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_lists_known_providers(self):
        names = [name for name, _ in list_providers()]
        assert "gemini" in names
        assert "deepseek" in names

    def test_get_gemini(self):
        p = get_provider({"llm_provider": "gemini"})
        assert isinstance(p, GeminiProvider)
        assert p.name == "gemini"

    def test_get_deepseek(self):
        p = get_provider({"llm_provider": "deepseek"})
        assert isinstance(p, DeepSeekProvider)
        assert p.name == "deepseek"

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
    def test_gemini_without_key_raises(self):
        p = GeminiProvider({"gemini_api_key": ""})
        with pytest.raises(NotConfigured):
            p.analyze("sys", "msg")

    def test_deepseek_without_key_raises(self):
        p = DeepSeekProvider({"deepseek_api_key": ""})
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
