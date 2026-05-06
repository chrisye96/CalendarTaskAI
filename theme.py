"""Color tokens used across all Tkinter windows.

Single source of truth so setup_wizard and the main task window stay visually
consistent. Phase 3 will add DARK_THEME and a runtime switcher; for now only
the existing macaron-blue light theme is exposed.
"""
from __future__ import annotations

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
    "accent_text":   "#FFFFFF",   # text on primary action

    # Status / feedback
    "success":       "#66BB6A",
    "success_bg":    "#E8F5E9",
    "warning":       "#FFA726",
    "warning_bg":    "#FFF3E0",
    "error":         "#E57373",
    "error_bg":      "#FFEBEE",

    # Title bar (used by floating windows that draw their own chrome)
    "title_bg":      "#89CFF0",
    "title_fg":      "#FFFFFF",

    # Disabled
    "disabled_bg":   "#CFD8DC",
    "disabled_fg":   "#90A4AE",
}


def current_theme() -> dict[str, str]:
    """Return the active theme dict.

    Phase 1 always returns LIGHT_THEME. Phase 3 will read from config and
    return LIGHT_THEME or DARK_THEME accordingly.
    """
    return LIGHT_THEME
