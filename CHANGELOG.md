# Changelog

Versions follow [Semantic Versioning](https://semver.org). Dates are in `YYYY-MM-DD`.

## v1.0.0 — 2026-05-06 (first public release)

First release of the unofficial CalendarTaskAI plugin for [DesktopCal](https://www.desktopcal.com/). Distributable as both a pip-installable Python package and a single `.zip` containing a Windows executable bundle.

### Highlights
- **BYOK LLM access**. Bring your own Gemini or DeepSeek API key; nothing ships with the app.
- **Pluggable provider backend**. Gemini default, DeepSeek opt-in. When DeepSeek is configured, Gemini failures auto-fallback to DeepSeek-flash. Manual "Re-run with DeepSeek-flash / Pro" buttons in the confirm view for explicit escalation.
- **Deterministic-first parsing**. Date hints (`今天`, `明天`, `下周一`, `2026-03-25`, `next monday`, ...) and time hints (`9点`, `下午3-5点`, `9:00-10:30`, `9am`, ...) are extracted by regex; the LLM only handles the leftovers. No silent format drift.
- **Recurring tasks**. `每周一健身房`, `每月15号交房租`, `every monday standup`, etc. Pre-expanded 12 weeks ahead, top-up at every startup.
- **Workflow conveniences**: undo last add, 5 built-in templates (Standup / 周报 / Sprint planning / 健身计划 / 读书清单) plus user-defined entries, JSON backup / restore, CLI `next [N]` for upcoming-window listings.
- **Light + Dark theme**, switchable via tray menu (`Light` / `Dark` / `Follow System`). Macaron baby-blue identity preserved in both modes via desaturation, not naive inversion. WCAG AA contrast on every action button in both themes.
- **Robust packaging**. Two executables in one bundle: `CalendarTaskAI.exe` (silent, tray + hotkey) and `CalendarTaskAI-cli.exe` (CLI with console). Build via `python build_release.py` or push a `v*` git tag and let the GitHub Actions workflow do it.

### Architecture
- 25+ Python modules, ~6 000 lines of production code, 197 hermetic unit tests covering the parser stack, providers, recurring rules, templates, backup/restore, and theme tokens.
- Runtime data lives under `%APPDATA%\CalendarTaskAI\` (config, profile, history, recurring, templates, last-op, logs); the install location is read-only so the same exe / source / venv build all read the same user data.

### Deferred to a future release
- Toast notifications (was Phase 4a — withdrawn during build).
- Mini calendar heatmap (was Phase 4b — withdrawn after merge).
- Google Calendar sync (was Phase 4c — postponed).

These can come back in v1.1+ if there's demand.

### Breaking changes vs the original `1.0.0` script
- Source no longer co-located with user data. Old installs at `%APPDATA%\CalendarTaskAI\<source files>` should migrate to the new layout: source under `source/repos/CalendarTaskAI` (or anywhere on disk, including a frozen exe), data under `%APPDATA%\CalendarTaskAI\data\`.
- `auto_restart_desktopcal` is now off by default. Setting it to `true` restores the previous behavior of force-killing DesktopCal after every write.
- `gemini_model` no longer silently falls back to a different Gemini model on 404; it errors out so misconfigurations are visible. Cross-provider fallback (Gemini → DeepSeek-flash) replaces it.
- `preprocess_input` and `analyze_tasks` have new tuple return shapes to support the recurring-tasks pipeline.

### Acknowledgements
- [DesktopCal](https://www.desktopcal.com/) team for the calendar app this plugs into.
- [pystray](https://github.com/moses-palmer/pystray), [Pillow](https://pillow.readthedocs.io), [keyboard](https://github.com/boppreh/keyboard), [click](https://click.palletsprojects.com), [google-genai](https://pypi.org/project/google-genai/) for the runtime.
- [PyInstaller](https://pyinstaller.org) for the Windows binary.
