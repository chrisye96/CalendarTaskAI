# CalendarTaskAI

**AI-Powered Task Scheduling for DesktopCal** (unofficial plugin)

CalendarTaskAI is an intelligent task scheduling assistant that integrates with [DesktopCal](https://www.desktopcal.com/) (a popular desktop calendar application). It uses a **deterministic-first approach**: explicit dates are parsed using regex and rules (no AI needed), while tasks without dates are intelligently scheduled by an LLM based on your profile, habits, and existing workload.

> **BYOK (Bring Your Own Key).** CalendarTaskAI does not ship with any API access. You configure your own Gemini or DeepSeek key on first launch; the key is stored only on your machine in `%APPDATA%\CalendarTaskAI\data\config.json`.

---

## Features

- **System Tray Integration** - Runs quietly in your system tray with a global hotkey (`Ctrl+Alt+Space`) for quick task entry
- **Macaron Light Theme UI** - Clean, modern floating window with pastel light blue theme (dark mode coming in a later release)
- **AI-Powered Task Analysis** - Pluggable LLM backend (Gemini today, DeepSeek next) for intelligent task scheduling when dates aren't explicitly specified
- **Deterministic Date Parsing** - Regex-based parsing for explicit dates (today, tomorrow, 3月25日, next Monday, etc.) - no LLM call needed
- **Smart Learning System** - Learns from your behavior: tracks accepted/rejected suggestions, task modifications, and satisfaction ratings
- **Offline Cache with Auto-Retry** - Failed API requests are saved locally and automatically retried on next startup
- **Full CLI Interface** - Complete command-line interface for all operations
- **Auto-Start on Boot** - Optional Windows startup integration

---

## Prerequisites

- **Python 3.10+** (3.12 recommended)
- **Windows OS** (uses Windows-specific features like registry for auto-start)
- **DesktopCal** installed (with its SQLite database)
- **An LLM API key** of your own:
  - [Google Gemini](https://aistudio.google.com/apikey) (free tier available)
  - or [DeepSeek](https://platform.deepseek.com/api_keys)

---

## Installation

1. **Navigate to the project directory:**
   ```powershell
   cd "$env:APPDATA\CalendarTaskAI"
   ```

2. **Create a virtual environment (recommended):**
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

   Required packages:
   - `google-genai` - Gemini AI SDK (new unified SDK, replaces deprecated `google-generativeai`)
   - `pystray` - System tray icon
   - `Pillow` - Image processing for tray icon
   - `keyboard` - Global hotkey support
   - `click` - CLI framework

---

## LLM Providers

CalendarTaskAI is provider-agnostic. The active backend is chosen by the `llm_provider` field in `config.json`. New providers plug in by subclassing `providers.LLMProvider`.

### Routing model

For new users, **Gemini is the default**. DeepSeek is opt-in: configure `deepseek_api_key` and you unlock both an automatic fallback and two manual escape hatches.

```
                   ┌───────────────┐
   user submits ─► │    Gemini     │ ── success ──► confirm view
                   └───────┬───────┘
                           │ on error (network, 4xx, 5xx, timeout)
                           │ AND DeepSeek configured
                           ▼
                   ┌───────────────┐
                   │ DeepSeek-flash│ ── auto fallback (no user action)
                   └───────────────┘

   confirm view buttons (visible when DeepSeek is configured):
     [Re-run · DeepSeek flash]   alternative model, same tier
     [Re-run · DeepSeek Pro]     escalate to the smarter tier for complex inputs
```

Properties:
- **Pro is never automatic.** It only runs when the user clicks the Pro button, so there are no surprise charges.
- **Manual buttons disable the auto-fallback.** When you explicitly pick a provider via the buttons, errors surface directly so you can react. Auto-fallback only applies to the default Gemini path.
- **Default-DeepSeek users** still see both buttons in the confirm view (re-run flash for a fresh attempt, Pro to escalate).

| Provider | Default model | Auto-fallback target | Tiered? |
|----------|--------------|---------------------|---------|
| `gemini` | `gemini-3.1-flash-lite-preview` | DeepSeek-flash (when configured) | No |
| `deepseek` | `deepseek-v4-flash` for ≤ `deepseek_pro_threshold` tasks (default 5), `deepseek-v4-pro` above | None | Yes (manual via Pro button) |

## Configuration

### First-Time Setup (GUI)

The first time you run `python main.py` (GUI mode), a Tkinter setup wizard opens:

1. Pick a provider — Gemini (free tier) or DeepSeek.
2. Click "Get a {provider} API key →" to open the provider's key page in your browser.
3. Paste the key into the masked field.
4. (Recommended) Click **Test** to verify the key works. The wizard makes a tiny live call and reports ✓ or an error.
5. Click **Save**.

Your key is saved to `%APPDATA%\CalendarTaskAI\data\config.json` and never leaves your machine. To change it later, click `Config` in the tray menu (or edit the JSON directly).

### CLI Setup

If you prefer the terminal, run:

```powershell
python main.py config setup
```

This walks through the same fields with prompts. Press Enter to skip a field, or type `q` to save and exit.

### Manual Configuration

Edit `%APPDATA%\CalendarTaskAI\data\config.json` directly:

```json
{
  "llm_provider": "gemini",
  "gemini_api_key": "your-key-here",
  "gemini_model": "gemini-3.1-flash-lite-preview",
  "deepseek_api_key": "",
  "deepseek_model_flash": "deepseek-v4-flash",
  "deepseek_model_pro": "deepseek-v4-pro",
  "deepseek_endpoint": "https://api.deepseek.com/v1",
  "hotkey": "ctrl+alt+space",
  "db_path": "",
  "auto_start": false,
  "retry_on_startup": true,
  "auto_restart_desktopcal": false,
  "request_timeout_sec": 30,
  "rating_interval": 20
}
```

> **Note:** Leave `db_path` empty for auto-detection (`%APPDATA%\CalendarTask\Db\calendar.db`), or specify a custom path.

| Field | Description |
|-------|-------------|
| `llm_provider` | `"gemini"` or `"deepseek"` |
| `gemini_api_key` / `deepseek_api_key` | API key for the chosen provider (BYOK) |
| `gemini_model` | Gemini model name. If the model doesn't exist, the error surfaces directly — no silent fallback (deliberate, so misconfigurations are visible) |
| `deepseek_model_flash` / `_pro` | DeepSeek "fast" and "smart" tiers; the app uses pro for inputs above `deepseek_pro_threshold` unresolved tasks |
| `hotkey` | Global hotkey to open the task input window |
| `db_path` | Full path to DesktopCal's SQLite database file (empty = auto-detect) |
| `auto_start` | Start CalendarTaskAI when Windows boots |
| `retry_on_startup` | Retry failed requests automatically on startup |
| `auto_restart_desktopcal` | **Off by default.** When on, CalendarTaskAI force-kills and restarts DesktopCal after writing tasks. Convenient but may discard unsaved state in DesktopCal's other panels. |
| `request_timeout_sec` | Per-call LLM API timeout in seconds (default 30) |
| `rating_interval` | Prompt for satisfaction rating every N operations |

### View Current Configuration

```powershell
python main.py config show
```

---

## Personal Profile Setup

The profile (`data/profile.md`) helps the AI understand your work habits, preferences, and scheduling rules for better task allocation.

### Edit Profile

```powershell
python main.py profile edit
```

This opens the profile in your default text editor.

### Profile Structure

```markdown
# Personal Profile

## Career
- Role: Software Developer
- Industry: Technology
- Current projects: CalendarTaskAI, Web App

## Skills
- Primary skills: Python, JavaScript
- Learning: Machine Learning

## Work Habits
- Preferred working hours: 9 AM - 6 PM
- Most productive time: Morning
- Break preferences: Pomodoro technique

## Interests & Hobbies
- Reading, Gaming

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

### Scheduling Rules Section

The **Scheduling Rules** section is particularly important. Define your personal rules here, and the AI will follow them when deciding which dates to assign tasks:

- `No work tasks on weekends` - AI will only schedule work tasks Mon-Fri
- `Max 3 tasks per workday` - AI will spread tasks if a day is overloaded
- `Programming tasks in the morning` - AI considers task type when scheduling
- `Exercise on Mon/Wed/Fri` - AI will schedule exercise-related tasks on these days

---

## How to Start

### GUI Mode (Recommended)

Start with the system tray icon and global hotkey:
```powershell
python main.py
```

To run without a console window (silent mode):
```powershell
pythonw main.py
```
> **Tip:** Use `pythonw` for a cleaner experience - the app runs entirely from the system tray without showing a console window.

On startup:
1. Configuration is validated (setup wizard runs if not configured)
2. Pending failed requests are automatically retried (if enabled)
3. System tray icon appears
4. Global hotkey is registered

### CLI Mode

Run specific commands directly:
```powershell
python main.py <command> [options]
```

> **Note:** CLI commands can be used from a separate terminal window while the GUI is running. This allows you to quickly query tasks (`python main.py today`) or add tasks via command line without interrupting the GUI.

---

## Usage Guide

### GUI Mode

1. **Open Task Input Window**
   - Press `Ctrl+Alt+Space` (or your configured hotkey)
   - Or right-click tray icon → "Add Task"

2. **Enter Tasks**
   - Type your tasks in the text area
   - One task per line, or use separators (see Task Input Format)
   - **Buttons available:**
     - **Clear** - Clear the input text
     - **Paste** - Paste from clipboard
   - Press `Ctrl+Enter` or click "Submit"

3. **Review AI Allocation**
   - The AI analyzes your input and proposes dates
   - Review the allocation table
   - **Buttons available:**
     - **Edit** - Go back to edit your input
     - **Copy** - Copy the allocation result to clipboard
   - Click "Confirm" to write to calendar, or "Cancel" to discard

4. **Rating (Optional)**
   - Every 10 operations, you'll be asked to rate satisfaction (1-5 stars)
   - This helps the AI learn your preferences

### Tray Icon Menu

The tray icon features a macaron blue background with dark "CT" text, matching the app's light theme.

Right-click the tray icon for:
- **Add Task** - Open input window
- **Add from template ▶** - Pre-fill the input with one of the saved templates (5 ship out of the box: Standup, 周报, Sprint planning, 健身计划, 读书清单; edit `data/templates.json` to add your own)
- **Today's Tasks** - View tasks for today
- **Undo last add** - Reverses the most recent add (greyed out when there's nothing to undo)
- **Retry Pending** - Manually retry failed requests
- **Config** - Open config.json in editor
- **Profile** - Open profile.md in editor
- **Auto Start** - Toggle Windows startup
- **Quit** - Exit the application

### CLI Commands

| Command | Description | Example |
|---------|-------------|---------|
| `add [TEXT]` | Add tasks using AI analysis | `python main.py add "买菜 明天"` |
| `profile [ACTION]` | View, edit, or reset profile | `python main.py profile edit` |
| `config [ACTION]` | View or modify configuration | `python main.py config show` |
| `list [DATE]` | List tasks for a date/range | `python main.py list this-week` |
| `today` | Show today's tasks | `python main.py today` |
| `next [N]` | Show tasks for the next N days (default 7) | `python main.py next 14` |
| `done KEYWORD` | Mark matching tasks as done | `python main.py done "买菜"` |
| `undone KEYWORD` | Mark matching tasks as undone | `python main.py undone "买菜"` |
| `delete KEYWORD` | Delete matching tasks | `python main.py delete "旧任务"` |
| `move KEYWORD DATE` | Move tasks to new date | `python main.py move "会议" 2026-03-25` |
| `search KEYWORD` | Search tasks by keyword | `python main.py search "报告"` |
| `undo` | Reverse the most recent batch of tasks added | `python main.py undo` |
| `backup [--out FILE]` | Export config (keys redacted), profile, history, templates, recurring rules, ±1 year of tasks | `python main.py backup --out my-backup.json` |
| `restore PATH` | Restore from a backup JSON file | `python main.py restore my-backup.json` |
| `export [OPTIONS]` | Export tasks to stdout | `python main.py export --format md` |
| `refresh` | Show refresh instructions | `python main.py refresh` |
| `retry` | Retry all pending requests | `python main.py retry` |

### CLI Examples

```powershell
# Add tasks interactively (prompts for input)
python main.py add

# Add tasks directly
python main.py add "明天开会讨论项目进度"
python main.py add "周五前完成报告; 下周一提交材料"

# List tasks
python main.py list today
python main.py list tomorrow
python main.py list this-week
python main.py list this-month
python main.py list 2026-03-25

# Manage tasks
python main.py done "报告"          # Mark as done
python main.py undone "报告"        # Unmark as done
python main.py move "会议" 2026-03-30  # Move to March 30
python main.py delete "取消的任务"    # Delete task

# Export tasks
python main.py export --format md --start 2026-03-01 --end 2026-03-31 > march_tasks.md

# Configuration
python main.py config setup         # Interactive setup
python main.py config show          # View current config
python main.py config set hotkey "ctrl+shift+t"  # Change single setting
```

---

## Task Input Format

### Supported Separators

Tasks can be separated by:
- **Newlines** - One task per line
- **Semicolons** - `任务1; 任务2` or `任务1；任务2`
- **Chinese enumeration comma** - `任务1、任务2、任务3`

> **Note:** Regular commas (`,`, `，`) and spaces are NOT used as separators to avoid accidentally splitting task descriptions.

### Supported Date Formats

**Chinese Relative Dates:**
- `今天`, `今日`, `今晚` - Today
- `明天`, `明日` - Tomorrow
- `后天` - Day after tomorrow
- `大后天` - 3 days from now
- `下周`, `下周一` ~ `下周日` - Next week / Next Monday~Sunday
- `这周一` ~ `这周日`, `这周末` - This week's Monday~Sunday, this weekend
- `下个月` - Next month (1st day)
- `这个月`, `月初` - This month
- `月底` - End of month

**Chinese Day of Week:**
- `周一` ~ `周日`, `周天` - Monday ~ Sunday
- `星期一` ~ `星期天` - Monday ~ Sunday
- `礼拜一` ~ `礼拜天` - Monday ~ Sunday

**Relative Expressions:**
- `3天后`, `三天后` - In 3 days
- `2周后`, `两周后` - In 2 weeks
- `1个月后` - In 1 month

**Short Dates (without year):**
- `3月25日`, `3月25` - March 25
- `0325` - March 25 (MMDD format)
- `3.25`, `3/25`, `3-25` - March 25

**Full Dates:**
- `2026年3月25日` - March 25, 2026
- `2026-03-25` - ISO format
- `2026/03/25`, `2026.03.25` - Alternative formats

**English Dates:**
- `today`, `tonight` - Today
- `tomorrow` - Tomorrow
- `next week`, `next monday` ~ `next sunday` - Next week/day
- `in 3 days`, `in 2 weeks` - Relative
- `end of month` - End of month

### Supported Time-of-Day Formats

Tasks can include a time hint that gets prefixed onto the task text as `[HH:MM]` (single time) or `[HH:MM-HH:MM]` (range). DesktopCal displays the prefix verbatim.

| You type | Becomes |
|----------|---------|
| `9点开会` | `[09:00] 开会` |
| `9点半开会` | `[09:30] 开会` |
| `9点45分会议` | `[09:45] 会议` |
| `上午9点开会` | `[09:00] 开会` |
| `下午3点开会` | `[15:00] 开会` |
| `晚上9点睡觉` | `[21:00] 睡觉` |
| `9-10点 开会` | `[09:00-10:00] 开会` |
| `下午3-5点 讨论` | `[15:00-17:00] 讨论` |
| `9:00 daily standup` | `[09:00] daily standup` |
| `3pm meeting` | `[15:00] meeting` |
| `9:00-10:30 review` | `[09:00-10:30] review` |
| `9-11am sprint` | `[09:00-11:00] sprint` |

Time extraction runs after date extraction, so `明天9点开会` resolves to date=tomorrow with task=`[09:00] 开会`. Anything we can't parse confidently is left in the task text untouched (no LLM-generated prefixes — that path was retired to avoid format drift like `[9:00]` without zero-padding).

### Deterministic vs AI Processing

- **Tasks with explicit dates** → Parsed deterministically using regex (no AI call)
- **Tasks without dates** → Sent to Gemini AI for intelligent scheduling based on your profile, existing tasks, and behavioral patterns

**Example:**
```
明天买菜              → Deterministic: assigned to tomorrow
下周一开会            → Deterministic: assigned to next Monday  
完成项目报告          → AI decides: considers workload, urgency, profile rules
```

---

## Database

CalendarTaskAI writes directly to DesktopCal's SQLite database.

**Default Path:**
```
%APPDATA%\CalendarTask\Db\calendar.db
```

This path is configurable via `db_path` in `config.json`.

### Data Format

The database uses DesktopCal's schema:
- **Table:** `item_table`
- **Key field:** `it_unique_id` - Format: `dkcal_mdays_YYYYMMDD` (e.g., `dkcal_mdays_20260325`)
- **Content field:** `it_content` - Tasks separated by `\r\n`
- **Done marker:** Tasks prefixed with `[+]` are marked as completed

**Example content:**
```
Buy groceries
[+]Completed task
Write report
```

### Refreshing DesktopCal

After CalendarTaskAI writes tasks, DesktopCal needs to reload:
- **Switch pages** in DesktopCal (navigate to another month and back)
- **Or restart** DesktopCal

---

## Smart Learning System

CalendarTaskAI learns from your behavior to improve task allocation over time.

### Behavioral Tracking (Automatic)

The system tracks:
- **Task moves** - When you move a task to a different date, it signals the AI assigned the wrong date
- **Task deletions** - Deleted tasks suggest misunderstanding of your intent
- **Completions** - Tasks marked done are positive signals
- **Rejections** - When you cancel an allocation, rejected tasks are recorded

### Interaction History

Every interaction is logged:
- Your input text
- AI's proposed allocation
- Which tasks you accepted/rejected
- Your satisfaction rating

This history is included in future AI prompts for context.

### User-Defined Scheduling Rules

Add rules to the `## Scheduling Rules` section in `profile.md`:
```markdown
## Scheduling Rules
- No work tasks on weekends
- Max 3 tasks per workday
- Programming tasks in the morning
- Exercise on Mon/Wed/Fri
```

### Rating System

Every 10 operations, you're prompted to rate satisfaction (1-5 stars). Low ratings signal the AI to pay more attention to your patterns.

---

## Data Files

All runtime data is stored under `%APPDATA%\CalendarTaskAI\`:

```
%APPDATA%\CalendarTaskAI\
├─ data\                  user data (config, profile, history)
│   ├─ config.json
│   ├─ profile.md
│   ├─ history.json
│   └─ pending.json
└─ logs\
    └─ app.log            rotating log (1 MB × 5)
```

This means the same install can run from `%APPDATA%`, `source/repos/`, or a frozen exe and read the same data. Source code itself does not write to its own directory.

| File | Description | Auto-generated |
|------|-------------|----------------|
| `config.json` | Configuration settings | Yes (on first run) |
| `profile.md` | Personal profile and rules | Yes (template) |
| `history.json` | Interaction history and modifications | Yes |
| `pending.json` | Offline retry queue for failed requests | Yes |

---

## Architecture Overview

### Module Responsibilities

| Module | Purpose |
|--------|---------|
| `main.py` | Entry point, routes to GUI or CLI mode |
| `cli.py` | Command-line interface using Click framework |
| `ui.py` | Tkinter floating window for task input |
| `tray.py` | System tray icon and menu management |
| `task_parser.py` | Deterministic date extraction using regex |
| `ai_client.py` | Gemini API integration and prompt building |
| `calendar_db.py` | SQLite operations for DesktopCal database |
| `profile_manager.py` | Profile loading and editing |
| `config_manager.py` | Configuration management |
| `history.py` | Interaction logging and behavioral analysis |
| `retry_queue.py` | Offline cache for failed API requests |
| `constants.py` | Shared constants and paths |

### Processing Flow

```
User Input
    │
    ▼
┌─────────────────────────────────────────────┐
│  task_parser.py (Deterministic)             │
│  ├─ Split tasks by separators               │
│  ├─ Extract dates using regex patterns      │
│  └─ Output: resolved[] + unresolved[]       │
└─────────────────────────────────────────────┘
    │
    ├── resolved[] ──────────────────────────────┐
    │   (tasks with explicit dates)              │
    │                                            │
    ▼                                            │
┌─────────────────────────────────────────────┐  │
│  ai_client.py (Only if unresolved exists)   │  │
│  ├─ Build prompt with profile, history      │  │
│  ├─ Call Gemini API                         │  │
│  └─ Parse JSON response                     │  │
└─────────────────────────────────────────────┘  │
    │                                            │
    ▼                                            │
┌─────────────────────────────────────────────┐  │
│  Merge Results                              │◄─┘
│  resolved[] + ai_results[]                  │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│  calendar_db.py                             │
│  └─ Write to DesktopCal SQLite database     │
└─────────────────────────────────────────────┘
```

### Threading Model

```
┌─────────────────────────────────────────────┐
│  Main Thread (Tkinter mainloop)             │
│  ├─ UI rendering and updates                │
│  ├─ Event handling                          │
│  └─ Database operations                     │
└─────────────────────────────────────────────┘
         │
         │ root.after(0, callback)
         ▼
┌─────────────────────────────────────────────┐
│  Tray Thread (pystray)                      │
│  └─ System tray icon and menu               │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│  Background Thread (per AI call)            │
│  └─ Gemini API calls (non-blocking)         │
└─────────────────────────────────────────────┘
```

---

## Troubleshooting

### API Key Not Set

**Error:** `Error: API key not configured.`

**Solution:** Run `python main.py config setup` and enter your Gemini API key.

### Database Locked

**Error:** `Database Error: database is locked`

**Solution:** 
- Close DesktopCal temporarily
- Wait a moment and retry
- The system has built-in retry logic (3 attempts with 0.5s delay)

### Hotkey Conflict

**Error:** `Failed to register hotkey 'ctrl+alt+space'`

**Solutions:**
- Another application may be using this hotkey
- Change the hotkey: `python main.py config set hotkey "ctrl+shift+t"`
- Run as administrator for global hotkey support

### Hotkey Not Working

**Issue:** Pressing the hotkey does nothing

**Solutions:**
- Ensure `keyboard` module is installed: `pip install keyboard`
- Try running as administrator
- Check if another app is capturing the hotkey

### DesktopCal Not Refreshing

**Issue:** Tasks added but not visible in DesktopCal

**Solution:** Switch to another month and back, or restart DesktopCal. The database is updated immediately, but DesktopCal needs to reload its view.

### API Rate Limits

**Error:** API errors related to rate limiting

**Solution:** 
- Your requests are automatically saved to the retry queue
- Run `python main.py retry` later, or wait for the next startup

### Tray Icon Not Showing

**Issue:** Application starts but no tray icon appears

**Solutions:**
- Ensure `pystray` and `Pillow` are installed
- Check if the system tray area is visible (expand hidden icons)
- Restart the application

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'xxx'`

**Solution:** Install all dependencies:
```powershell
pip install google-genai pystray Pillow keyboard click
```

---

## License

MIT. See [LICENSE](LICENSE).

This is an **unofficial** plugin for DesktopCal; it is not affiliated with or endorsed by the DesktopCal authors.

---

## Acknowledgments

- [DesktopCal](https://www.desktopcal.com/) - The desktop calendar application
- [Google Gemini](https://deepmind.google/technologies/gemini/) - AI model for task analysis
- [pystray](https://github.com/moses-palmer/pystray) - System tray library
- [Click](https://click.palletsprojects.com/) - CLI framework
