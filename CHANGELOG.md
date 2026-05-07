# Changelog

Versions follow [Semantic Versioning](https://semver.org). Dates are in `YYYY-MM-DD`.

## v1.0.0 (2026-05-06, first public release)

First release of the unofficial CalendarTaskAI plugin for DesktopCal.
Distributable as both a pip-installable Python package and a single zip
containing a Windows executable bundle.

### Highlights

- **BYOK across 5 mainstream LLM providers.** Bring your own key for any
  one of: Google Gemini, OpenAI ChatGPT, Anthropic Claude, DeepSeek, or
  Moonshot Kimi. The setup wizard lets you pick at first launch and
  switch later without restarting. New providers plug in by subclassing
  `LLMProvider`.
- **Pluggable provider backend.** Gemini is the default for new users
  (free tier; signup without payment). When a second key is configured,
  Gemini failures auto-fallback to DeepSeek-flash so a flaky API call
  does not lose work. Manual "Re-run with DeepSeek-flash / Pro" buttons
  in the confirm view for explicit escalation.
- **Deterministic-first parsing.** Date hints (today, tomorrow, next
  Monday, 2026-03-25, plus the equivalent Chinese forms) and time hints
  (9:00, 9am, 9-10am, plus equivalent Chinese forms)
  are extracted by regex; the LLM only handles the leftovers. No silent
  format drift.
- **Recurring tasks.** Pre-expanded 12 weeks ahead, with a startup top-up
  that keeps the rolling window full as time advances. Supports both
  Chinese (every Monday, 15th of every month) and English (every monday)
  syntax. Time prefixes attached to the rule body are preserved.
- **Workflow conveniences.** Undo last add, 5 built-in templates plus
  user-defined entries in templates.json, JSON backup and restore, CLI
  `next [N]` for upcoming-window listings.
- **Light and Dark themes,** switchable via tray menu. The macaron baby
  blue identity is preserved in both modes via desaturation rather than
  naive inversion. Every action button passes WCAG AA contrast in both
  themes.
- **Robust packaging.** Two executables in one bundle: `CalendarTaskAI.exe`
  (silent, tray + hotkey) and `CalendarTaskAI-cli.exe` (CLI with
  console). Build via `python build_release.py`, or push a versioned
  git tag and let the GitHub Actions workflow do it on a clean Windows
  runner.

### Architecture

- Roughly 25 production Python modules, around 6,000 lines of code.
- 210 hermetic unit tests covering the parser stack, all 5 providers,
  recurring rules, templates, backup and restore, and theme tokens.
- Runtime data lives under `%APPDATA%\CalendarTaskAI\` (config, profile,
  history, recurring, templates, last-op, logs); the install location
  is read-only so the same exe, source, or venv build all read the
  same user data.

### Deferred to a future release

- Toast notifications (was Phase 4a, withdrawn during build).
- Mini calendar heatmap (was Phase 4b, withdrawn after merge).
- Google Calendar sync (was Phase 4c, postponed).

These can come back in v1.1+ if there is demand.

### Breaking changes vs the original `1.0.0` script

- Source no longer co-located with user data. Old installs at
  `%APPDATA%\CalendarTaskAI\<source files>` should migrate to the new
  layout: source under `source/repos/CalendarTaskAI` (or anywhere on
  disk, including a frozen exe), data under `%APPDATA%\CalendarTaskAI\data\`.
- `auto_restart_desktopcal` is now off by default. Setting it to `true`
  restores the previous behavior of force-killing DesktopCal after every
  write.
- `gemini_model` no longer silently falls back to a different Gemini
  model on 404; it errors out so misconfigurations are visible.
  Cross-provider fallback (Gemini to DeepSeek-flash) replaces it.
- `preprocess_input` and `analyze_tasks` have new tuple return shapes
  to support the recurring-tasks pipeline.

### Acknowledgements

CalendarTaskAI is built on top of, and grateful to:

- The **DesktopCal** team for the calendar app this plugin writes into.
- The five LLM providers it supports out of the box: **Google Gemini,
  OpenAI, Anthropic Claude, DeepSeek, and Moonshot Kimi.**
- Open-source dependencies that do the heavy lifting: pystray, Pillow,
  keyboard, click, google-genai, PyInstaller.
