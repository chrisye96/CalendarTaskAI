"""Offline cache for failed API requests."""
import json
import os
from datetime import datetime
from constants import PENDING_PATH, DATA_DIR


def save_pending(user_input: str, timestamp: str = None):
    """Save a failed request to pending queue.
    
    Args:
        user_input: The user's task input that failed to process
        timestamp: Optional ISO timestamp, defaults to current time
    """
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    
    pending = load_pending()
    pending.append({"input": user_input, "timestamp": timestamp})
    
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PENDING_PATH, "w", encoding="utf-8") as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)


def load_pending() -> list[dict]:
    """Load pending requests list.
    
    Returns:
        List of {"input": str, "timestamp": str} dicts
    """
    if not os.path.exists(PENDING_PATH):
        return []
    try:
        with open(PENDING_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def remove_pending(index: int):
    """Remove a pending request by index.
    
    Args:
        index: Zero-based index of the item to remove
    """
    pending = load_pending()
    if 0 <= index < len(pending):
        pending.pop(index)
        with open(PENDING_PATH, "w", encoding="utf-8") as f:
            json.dump(pending, f, ensure_ascii=False, indent=2)


def clear_pending():
    """Clear all pending requests."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PENDING_PATH, "w", encoding="utf-8") as f:
        json.dump([], f)


def retry_all(config: dict) -> dict:
    """Retry all pending requests.
    
    Args:
        config: Config dict with API keys and settings
    
    Returns:
        {
            "success": int,  # Number of successfully processed requests
            "failed": int,   # Number of still-failed requests
            "results": [     # Details for each request
                {"input": str, "tasks": list, "written": int} or
                {"input": str, "error": str}
            ]
        }
    """
    from ai_client import analyze_tasks
    from calendar_db import write_tasks
    
    pending = load_pending()
    if not pending:
        return {"success": 0, "failed": 0, "results": []}
    
    success = 0
    failed = 0
    results = []
    remaining = []
    
    for item in pending:
        try:
            tasks, pending_recurring = analyze_tasks(item["input"], config)
            written = write_tasks(tasks)
            # Register any recurring rules that were detected on the
            # original (failed) attempt; they weren't persisted then
            # because registration is gated on a successful write.
            if pending_recurring:
                from recurring import register_rule
                for rule in pending_recurring:
                    register_rule(rule)
            results.append({"input": item["input"], "tasks": tasks, "written": written})
            success += 1
        except Exception as e:
            remaining.append(item)
            failed += 1
            results.append({"input": item["input"], "error": str(e)})
    
    # Save remaining failed ones
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PENDING_PATH, "w", encoding="utf-8") as f:
        json.dump(remaining, f, ensure_ascii=False, indent=2)
    
    return {"success": success, "failed": failed, "results": results}
