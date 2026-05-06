"""Tests for theme.py.

Covers the resolution logic + a structural invariant: the dark and light
palettes must expose the same set of color tokens so any consumer reading
`current_theme()["foo"]` works in both modes.
"""
import pytest

import theme


# ---------------------------------------------------------------------------
# Structural invariants
# ---------------------------------------------------------------------------

class TestPaletteShape:
    def test_dark_has_same_keys_as_light(self):
        # If dark mode ever drops a key the light theme uses, every consumer
        # would crash with a KeyError on `t["missing_token"]` after switching.
        assert theme.LIGHT_THEME.keys() == theme.DARK_THEME.keys()

    def test_all_values_are_hex(self):
        for name, t in (("light", theme.LIGHT_THEME), ("dark", theme.DARK_THEME)):
            for k, v in t.items():
                assert v.startswith("#") and len(v) == 7, (
                    f"{name}.{k!r} not a 6-digit hex: {v!r}"
                )

    def test_dark_is_actually_darker(self):
        # The bg token defines the overall mode: a dark theme MUST have a
        # darker `bg` than the light theme, otherwise something is wrong.
        assert _luminance(theme.DARK_THEME["bg"]) < _luminance(theme.LIGHT_THEME["bg"])

    def test_dark_text_passes_aa_contrast_on_dark_bg(self):
        # Body text on the surface must hit at least 4.5:1 (WCAG AA).
        ratio = _contrast(theme.DARK_THEME["fg"], theme.DARK_THEME["surface"])
        assert ratio >= 4.5, f"dark fg/surface contrast = {ratio:.2f}"

    def test_dark_accent_button_text_passes_contrast(self):
        # The dark theme uses dark text on the accent button (flipped from
        # light's white). Verify the flip actually buys us legibility.
        ratio = _contrast(theme.DARK_THEME["accent_text"], theme.DARK_THEME["accent"])
        assert ratio >= 4.5, f"dark accent_text/accent contrast = {ratio:.2f}"

    def test_light_accent_button_text_passes_contrast(self):
        # Symmetric check on light mode. White-on-baby-blue (the original
        # design) gave only ~1.7:1; the fix is dark navy on the same blue.
        ratio = _contrast(theme.LIGHT_THEME["accent_text"], theme.LIGHT_THEME["accent"])
        assert ratio >= 4.5, f"light accent_text/accent contrast = {ratio:.2f}"

    def test_light_success_button_text_passes_contrast(self):
        # The is_success button in ui.py uses ACCENT_TEXT on the success
        # background. Verify both halves of that pairing work.
        ratio = _contrast(theme.LIGHT_THEME["accent_text"], theme.LIGHT_THEME["success"])
        assert ratio >= 4.5, f"light accent_text/success contrast = {ratio:.2f}"

    def test_dark_success_button_text_passes_contrast(self):
        ratio = _contrast(theme.DARK_THEME["accent_text"], theme.DARK_THEME["success"])
        assert ratio >= 4.5, f"dark accent_text/success contrast = {ratio:.2f}"

    def test_light_text_passes_aa_contrast_on_light_bg(self):
        ratio = _contrast(theme.LIGHT_THEME["fg"], theme.LIGHT_THEME["surface"])
        assert ratio >= 4.5, f"light fg/surface contrast = {ratio:.2f}"


# ---------------------------------------------------------------------------
# Resolution logic
# ---------------------------------------------------------------------------

class TestResolution:
    def test_explicit_light_returns_light(self):
        assert theme.current_theme("light") is theme.LIGHT_THEME

    def test_explicit_dark_returns_dark(self):
        assert theme.current_theme("dark") is theme.DARK_THEME

    def test_resolve_effective_known_values(self):
        assert theme.resolve_effective_theme("light") == "light"
        assert theme.resolve_effective_theme("dark") == "dark"

    def test_resolve_effective_unknown_falls_back_to_system(self, monkeypatch):
        # Force a deterministic system answer.
        monkeypatch.setattr(theme, "resolve_system_theme", lambda: "light")
        assert theme.resolve_effective_theme("system") == "light"
        assert theme.resolve_effective_theme(None) == "light"
        assert theme.resolve_effective_theme("garbage") == "light"

    def test_current_theme_reads_config_when_no_arg(self, monkeypatch):
        # Make config say "dark" without touching real config_manager.
        import config_manager
        monkeypatch.setattr(config_manager, "get_config", lambda key: "dark" if key == "theme" else None)
        assert theme.current_theme() is theme.DARK_THEME

    def test_current_theme_resilient_to_config_failure(self, monkeypatch):
        import config_manager
        def boom(_):
            raise RuntimeError("config blew up")
        monkeypatch.setattr(config_manager, "get_config", boom)
        # Force the system probe to a known value so the test is deterministic.
        monkeypatch.setattr(theme, "resolve_system_theme", lambda: "light")
        assert theme.current_theme() is theme.LIGHT_THEME


# ---------------------------------------------------------------------------
# Helpers (small WCAG implementation)
# ---------------------------------------------------------------------------

def _luminance(hex_color: str) -> float:
    """Relative luminance per WCAG 2.1."""
    r, g, b = (int(hex_color[i:i + 2], 16) / 255.0 for i in (1, 3, 5))

    def channel(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _contrast(fg: str, bg: str) -> float:
    """WCAG contrast ratio between two hex colors."""
    a, b = sorted((_luminance(fg), _luminance(bg)))
    return (b + 0.05) / (a + 0.05)


# ---------------------------------------------------------------------------
# Sanity-check the helpers themselves
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_luminance_white_is_one(self):
        assert _luminance("#FFFFFF") == pytest.approx(1.0, abs=0.001)

    def test_luminance_black_is_zero(self):
        assert _luminance("#000000") == pytest.approx(0.0, abs=0.001)

    def test_contrast_white_on_black_is_max(self):
        assert _contrast("#FFFFFF", "#000000") == pytest.approx(21.0, abs=0.05)
