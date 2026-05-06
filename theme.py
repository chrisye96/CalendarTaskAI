"""Color tokens used across all Tkinter windows.

Single source of truth so setup_wizard and the main task window stay visually
consistent. Two palettes are defined: macaron-blue LIGHT and a dark mode
that keeps the macaron-blue identity through desaturation rather than simple
inversion.

Resolution order for `current_theme()`:
  1. Read `config["theme"]`. If "light" or "dark", use that.
  2. If "system" (or anything else), query the Windows registry for
     `HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize\\AppsUseLightTheme`
     and pick LIGHT (1) or DARK (0). Falls back to LIGHT on non-Windows
     or registry errors.

Why a few specific choices in the dark theme:

  * `bg = #1A2530` (not pure black). Pure black is harsh on LCD displays
    and hurts macaron identity. A blue-tinted slate keeps the brand.

  * `accent = #5C9DC8` (desaturated baby blue) and `accent_text = #1A2530`
    (DARK text on the accent button, flipped from light theme's white).
    White on `#5C9DC8` is ~3:1 contrast, fails WCAG AA for normal text;
    dark slate on the same blue is ~15:1 and looks correct in dark mode.

  * `title_bg = #3A5775` deeper than `accent`. The title bar should still
    feel branded but not glow at the top of the window in dark mode.
"""
from __future__ import annotations

import sys

LIGHT_THEME: dict[str, str] = {
    # Surfaces
    "bg":            "#F5F9FC",   # window background
    "surface":       "#FFFFFF",   # cards, inputs
    "surface_alt":   "#E3F2FD",   # secondary buttons, subtle highlights
    "border":        "#B3D9F2",   # 1 px borders / dividers
    "border_strong": "#89CFF0",   # focused inputs, selected radio cards

    # Text
    "fg":            "#2C3E50",   # primary
    "fg_muted":      "#78909C",   # captions, helper text
    "fg_subtle":     "#90A4AE",   # placeholders
    "link":          "#1976D2",   # hyperlink-style text

    # Accents
    "accent":        "#89CFF0",   # primary action background
    "accent_dark":   "#6BB8E0",   # primary action hover
    "accent_light":  "#D4EEFF",   # very pale accent (subtle highlights)
    # Dark text on the macaron-blue / green button bg. White text on either
    # the accent #89CFF0 (~1.7:1) or success #81C784 (~1.95:1) backgrounds
    # fails WCAG AA; dark navy passes both (5.66:1 and 4.93:1 respectively).
    "accent_text":   "#2C3E50",   # text on primary / success action

    # Button states (secondary buttons that aren't accent-colored)
    "button_hover":  "#BBDEFB",

    # Status / feedback
    "success":       "#81C784",
    "success_dark":  "#66BB6A",   # success hover
    "success_bg":    "#E8F5E9",
    "warning":       "#FFA726",
    "warning_bg":    "#FFF3E0",
    "error":         "#E57373",
    "error_bg":      "#FFEBEE",

    # Title bar (floating windows draw their own chrome)
    "title_bg":      "#89CFF0",
    "title_fg":      "#FFFFFF",

    # Disabled
    "disabled_bg":   "#CFD8DC",
    "disabled_fg":   "#90A4AE",

    # Misc
    "star":          "#FFD54F",   # rating stars

    # Heatmap density buckets for the mini-calendar view (GitHub-contributions
    # style). Five stops: no-tasks, 1-2, 3-4, 5-7, 8+. Stay on-brand within
    # the macaron-blue family. Stops 0-2 take the dark `fg`, stops 3-4 flip
    # to the lighter `accent_text` for legibility.
    "heat_0":        "#FFFFFF",   # no tasks (matches surface)
    "heat_1":        "#DBEDF8",   # very light tint
    "heat_2":        "#B3D9F2",   # = border
    "heat_3":        "#89CFF0",   # = accent
    # heat_4 must be darker than heat_3 (visual distinction) AND keep
    # ≥4.5:1 contrast with accent_text (#2C3E50, dark navy day-number).
    # `#69BCE0` is the sweet spot: ~0.12 luminance below heat_3 yet still
    # bright enough that dark text reads at ~4.9:1.
    "heat_4":        "#69BCE0",
}


