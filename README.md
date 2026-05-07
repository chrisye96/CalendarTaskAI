# CalendarTaskAI

[![v1.0.0 released](https://img.shields.io/badge/v1.0.0-released-brightgreen?logo=github)](https://github.com/chrisye96/CalendarTaskAI/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-lightgrey?logo=windows)](https://www.microsoft.com/windows)
[![Build status](https://img.shields.io/github/actions/workflow/status/chrisye96/CalendarTaskAI/release.yml?label=build&logo=githubactions)](https://github.com/chrisye96/CalendarTaskAI/actions/workflows/release.yml)

> **AI-powered task scheduling for [DesktopCal](https://www.desktopcal.com/).**
> Type tasks naturally in Chinese or English; explicit dates and times are pinned by a deterministic regex parser, anything ambiguous is scheduled by an LLM that knows your calendar load and habits. Unofficial plugin, BYOK (bring your own API key); pick from any of 10 mainstream providers including Gemini, ChatGPT, Claude, Grok, Mistral, DeepSeek, Kimi, Qwen, GLM, or OpenRouter.

```
┌──────────────────────────────────────────────┐
│  Press Ctrl+Alt+Space anywhere               │
│  ┌────────────────────────────────────────┐  │
│  │ 明天9点开会                            │  │
│  │ 完成项目报告                           │  │
│  │ 每周一健身房                           │  │
│  └────────────────────────────────────────┘  │
│              [Submit]                        │
└──────────────────────────────────────────────┘
                    ↓
   AI Allocation:
   2026-05-07   [09:00] 开会
   2026-05-08   完成项目报告
   2026-05-11   健身房   ← 12 weeks expanded
   2026-05-18   健身房
   ...
                    ↓
            DesktopCal updated
```

---

## Quick Start

### A. Windows users (no Python required)

1. Download `CalendarTaskAI-v1.0.0.zip` from the [latest release](https://github.com/chrisye96/CalendarTaskAI/releases/latest).
2. Extract anywhere (e.g. `C:\Apps\CalendarTaskAI`).
3. Double-click `CalendarTaskAI.exe`. The setup wizard opens; pick a provider, paste your API key, click **Test**, then **Save**.
4. Press `Ctrl+Alt+Space` to start typing tasks. The tray icon (CT on baby blue) sits in the system tray; right-click for the full menu.

> Windows SmartScreen may warn on first launch (the bundle is unsigned). Click **More info** then **Run anyway**.

### B. Python developers

```powershell
git clone https://github.com/chrisye96/CalendarTaskAI.git
cd CalendarTaskAI
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pythonw main.py        # GUI mode (no console window)
# or:  python main.py today        # CLI mode
```

You need an API key from one of the supported providers. Quick links:

- [Google Gemini](https://aistudio.google.com/apikey) (free tier)
- [OpenAI ChatGPT](https://platform.openai.com/api-keys) (paid)
- [Anthropic Claude](https://console.anthropic.com/settings/keys) (paid)
- [xAI Grok](https://console.x.ai/) (paid)
- [Mistral AI](https://console.mistral.ai/api-keys) (EU-hosted)
- [DeepSeek](https://platform.deepseek.com/api_keys) (cheap)
- [Moonshot Kimi](https://platform.moonshot.cn/console/api-keys) (free tier)
- [Alibaba Qwen / DashScope](https://bailian.console.aliyun.com/?tab=model#/api-key) (mainland-friendly)
- [Zhipu GLM](https://open.bigmodel.cn/usercenter/apikeys) (mainland-friendly)
- [OpenRouter](https://openrouter.ai/keys) (300+ models, one key)

---

## What is CalendarTaskAI?

[DesktopCal](https://www.desktopcal.com/) is a beloved free Windows calendar that draws straight onto the desktop wallpaper. Adding tasks to it means clicking a date, opening a tiny inline editor, and typing. Fine for one task. Painful for the way most people actually plan: dump a list, expect the calendar to figure out where things go.

CalendarTaskAI sits beside DesktopCal and writes directly into its SQLite database. It accepts free-form input and applies two layers of understanding:

1. **A deterministic parser** handles every date and time format it recognizes (12 Chinese variants, 8 English ones, plus times in five formats and ranges). These tasks bypass the LLM entirely: instant, free, and offline.
2. **A pluggable LLM backend** picks dates only for tasks that don't carry an explicit hint. The prompt sees your profile (work hours, scheduling rules), current task load, recent interaction history, and your satisfaction ratings.

The result: 70-90% of typical input is resolved without any API call. The leftover 10-30% goes to whichever LLM you've configured (Gemini default; DeepSeek opt-in with auto-fallback when Gemini fails).

---

## Features

**Input**
- Free-form natural-language task entry, Chinese and English mixed
- Multi-task input via newline, `;`/`；`, or Chinese enumeration comma `、`
- Explicit dates: `今天`, `明天`, `下周一`, `3月25日`, `2026-12-01`, `next monday`, `in 3 days`, ...
- Explicit times: `9点`, `9点半`, `下午3-5点`, `9:00-10:30`, `9am`, ...
- Recurring patterns: `每周一健身房`, `每月15号交房租`, `every monday standup`

**Scheduling**
- Deterministic-first: regex resolves explicit hints, LLM handles only the rest
- 10 mainstream LLM providers supported out of the box: Google Gemini, OpenAI ChatGPT, Anthropic Claude, xAI Grok, Mistral AI, DeepSeek, Moonshot Kimi, Alibaba Qwen, Zhipu GLM, and OpenRouter (300+ models behind one key)
- Cross-provider auto-fallback: when DeepSeek is configured, a Gemini failure is silently retried on DeepSeek-flash so transient API issues don't lose work
- Manual escalation buttons in the confirm view: **Re-run with DeepSeek-flash** / **Re-run with DeepSeek Pro**
- Profile-aware prompting: scheduling rules in `profile.md` are honored by the LLM
- Behavioral learning: every accepted / rejected / moved task feeds back into future prompts

**Workflow**
- Global hotkey (default `Ctrl+Alt+Space`) opens the floating input window
- Tray icon menu: Add Task, Templates submenu, Today, Undo last add, Retry pending, Calendar refresh, Theme, Auto-start
- 5 built-in templates (Standup / 周报 / Sprint planning / 健身计划 / 读书清单), plus user-defined entries in `data/templates.json`
- One-click undo of the last batch added (CLI parity: `python main.py undo`)
- Offline cache: failed API requests retry automatically at next startup

**Distribution**
- Two Windows executables in one zip: `CalendarTaskAI.exe` (silent, tray + hotkey) and `CalendarTaskAI-cli.exe` (CLI with console)
- Or run from source on Python 3.10+
- JSON backup / restore covering config (keys redacted), profile, history, recurring rules, templates, and ±1 year of tasks

**Polish**
- Light + Dark theme, switchable via tray menu (Light / Dark / Follow System)
- All action buttons pass WCAG AA contrast in both themes
- Hi-DPI aware (sharp on 4K laptops)
- Logs to `%APPDATA%\CalendarTaskAI\logs\app.log` (rotating, 1 MB × 5)

---

## Installation

### Option A: Pre-built Windows executable

Recommended for non-developers.

1. Visit [Releases](https://github.com/chrisye96/CalendarTaskAI/releases) and download `CalendarTaskAI-vX.Y.Z.zip` (~25 MB).
2. Extract to a folder you control (e.g. `C:\Apps\CalendarTaskAI`).
3. Inside, you'll find:
   - `CalendarTaskAI.exe`: GUI launcher (no console window). This is what you run for daily use.
   - `CalendarTaskAI-cli.exe`: CLI variant with a console. Use this for `today`, `add`, `next`, `backup`, etc.
4. (Optional) Pin `CalendarTaskAI.exe` to taskbar / send to Start menu, or enable auto-start via the tray menu.

### Option B: From source

For Python 3.10+ on Windows.

```powershell
git clone https://github.com/chrisye96/CalendarTaskAI.git
cd CalendarTaskAI
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Then run:

| Mode | Command |
|------|---------|
| GUI (no console) | `pythonw main.py` |
| GUI (with console for debugging) | `python main.py` |
| CLI | `python main.py <command>` (see [CLI mode](#cli-mode)) |

### Option C: Build your own executable

```powershell
pip install -r requirements-dev.txt
python build_release.py
```

Produces `dist/CalendarTaskAI-vX.Y.Z.zip` after running the test suite. Or push a `v[0-9]*` tag to GitHub to trigger the release workflow which does the same on a clean Windows runner and attaches the zip to a GitHub Release as a draft.

---

## First-Run Setup

### GUI

The first launch shows a Tkinter wizard:

1. **Pick a provider** from the scrollable list (Gemini is the default for new users; free tier).
2. Click the "Get a {provider} API key" link to open the provider's key page in your browser.
3. Paste the key into the masked field.
4. (Recommended) Click **Test** to make a tiny live API call and confirm the key works.
5. **Save**.

The key is stored only on your machine, in `%APPDATA%\CalendarTaskAI\data\config.json`. To change it later, edit that file directly or open it via tray menu **Config**.

### CLI

```powershell
python main.py config setup
```

Walks through the same fields with prompts. Press Enter to keep the current value, type `q` to save and exit.

---

## Daily Use

### GUI mode

1. Press `Ctrl+Alt+Space` (or right-click tray → **Add Task**).
2. Type your tasks in the floating window. Multiple tasks per line work; separate with `;`/`；`/`、` or use newlines.
3. Press `Ctrl+Enter` (or click **Submit**).
4. The AI analyzes the input, then shows the proposed allocation with each task's date.
5. Click **Confirm** to write to DesktopCal, **Edit** to revise the input, or **Cancel** to discard.
6. (When DeepSeek is configured) The confirm view shows two extra buttons: **Re-run with DeepSeek-flash** for an alternative attempt, **Re-run with DeepSeek Pro** for genuinely complex inputs.

DesktopCal needs to be told to reload (its in-memory view doesn't auto-refresh). Either:
- Switch to another month and back, or restart DesktopCal manually, or
- Set `auto_restart_desktopcal: true` in `config.json` (off by default; warning: force-kills DesktopCal which loses unsaved state in its other panels).

### CLI mode

| Command | Purpose | Example |
|---------|---------|---------|
| `add [TEXT]` | Add tasks via AI (or stdin if no TEXT) | `python main.py add "明天买菜"` |
| `today` | Show today's tasks | `python main.py today` |
| `next [N]` | Show tasks for the next N days (default 7) | `python main.py next 14` |
| `list [DATE]` | Show tasks for a date or range | `python main.py list 2026-03-25` |
| `done KEYWORD` | Mark matching tasks done | `python main.py done "买菜"` |
| `undone KEYWORD` | Unmark done | `python main.py undone "报告"` |
| `delete KEYWORD` | Delete matching tasks | `python main.py delete "取消的任务"` |
| `move KEYWORD DATE` | Move matching tasks to DATE | `python main.py move "会议" 2026-04-01` |
| `search KEYWORD` | Find tasks across all dates | `python main.py search "复盘"` |
| `undo` | Reverse the last batch added | `python main.py undo` |
| `backup [--out FILE]` | Export full state to JSON | `python main.py backup --out my-backup.json` |
| `restore FILE` | Restore from a backup JSON | `python main.py restore my-backup.json` |
| `export [--format md\|txt]` | Print tasks for a date range | `python main.py export --start 2026-03-01 --end 2026-03-31` |
| `retry` | Retry pending failed AI requests | `python main.py retry` |
| `refresh` | Print instructions for reloading DesktopCal's display | `python main.py refresh` |
| `profile [view\|edit\|reset]` | Manage the personal profile | `python main.py profile edit` |
| `config [show\|set\|setup]` | Manage configuration | `python main.py config show` |

---

## Tray Menu

Right-click the tray icon (a 64×64 square with "CT" on macaron baby blue) for:

- **Add Task**: opens the input window (default action; left-click also works)
- **Add from template ▶**: submenu of saved templates; pick one to pre-fill the input window
- **Today's Tasks**: message box listing today's pending tasks
- **Undo last add**: reverses the most recent batch (greyed when there's nothing to undo)
- **Retry Pending**: retry any failed AI requests sitting in the offline cache
- **Config**: opens `config.json` in the system editor
- **Profile**: opens `profile.md` in the system editor
- **Theme ▶**: Light / Dark / Follow System (radio menu)
- **Auto Start**: toggle the Windows registry entry that launches CalendarTaskAI on login
- **Quit**

---

## Configuration

All runtime data lives under `%APPDATA%\CalendarTaskAI\`:

```
%APPDATA%\CalendarTaskAI\
├─ data\
│   ├─ config.json       (provider keys, hotkey, theme, etc.)
│   ├─ profile.md        (your work habits + scheduling rules)
│   ├─ history.json      (interaction log + behavioral analysis)
│   ├─ pending.json      (failed AI requests waiting for retry)
│   ├─ recurring.json    (registered recurring rules)
│   ├─ templates.json    (5 built-ins seeded on first launch + user adds)
│   └─ last_op.json      (most recent batch, for Undo)
└─ logs\
    └─ app.log           (rotating, 1 MB × 5)
```

### `config.json` reference

```json
{
  "llm_provider": "gemini",
  "gemini_api_key": "your-key-here",
  "gemini_model": "gemini-3.1-flash-lite-preview",
  "openai_api_key": "",
  "openai_model": "gpt-4o",
  "openai_endpoint": "https://api.openai.com/v1",
  "claude_api_key": "",
  "claude_model": "claude-sonnet-4-6",
  "claude_endpoint": "https://api.anthropic.com/v1",
  "claude_max_tokens": 2048,
  "grok_api_key": "",
  "grok_model": "grok-4",
  "grok_endpoint": "https://api.x.ai/v1",
  "mistral_api_key": "",
  "mistral_model": "mistral-large-latest",
  "mistral_endpoint": "https://api.mistral.ai/v1",
  "deepseek_api_key": "",
  "deepseek_model_flash": "deepseek-v4-flash",
  "deepseek_model_pro": "deepseek-v4-pro",
  "deepseek_endpoint": "https://api.deepseek.com/v1",
  "deepseek_pro_threshold": 5,
  "kimi_api_key": "",
  "kimi_model": "moonshot-v1-32k",
  "kimi_endpoint": "https://api.moonshot.cn/v1",
  "qwen_api_key": "",
  "qwen_model": "qwen-plus",
  "qwen_endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "glm_api_key": "",
  "glm_model": "glm-4.6",
  "glm_endpoint": "https://open.bigmodel.cn/api/paas/v4",
  "openrouter_api_key": "",
  "openrouter_model": "openrouter/auto",
  "openrouter_endpoint": "https://openrouter.ai/api/v1",
  "hotkey": "ctrl+alt+space",
  "db_path": "%APPDATA%\\CalendarTask\\Db\\calendar.db",
  "auto_start": false,
  "retry_on_startup": true,
  "auto_restart_desktopcal": false,
  "request_timeout_sec": 30,
  "rating_interval": 20,
  "theme": "system"
}
```

| Field | Description |
|-------|-------------|
| `llm_provider` | One of `"gemini"`, `"openai"`, `"claude"`, `"grok"`, `"mistral"`, `"deepseek"`, `"kimi"`, `"qwen"`, `"glm"`, `"openrouter"`. Default Gemini. |
| `<provider>_api_key` | BYOK key for the chosen provider. Never sent off your machine except to that provider. Only the active provider's key is required; the others can stay empty. |
| `gemini_model` | Exact Gemini model name. 404 surfaces directly (no silent fallback to a different Gemini model). |
| `openai_model` | OpenAI model name. Defaults to `gpt-4o`; common overrides include `gpt-5`, `gpt-4o-mini`, `o4-mini`. |
| `claude_model` | Anthropic model name. Defaults to `claude-sonnet-4-6`. Override to `claude-opus-4-5` for harder reasoning or `claude-haiku-4-5` for faster, cheaper calls. |
| `claude_max_tokens` | Required by the Anthropic API. Default 2048 is plenty for date allocation. |
| `grok_model` | xAI model name. Defaults to `grok-4`. SuperGrok-Heavy users can override to `grok-4.3` once it leaves beta. |
| `mistral_model` | Mistral model name. Defaults to `mistral-large-latest` (Mistral Large 3). Override to `mistral-small-latest` for cheaper calls. |
| `deepseek_model_flash` / `_pro` | DeepSeek "fast" and "smart" tiers. The app picks pro for inputs above `deepseek_pro_threshold`. |
| `deepseek_pro_threshold` | Number of unresolved tasks above which DeepSeek auto-uses pro instead of flash. Default 5. |
| `kimi_model` | Moonshot context-length tier: `moonshot-v1-8k` / `-32k` / `-128k`. Default 32k. |
| `qwen_model` | Alibaba Qwen model. Defaults to `qwen-plus` (balanced). Override to `qwen3-max` (flagship) or `qwen3.5-flash` (cheapest). |
| `qwen_endpoint` | DashScope OpenAI-compatible endpoint. Mainland China by default; international users can swap to `dashscope-intl.aliyuncs.com` (Singapore) or `dashscope-us.aliyuncs.com`. |
| `glm_model` | Zhipu GLM model. Defaults to `glm-4.6`. Override to `glm-5` / `glm-5.1` once your account has access. |
| `openrouter_model` | OpenRouter model id. Defaults to `openrouter/auto` (the router picks for each prompt). Override to a specific id like `anthropic/claude-opus-4-7` or `meta-llama/llama-4-maverick`. |
| `<provider>_endpoint` | Base URL for the OpenAI-compatible / Anthropic API. Override only if routing through a corporate gateway or self-hosted endpoint. |
| `hotkey` | Global hotkey to open the input window (uses [keyboard](https://github.com/boppreh/keyboard) syntax). |
| `db_path` | Full path to DesktopCal's `calendar.db`. Defaults to `%APPDATA%\CalendarTask\Db\calendar.db` and can stay as-is unless DesktopCal is installed in a non-standard location. |
| `auto_start` | Run on Windows login. Toggleable via tray menu. |
| `retry_on_startup` | Retry failed AI requests automatically at every launch. |
| `auto_restart_desktopcal` | **Off by default.** When on, force-kills + relaunches DesktopCal after writing tasks (refreshes its view automatically but may discard unsaved state in its other panels). |
| `request_timeout_sec` | Per-call LLM API timeout. |
| `rating_interval` | Prompt for satisfaction rating every N operations. |
| `theme` | `"light"` / `"dark"` / `"system"`. `"system"` follows the Windows app theme. |

---

## Input Reference

### Date hints

| You type | Resolves to |
|----------|-------------|
| `今天` `今日` `今晚` | Today |
| `明天` `明日` | Tomorrow |
| `后天` `大后天` | Day after tomorrow / 3 days from now |
| `下周` | Next Monday |
| `下周一` ~ `下周日` | Next week's Mon/Tue/.../Sun |
| `这周三` `这周末` | This Wednesday / This Saturday |
| `周一` ~ `周日`, `星期一` ~ `星期天`, `礼拜一` ~ `礼拜天` | Next occurrence of that weekday |
| `下个月` `这个月` `月初` `月底` | First of next month / first of this month / first or last |
| `3天后` `三天后` `2周后` `1个月后` | Relative offsets (Arabic or Chinese numerals) |
| `2026年3月25日` `2026-03-25` `2026.03.25` `2026/03/25` | Full ISO/Chinese dates |
| `3月25日` `3月25` `0325` `3.25` `3/25` `3-25` | Short dates (year inferred; past dates roll to next year) |
| `today` `tonight` `tomorrow` `next week` `next monday` | English equivalents |
| `in 3 days` `in 2 weeks` `end of month` | English relative |

### Time hints

Time prefixes attach to the task text as `[HH:MM]` or `[HH:MM-HH:MM]`. The deterministic parser owns these (the LLM is forbidden from inventing them, to avoid format drift).

| You type | Becomes |
|----------|---------|
| `9点开会` | `[09:00] 开会` |
| `9点半开会` | `[09:30] 开会` |
| `9点45分会议` | `[09:45] 会议` |
| `上午9点开会` `下午3点开会` `晚上9点睡觉` `凌晨2点起床` `中午12点吃饭` | Period-aware 24-hour conversion |
| `9-10点 开会` `下午3-5点 讨论` | Chinese ranges |
| `9:00 daily standup` `3pm meeting` `9:00-10:30 review` `9-11am sprint` | Western ranges, AM/PM |

Combinable: `明天9点开会` resolves to date=tomorrow, task=`[09:00] 开会`.

### Recurring patterns

| You type | What gets scheduled |
|----------|---------------------|
| `每周一 健身房` | "健身房" every Monday for the next 12 weeks |
| `每周一三五 健身` | every Mon / Wed / Fri |
| `每周一、三、五 健身` | comma-separated equivalent |
| `每周三 上午10-11点 团队会议` | `[10:00-11:00] 团队会议` every Wednesday |
| `每月15号 交房租` | "交房租" on the 15th of every month |
| `每月1日 报销` | "报销" on the 1st |
| `every monday 9am standup` | `[09:00] standup` every Monday |
| `every fri team review` | "team review" every Friday |

Properties:
- **Pre-expanded ~12 weeks ahead.** New instances appear in the confirm view; you can cancel the whole batch.
- **Rules saved on confirm only.** Cancelled inputs leave no trace in `recurring.json`.
- **Top-up at startup.** Each launch refills the rolling 12-week window. Idempotent on a given day.
- **Out of scope:** biweekly, day-of-month ranges, "every other Tuesday", full cron. Open an issue if you'd actually use any of these.

### Separator behavior

| Separator | Splits? |
|-----------|---------|
| Newline | Yes |
| `;` `；` (English / Chinese semicolon) | Yes |
| `、` (Chinese enumeration comma) | Yes |
| `,` `，` (regular comma) | **No** (would mangle prose like "买菜, 然后洗衣服") |
| Space | **No** (would split phrases like "完成项目报告") |

---

## Personal Profile

The profile lives at `%APPDATA%\CalendarTaskAI\data\profile.md` and is fed into every LLM prompt. A template is generated on first launch:

```markdown
# Personal Profile

## Career
- Role: 
- Industry: 
- Current projects: 

## Skills
- Primary skills: 
- Learning: 

## Work Habits
- Preferred working hours: 
- Most productive time: 

## Scheduling Rules
<!-- The AI will follow these rules when assigning dates -->
- No work tasks on weekends
- Max 3 tasks per workday
- Programming tasks in the morning
- Exercise on Mon/Wed/Fri
- Meetings only in the afternoon

## Preferences
- Task priority style: deadline-driven
- Preferred task granularity: detailed steps
```

The **Scheduling Rules** section is the most directly impactful: each bullet is treated as a hard constraint by the LLM when picking dates for unresolved tasks. Edit via tray menu **Profile** or `python main.py profile edit`.

---

## Theming

Two palettes ship: a macaron baby-blue light theme and a desaturated-blue dark variant.

- **Light**: pastel surface, baby-blue accent, dark navy primary text.
- **Dark**: blue-tinted slate surface, desaturated baby-blue accent, off-white primary text. Action buttons use dark text on the lighter accent for WCAG AA contrast (white-on-baby-blue would fail AA).

Switch via tray menu **Theme ▶ Light / Dark / Follow System**. The "Follow System" option reads the Windows registry value `HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize\AppsUseLightTheme`.

Switching takes effect on the next time you open the input window or wizard. If a window is currently visible during the switch, it's left alone (so your work isn't yanked) and rebuilds with the new palette on next open.

---

## Backup & Restore

```powershell
python main.py backup --out my-backup.json
python main.py restore my-backup.json
```

A backup includes:
- `config.json` (API keys are replaced with `*** REDACTED ***`)
- `profile.md`
- `history.json`
- `templates.json`
- `recurring.json`
- ±1 year of tasks from the calendar database

A restore overwrites `profile.md`, `history.json`, `templates.json`, and `recurring.json`. Tasks are **appended** to the database (duplicates may result if you restore on top of a populated DB). API keys are kept from your existing `config.json`; the backup never contains real keys, even when made with `--overwrite-config`.

---

## How DesktopCal Integration Works

CalendarTaskAI writes directly to DesktopCal's SQLite database at `%APPDATA%\CalendarTask\Db\calendar.db`.

**Schema:**
- Table: `item_table`
- Key field: `it_unique_id` in the form `dkcal_mdays_YYYYMMDD` (e.g. `dkcal_mdays_20260325`)
- Content field: `it_content`. Tasks for a day are stored as one string with `\r\n` separators. Done tasks are prefixed with `[+]`.

**Refresh:**
DesktopCal caches its display in memory. After a write, it doesn't notice until you switch months in DesktopCal and back. Set `auto_restart_desktopcal: true` to have CalendarTaskAI force-restart DesktopCal after each write (warning: loses unsaved state in DesktopCal's other panels).

---

## Architecture

For curious developers. Roughly 25 modules and 6 000 lines of production Python; 197 unit tests.

### Pipeline

```
User Input
    │
    ▼
┌─────────────────────────────────────────────┐
│  task_parser.preprocess_input               │
│  ├─ split_tasks                             │
│  ├─ recurring.parse_recurring_rule          │  → expand 12 weeks
│  ├─ extract_date  (regex)                   │
│  └─ extract_time  (regex, separate module)  │
│  Returns: (resolved, unresolved, pending_recurring)
└─────────────────────────────────────────────┘
    │                  │                  │
    │ resolved         │ unresolved       │ pending_recurring
    │                  ▼                  │
    │      ┌─────────────────────┐        │
    │      │  ai_client.analyze  │        │
    │      │  + provider routing │        │
    │      └──────────┬──────────┘        │
    ▼                 ▼                   │
   merge ─────────────────────────────────┤
                      │                   │
                      ▼                   ▼
              calendar_db.write_tasks   recurring.register_rule
                      │                  (only on user confirm)
                      ▼
              DesktopCal calendar.db
```

### Key modules

| Module | Purpose |
|--------|---------|
| `main.py` | Entry point; routes CLI vs GUI, redirects GUI exe with CLI args to the CLI exe |
| `cli.py` | Click-based CLI (add/today/next/done/undo/backup/restore/...) |
| `ui.py` | Tkinter floating input window, theme-aware |
| `tray.py` | pystray icon + menu (Templates submenu, Theme submenu, Auto-start, Undo) |
| `setup_wizard.py` | First-run BYOK Tkinter wizard (provider picker, masked key, Test button) |
| `task_parser.py` | Splits multi-task input, runs date extraction (Chinese + English) |
| `time_parser.py` | Time-of-day extraction (24h, 12h+AM/PM, 中文 with periods, ranges) |
| `recurring.py` | Weekly/monthly rule parsing + 12-week pre-expansion + startup top-up |
| `ai_client.py` | Cross-provider orchestration: provider override, auto-fallback, prompt building |
| `providers/` | `LLMProvider` ABC + `OpenAICompatibleProvider` base + 10 concrete providers (Gemini / OpenAI / Claude / Grok / Mistral / DeepSeek / Kimi / Qwen / GLM / OpenRouter) + factory |
| `calendar_db.py` | SQLite reads/writes against DesktopCal's schema; LIKE-escape, lock retries |
| `last_op.py` | Records the most recent batch for one-deep undo |
| `templates.py` | 5 built-in templates + user-defined; tray submenu |
| `backup.py` | Schema-versioned full-state JSON export / restore |
| `theme.py` | Light + dark palette tokens; system-pref resolution |
| `history.py` | Interaction logging + behavioral pattern summary for prompts |
| `retry_queue.py` | Offline cache of failed AI requests; retried on startup or via CLI |
| `config_manager.py` | `config.json` load/save; interactive setup |
| `profile_manager.py` | `profile.md` load/edit |
| `logger.py` | Rotating file handler under `%APPDATA%\CalendarTaskAI\logs\` |
| `constants.py` | Centralized paths + DEFAULT_CONFIG |

---

## Troubleshooting

**API key error / "Not configured"**
Run `python main.py config setup` (or open the GUI for the wizard) and re-enter the key.

**Hotkey not working**
- Confirm `keyboard` is installed (`pip show keyboard`).
- Try running as administrator (Windows blocks global hotkey registration for some apps without admin).
- Change the hotkey in `config.json`: `"hotkey": "ctrl+shift+t"`.

**Database locked**
Close DesktopCal momentarily; the app retries 3 times with a 0.5 s backoff but can't write while another process holds an exclusive lock.

**Tasks appear but DesktopCal doesn't show them**
DesktopCal caches its in-memory view. Switch to another month and back. Or set `auto_restart_desktopcal: true`.

**Tray icon doesn't appear**
Pillow + pystray must be installed (`pip install pillow pystray`). Expand the system tray's hidden-icons area; Windows often hides new icons.

**API rate-limit / quota exhausted**
The failed request is saved to `pending.json` and retried on next startup. Or run `python main.py retry` after switching to a different provider / waiting out the quota.

**Bundle exe won't launch**
Right-click `CalendarTaskAI.exe` → Properties → check "Unblock" if present (Windows zone-of-origin protection). Confirm Windows version is 10 or later.

**Where do logs go?**
`%APPDATA%\CalendarTaskAI\logs\app.log`. Rotated at 1 MB, 5 backups.

---

## Contributing

Pull requests welcome. The repo follows conventional commits (`feat:` / `fix:` / `refactor:` / `test:` / `docs:` / `chore:`) and runs the full test suite on every release tag.

To run tests:

```powershell
pip install -r requirements-dev.txt
pytest tests/
```

To build a release locally:

```powershell
python build_release.py
```

---

## License & Acknowledgments

MIT. See [LICENSE](LICENSE).

CalendarTaskAI is an **unofficial** plugin for DesktopCal; it is not affiliated with or endorsed by the DesktopCal authors.

Built on:
- [DesktopCal](https://www.desktopcal.com/), the calendar app this plugin writes to.
- The ten LLM providers it supports: Google Gemini, OpenAI, Anthropic Claude, xAI Grok, Mistral AI, DeepSeek, Moonshot Kimi, Alibaba Qwen, Zhipu GLM, and OpenRouter.
- Open-source dependencies that do the heavy lifting: pystray, Pillow, keyboard, click, google-genai, PyInstaller.
