"""Shared constants and paths for CalendarTaskAI."""
import os

# Source code directory (where this file lives).
# Used for locating bundled resources only - never for runtime data.
APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Runtime data lives under %APPDATA%, independent of source location.
# This way the same data is read whether the app runs from %APPDATA%,
# source/repos/, or a frozen PyInstaller exe.
_APPDATA_ROOT = os.path.join(os.getenv('APPDATA', ''), 'CalendarTaskAI')
DATA_DIR = os.path.join(_APPDATA_ROOT, 'data')
LOG_DIR = os.path.join(_APPDATA_ROOT, 'logs')

# File paths under DATA_DIR
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
PROFILE_PATH = os.path.join(DATA_DIR, "profile.md")
PENDING_PATH = os.path.join(DATA_DIR, "pending.json")
HISTORY_PATH = os.path.join(DATA_DIR, "history.json")
LAST_OP_PATH = os.path.join(DATA_DIR, "last_op.json")
TEMPLATES_PATH = os.path.join(DATA_DIR, "templates.json")
RECURRING_PATH = os.path.join(DATA_DIR, "recurring.json")

# Default database path for DesktopCal
DEFAULT_DB_PATH = os.path.join(os.getenv('APPDATA', ''), 'CalendarTask', 'Db', 'calendar.db')

# Default config. BYOK: API keys are empty by default; users must configure on first run.
DEFAULT_CONFIG = {
    # Provider selection. One of:
    #   "gemini"   - Google Gemini (default; free tier)
    #   "openai"   - ChatGPT
    #   "claude"   - Anthropic Claude
    #   "deepseek" - DeepSeek (cheap, mainland-China-friendly)
    #   "kimi"     - Moonshot AI (mainland-China-friendly, free tier)
    "llm_provider": "gemini",

    # Gemini
    "gemini_api_key": "",
    "gemini_model": "gemini-3.1-flash-lite-preview",

    # OpenAI / ChatGPT
    "openai_api_key": "",
    "openai_model": "gpt-4o",
    "openai_endpoint": "https://api.openai.com/v1",

    # Anthropic Claude
    "claude_api_key": "",
    "claude_model": "claude-sonnet-4-6",
    "claude_endpoint": "https://api.anthropic.com/v1",
    "claude_max_tokens": 2048,  # Anthropic API requires max_tokens

    # DeepSeek (endpoint and pro/flash threshold; api key empty until user configures)
    "deepseek_api_key": "",
    "deepseek_model_flash": "deepseek-v4-flash",
    "deepseek_model_pro": "deepseek-v4-pro",
    "deepseek_endpoint": "https://api.deepseek.com/v1",
    "deepseek_pro_threshold": 5,  # use pro when unresolved task count exceeds this

    # Kimi (Moonshot AI)
    "kimi_api_key": "",
    "kimi_model": "moonshot-v1-32k",
    "kimi_endpoint": "https://api.moonshot.cn/v1",

    # App behavior
    "hotkey": "ctrl+alt+space",
    "db_path": DEFAULT_DB_PATH,
    "auto_start": False,
    "retry_on_startup": True,
    "auto_restart_desktopcal": False,  # off by default: forcibly killing DesktopCal risks data loss
    "request_timeout_sec": 30,
    "rating_interval": 20,
    "theme": "system",  # "light" | "dark" | "system" (follow Windows AppsUseLightTheme)
}

# App info
APP_NAME = "CalendarTaskAI"
APP_VERSION = "1.0.0"
HISTORY_MAX_INTERACTIONS = 50

# Backward compat shim. Code still doing `from constants import RATING_INTERVAL`
# will keep working; new code should read config["rating_interval"] instead so
# users can tune it in config.json.
RATING_INTERVAL = DEFAULT_CONFIG["rating_interval"]
