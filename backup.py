"""Full-state backup and restore.

A backup captures everything the user could lose by reinstalling: config
(API keys redacted), profile, interaction history, templates, recurring
rules (when feature is implemented), and a wide window of tasks from the
DesktopCal database.

The format is a single JSON object:

    {
      "schema_version": 1,
      "created_at": "2026-05-05T...",
      "app_version": "0.2.0",
      "config": { ... API keys replaced with REDACTED_TOKEN ... },
      "profile": "<markdown text>",
      "history": { interactions, modifications, operations_count },
      "templates": [ {name, text, builtin?}, ... ],
      "recurring": [ ... rules ... ],
      "tasks": { "YYYY-MM-DD": [ {text, done}, ... ] }
    }

Restore semantics:
  * Profile, history, templates, recurring: completely overwritten.
  * Config: ONLY non-key fields are restored unless --overwrite-config is
    set. API keys are never restored from the backup (they aren't there).
  * Tasks: APPENDED to the DB (calendar_db.write_tasks behavior).
    Restoring on top of an existing populated DB will create duplicates.
    Phase 3a accepts this; deduplication is a Phase-4-or-later concern.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta

from constants import (
    APP_VERSION,
    CONFIG_PATH,
    HISTORY_PATH,
    PROFILE_PATH,
    RECURRING_PATH,
    TEMPLATES_PATH,
)
from logger import get_logger

log = get_logger(__name__)

REDACTED_TOKEN = "*** REDACTED ***"
SCHEMA_VERSION = 1

# How wide a task window to back up: 1 year past, 1 year future. Beyond
# this and DesktopCal's database starts to feel slow on large calendars.
_TASK_WINDOW_DAYS = 365


def create_backup(reference_date: date | None = None) -> dict:
    """Build an in-memory backup dict (caller writes it to disk)."""
    if reference_date is None:
        reference_date = date.today()

    backup: dict = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now().isoformat(),
        "app_version": APP_VERSION,
    }

    backup["config"] = _redacted_config()

    backup["profile"] = _read_text(PROFILE_PATH, default="")
    backup["history"] = _read_json(HISTORY_PATH, default={
        "interactions": [], "modifications": [], "operations_count": 0,
    })
    backup["templates"] = _read_json(TEMPLATES_PATH, default=[])
    backup["recurring"] = _read_json(RECURRING_PATH, default=[])

    # Tasks: ±1 year window
    from calendar_db import get_tasks_in_range
    start = (reference_date - timedelta(days=_TASK_WINDOW_DAYS)).isoformat()
    end = (reference_date + timedelta(days=_TASK_WINDOW_DAYS)).isoformat()
    try:
        backup["tasks"] = get_tasks_in_range(start, end)
    except Exception:
        log.exception("Backup: failed to read tasks")
        backup["tasks"] = {}

    return backup


def restore_backup(backup: dict, *, overwrite_config: bool = False) -> dict:
    """Apply `backup` to local state. Returns counts dict for reporting."""
    if not isinstance(backup, dict):
        raise ValueError("Backup must be a JSON object")
    if backup.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported backup schema_version: {backup.get('schema_version')!r} "
            f"(expected {SCHEMA_VERSION})"
        )

    counts = {"profile": 0, "history": 0, "templates": 0, "recurring": 0, "tasks": 0}

    if "profile" in backup:
        _write_text(PROFILE_PATH, backup["profile"])
        counts["profile"] = 1

    if "history" in backup:
        _write_json(HISTORY_PATH, backup["history"])
        counts["history"] = 1

    if "templates" in backup:
        _write_json(TEMPLATES_PATH, backup["templates"])
        counts["templates"] = 1

    if "recurring" in backup:
        _write_json(RECURRING_PATH, backup["recurring"])
        counts["recurring"] = 1

    if overwrite_config and "config" in backup:
        _restore_config_preserving_keys(backup["config"])

    if "tasks" in backup:
        counts["tasks"] = _restore_tasks(backup["tasks"])

    log.info("Restore complete: %s", counts)
    return counts


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _redacted_config() -> dict:
    """Return the config with any API-key field replaced by REDACTED_TOKEN."""
    from config_manager import load_config
    cfg = load_config()
    redacted = dict(cfg)
    for key in cfg:
        # All known keys ending with "api_key" carry secrets.
        if key.endswith("api_key") and cfg[key]:
            redacted[key] = REDACTED_TOKEN
    return redacted


def _restore_config_preserving_keys(incoming: dict) -> None:
    """Apply backup config but keep existing local API keys intact.

    Backups never contain real keys (they're redacted at backup time), so
    blindly applying `incoming` would wipe the user's keys. We merge the
    backup over the current config and then restore the original key
    values for any redacted entries.
    """
    from config_manager import load_config, save_config

    current = load_config()
    merged = dict(incoming)
    for key, value in incoming.items():
        if key.endswith("api_key") and value == REDACTED_TOKEN:
            merged[key] = current.get(key, "")
    save_config(merged)


def _restore_tasks(tasks_by_date: dict) -> int:
    """Append `tasks_by_date` to the calendar DB. Returns task count written."""
    from calendar_db import write_tasks

    items: list[dict] = []
    for date_str, task_list in tasks_by_date.items():
        for t in task_list:
            text = t.get("text", "")
            if not text:
                continue
            # Re-encode done state: write_tasks treats text verbatim, so
            # prepend [+] for done tasks to match DesktopCal's convention.
            if t.get("done"):
                text = f"[+]{text}"
            items.append({"date": date_str, "task": text})

    if not items:
        return 0
    return write_tasks(items)


def _read_text(path: str, *, default: str) -> str:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        log.exception("Backup: failed to read %s", path)
        return default


def _read_json(path: str, *, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        log.exception("Backup: failed to read JSON %s", path)
        return default


def _write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _write_json(path: str, value) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
