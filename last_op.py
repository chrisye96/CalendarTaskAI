"""Tracks the most recent batch of tasks added so the user can undo it.

Scope is intentionally one-deep: only the LAST add is undoable. Maintaining a
multi-step history would require reasoning about edits the user made between
operations (mark-as-done, manual delete, recurring-rule expansion); none of
that complexity is justified for "I just typed something I didn't mean to".
"""
from __future__ import annotations

import json
import os
from datetime import datetime

from constants import DATA_DIR, LAST_OP_PATH
from logger import get_logger

log = get_logger(__name__)


def record_last_add(tasks: list[dict]) -> None:
    """Persist the just-written task batch.

    Called by the UI / CLI right after `calendar_db.write_tasks` succeeds.
    `tasks` is a list of `{"date": "YYYY-MM-DD", "task": "..."}` matching
    what was passed to write_tasks.
    """
    if not tasks:
        return
    os.makedirs(DATA_DIR, exist_ok=True)
    payload = {
        "timestamp": datetime.now().isoformat(),
        "tasks": tasks,
    }
    try:
        with open(LAST_OP_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        log.exception("Failed to record last_op")


def peek_last() -> dict | None:
    """Return the recorded last add, or None if no record exists."""
    if not os.path.exists(LAST_OP_PATH):
        return None
    try:
        with open(LAST_OP_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        log.exception("Failed to read last_op")
        return None


def clear() -> None:
    """Remove the last_op record."""
    if os.path.exists(LAST_OP_PATH):
        try:
            os.remove(LAST_OP_PATH)
        except Exception:
            log.exception("Failed to clear last_op")


def undo_last_add() -> tuple[int, str]:
    """Remove the tasks from the last recorded add.

    Tasks are matched by exact text on the recorded date. If the user has
    since marked a task done (e.g. `[+]task` in DesktopCal), the parsed text
    still matches because `_parse_tasks` strips the `[+]` prefix.

    Returns (removed_count, message).
    """
    record = peek_last()
    if not record:
        return 0, "Nothing to undo."

    tasks = record.get("tasks", [])
    if not tasks:
        clear()
        return 0, "Nothing to undo (last record was empty)."

    # Lazy import to avoid a circular dependency at module load.
    from calendar_db import remove_specific_tasks

    try:
        removed = remove_specific_tasks(tasks)
    except Exception as e:
        log.exception("Undo failed during DB write")
        return 0, f"Undo failed: {e}"

    clear()

    if removed == 0:
        return 0, "Last add not found in DB (maybe already removed)."
    return removed, f"Removed {removed} task(s) from the last add."
