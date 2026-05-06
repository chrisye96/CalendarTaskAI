"""Unit tests for the mini calendar heatmap.

Focus on the pure logic that doesn't require an actual Tkinter window:
density bucket mapping, the Monday-aligned grid start helper, and the
theme parity invariant for the new heat_* tokens.
"""
from datetime import date

import pytest

import calendar_view
import theme


# ---------------------------------------------------------------------------
# density_bucket
# ---------------------------------------------------------------------------

class TestDensityBucket:
    @pytest.mark.parametrize("count, expected", [
        # Bucket 0 covers 0 (and any negative defensive case).
        (0, 0),
        (-1, 0),
        # Bucket 1: 1-2.
        (1, 1),
        (2, 1),
        # Bucket 2: 3-4.
        (3, 2),
        (4, 2),
        # Bucket 3: 5-7.
        (5, 3),
        (6, 3),
        (7, 3),
        # Bucket 4: 8+, no upper bound.
        (8, 4),
        (20, 4),
        (100, 4),
    ])
    def test_known_counts(self, count, expected):
        assert calendar_view.density_bucket(count) == expected


class TestAccentTextForBucket:
    def test_low_buckets_use_plain_fg(self):
        # Stops 0-2: light/medium backgrounds; the theme's `fg` token
        # gives natural contrast and does NOT need the accent_text flip.
        for b in (0, 1, 2):
            assert calendar_view._use_accent_text_for_bucket(b) is False

    def test_high_buckets_use_accent_text(self):
        # Stops 3-4: saturated blues; switch to `accent_text` which is the
        # contrasting dark-on-blue token in both themes (verified AA below).
        for b in (3, 4):
            assert calendar_view._use_accent_text_for_bucket(b) is True


# ---------------------------------------------------------------------------
# _grid_start: Monday-aligned 6-week start
# ---------------------------------------------------------------------------

class TestGridStart:
    def test_first_is_monday_returns_first(self):
        # 2026-06-01 is a Monday.
        assert calendar_view._grid_start(date(2026, 6, 1)) == date(2026, 6, 1)

    def test_first_is_tuesday_steps_back_one(self):
        # 2026-09-01 is a Tuesday; step back to Aug 31 Monday.
        assert calendar_view._grid_start(date(2026, 9, 1)) == date(2026, 8, 31)

    def test_first_is_sunday_steps_back_six(self):
        # 2026-11-01 is a Sunday (weekday=6).
        assert calendar_view._grid_start(date(2026, 11, 1)) == date(2026, 10, 26)

    def test_anchor_can_be_mid_month_grid_start_uses_first(self):
        # Even if caller hands us a mid-month date, we anchor on day=1.
        assert calendar_view._grid_start(date(2026, 6, 15)) == date(2026, 6, 1)

    def test_grid_window_covers_42_days(self):
        # Property: from grid_start, day +41 should land on a Sunday so the
        # 6×7 grid is exactly Mon..Sun.
        from datetime import timedelta
        for sample in (date(2026, 1, 1), date(2026, 2, 1), date(2026, 12, 1)):
            start = calendar_view._grid_start(sample)
            end = start + timedelta(days=41)
            assert start.weekday() == 0   # Monday
            assert end.weekday() == 6     # Sunday


# ---------------------------------------------------------------------------
# theme parity for the new heat tokens
# ---------------------------------------------------------------------------

class TestHeatThemeParity:
    def test_all_five_stops_present_in_both_themes(self):
        for stop in range(5):
            key = f"heat_{stop}"
            assert key in theme.LIGHT_THEME, f"missing {key} in LIGHT_THEME"
            assert key in theme.DARK_THEME, f"missing {key} in DARK_THEME"

    def test_stops_strictly_darken_in_light_theme(self):
        # Light theme: heat_0 (white) is brightest; each higher stop has
        # equal or lower luminance. Strictly decreasing avoids visually
        # ambiguous bucket pairs.
        prev = _luminance(theme.LIGHT_THEME["heat_0"])
        for s in range(1, 5):
            cur = _luminance(theme.LIGHT_THEME[f"heat_{s}"])
            assert cur < prev, f"light heat_{s} not darker than heat_{s-1}"
            prev = cur

    def test_stops_strictly_brighten_in_dark_theme(self):
        # Dark theme: heat_0 (matches surface) is darkest; each higher stop
        # is brighter so the busiest days pop against the dark window.
        prev = _luminance(theme.DARK_THEME["heat_0"])
        for s in range(1, 5):
            cur = _luminance(theme.DARK_THEME[f"heat_{s}"])
            assert cur > prev, f"dark heat_{s} not brighter than heat_{s-1}"
            prev = cur

    def test_day_number_text_passes_aa_on_light_low_stops(self):
        # Stops 0-2 use `fg` (#2C3E50). Verify ≥ 4.5:1 on the lightest bgs.
        for s in (0, 1, 2):
            ratio = _contrast(theme.LIGHT_THEME["fg"], theme.LIGHT_THEME[f"heat_{s}"])
            assert ratio >= 4.5, f"light fg on heat_{s}: {ratio:.2f}"

    def test_day_number_text_passes_aa_on_light_high_stops(self):
        # Stops 3-4 use `accent_text` (the dark-text-on-light flip we
        # already verified for buttons). Reusing that same token here means
        # contrast is automatically AA on accent (#89CFF0) and stop 4.
        for s in (3, 4):
            ratio = _contrast(
                theme.LIGHT_THEME["accent_text"], theme.LIGHT_THEME[f"heat_{s}"]
            )
            assert ratio >= 4.5, f"light accent_text on heat_{s}: {ratio:.2f}"

    def test_day_number_text_passes_aa_on_dark_low_stops(self):
        # Dark stops 0-2 are very dark surfaces; `fg` (#E8ECF0) on them.
        for s in (0, 1, 2):
            ratio = _contrast(theme.DARK_THEME["fg"], theme.DARK_THEME[f"heat_{s}"])
            assert ratio >= 4.5, f"dark fg on heat_{s}: {ratio:.2f}"

    def test_day_number_text_passes_aa_on_dark_high_stops(self):
        # Dark stops 3-4 are saturated blue tones; the dark `accent_text`
        # (#1A2530) reads on top of them. Symmetric to the light-mode test.
        for s in (3, 4):
            ratio = _contrast(
                theme.DARK_THEME["accent_text"], theme.DARK_THEME[f"heat_{s}"]
            )
            assert ratio >= 4.5, f"dark accent_text on heat_{s}: {ratio:.2f}"


# ---------------------------------------------------------------------------
# helpers (small WCAG implementation, mirror of test_theme.py)
# ---------------------------------------------------------------------------

def _luminance(hex_color: str) -> float:
    r, g, b = (int(hex_color[i:i + 2], 16) / 255.0 for i in (1, 3, 5))

    def channel(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _contrast(fg: str, bg: str) -> float:
    a, b = sorted((_luminance(fg), _luminance(bg)))
    return (b + 0.05) / (a + 0.05)