DARK_THEME: dict[str, str] = {
    # Surfaces (blue-tinted slate, not pure black)
    "bg":            "#1A2530",   # window background
    "surface":       "#243240",   # cards, inputs
    "surface_alt":   "#2D3D4F",   # secondary buttons, subtle highlights
    "border":        "#3D5061",   # 1 px borders / dividers
    "border_strong": "#5C9DC8",   # focused inputs, selected radio cards

    # Text (primary fg ~13:1 on bg, fg_muted ~7:1, fg_subtle ~5:1; all AA+)
    "fg":            "#E8ECF0",   # primary
    "fg_muted":      "#A8B5C0",   # captions, helper text
    "fg_subtle":     "#8896A3",   # placeholders
    "link":          "#82B7E0",   # hyperlink, lighter blue for dark bg

    # Accents. Note: button TEXT is dark, not white, for AA contrast on
    # the desaturated accent. White on #5C9DC8 fails AA; dark on it passes.
    "accent":        "#5C9DC8",   # primary action background
    "accent_dark":   "#4A8AB4",   # primary action hover
    "accent_light":  "#3A4D62",   # subtle accent surface (e.g. selected list row)
    "accent_text":   "#1A2530",   # DARK text on accent button (flipped)

    # Button states
    "button_hover":  "#3D5061",

    # Status / feedback
    "success":       "#6FCB73",
    "success_dark":  "#5CB861",
    "success_bg":    "#1F3A22",
    "warning":       "#FFB74D",
    "warning_bg":    "#3F2E1A",
    "error":         "#EF8585",
    "error_bg":      "#3E1F1F",

    # Title bar. Deeper navy keeps brand color but doesn't glow on dark
    "title_bg":      "#3A5775",
    "title_fg":      "#FFFFFF",

    # Disabled
    "disabled_bg":   "#2A3540",
    "disabled_fg":   "#5A6770",

    # Misc (yellow stars work in both modes)
    "star":          "#FFD54F",

    # Heatmap density buckets, dark-mode tonal variants. Stop 0 matches
    # surface so empty days blend into the page; stops climb toward
    # `#5C9DC8` (full accent) so the busiest days pop against the dark
    # window without glowing. Day-number text uses `fg` on stops 0-2 and
    # `accent_text` (dark slate) on stops 3-4 (same flip logic as light).
    "heat_0":        "#243240",   # = surface
    "heat_1":        "#2D4055",
    "heat_2":        "#3A5775",   # = title_bg
    # heat_3 and heat_4 must be bright enough that the dark `accent_text`
    # (#1A2530) reads on them at ≥ 4.5:1. The earlier draft used the
    # accent_dark / accent tones (#4A8AB4 / #5C9DC8) but the former only
    # hit 3.85:1, failing AA. heat_3 promoted to the saturated-blue tone,
    # heat_4 to a brighter sky-blue so the gradient still strictly climbs.
    "heat_3":        "#5C9DC8",   # ~ 5.3:1 with accent_text
    "heat_4":        "#87C5E5",   # ~ 8.2:1 with accent_text
}


# Public values for `theme` config field.
THEME_CHOICES: tuple[str, ...] = ("light", "dark", "system")


def resolve_system_theme() -> str:
    """Detect the OS-level theme preference. Returns "light" or "dark".

    On Windows, reads HKCU AppsUseLightTheme (1=light, 0=dark). On any other
    OS, or if the registry read fails, falls back to "light".
    """
    if sys.platform != "win32":
        return "light"
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "light" if value == 1 else "dark"
    except Exception:
        return "light"


def resolve_effective_theme(setting: str | None = None) -> str:
    """Convert a `theme` config value into the concrete theme to apply.

    `setting` is one of "light", "dark", "system", or None (treated as
    "system"). Returns "light" or "dark" (never "system").
    """
    if setting in ("light", "dark"):
        return setting
    return resolve_system_theme()


def current_theme(setting: str | None = None) -> dict[str, str]:
    """Return the active theme dict.

    If `setting` is None, reads the `theme` field from config.json. Pass an
    explicit setting to bypass config (used by previews).
    """
    if setting is None:
        try:
            from config_manager import get_config
            setting = get_config("theme") or "system"
        except Exception:
            setting = "system"
    effective = resolve_effective_theme(setting)
    return DARK_THEME if effective == "dark" else LIGHT_THEME
