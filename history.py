"""Interaction history and behavioral learning system."""
import json
import os
from datetime import datetime
from constants import HISTORY_PATH, DATA_DIR, RATING_INTERVAL, HISTORY_MAX_INTERACTIONS


def _load_history() -> dict:
    """Load history data from file.
    
    Returns:
        Dict with keys: interactions, modifications, operations_count
    """
    if not os.path.exists(HISTORY_PATH):
        return {"interactions": [], "modifications": [], "operations_count": 0}
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure all keys exist
            data.setdefault("interactions", [])
            data.setdefault("modifications", [])
            data.setdefault("operations_count", 0)
            return data
    except (json.JSONDecodeError, IOError):
        return {"interactions": [], "modifications": [], "operations_count": 0}


def _save_history(data: dict):
    """Save history data to file.
    
    Args:
        data: History data dict to save
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def log_interaction(user_input: str, ai_result: list, accepted_tasks: list = None, 
                    rejected_tasks: list = None, rating: int = None) -> str:
    """Log an AI interaction.
    
    Args:
        user_input: What the user typed
        ai_result: Full AI response (list of {date, task})
        accepted_tasks: Tasks user confirmed (subset of ai_result)
        rejected_tasks: Tasks user rejected
        rating: Optional 1-5 rating
    
    Returns:
        The interaction ID (timestamp-based)
    """
    data = _load_history()
    
    interaction = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "timestamp": datetime.now().isoformat(),
        "input": user_input,
        "ai_result": ai_result,
        "accepted": accepted_tasks or ai_result,  # Default: all accepted
        "rejected": rejected_tasks or [],
        "rating": rating
    }
    
    data["interactions"].append(interaction)
    data["operations_count"] += 1
    
    # Trim to max size
    if len(data["interactions"]) > HISTORY_MAX_INTERACTIONS:
        data["interactions"] = data["interactions"][-HISTORY_MAX_INTERACTIONS:]
    
    _save_history(data)
    return interaction["id"]


def log_modification(action: str, task_text: str, details: str = ""):
    """Log a user modification (move, delete, done, undone).
    
    This tracks behavioral signals:
    - "move": user moved a task to different date -> AI may have assigned wrong date
    - "delete": user deleted a task -> AI may have misunderstood
    - "done": user completed a task -> positive signal
    - "undone": user unmarked a task -> may have been prematurely marked
    
    Args:
        action: One of "move", "delete", "done", "undone"
        task_text: The task text that was modified
        details: Additional context (e.g., "from 2024-01-01 to 2024-01-05")
    """
    data = _load_history()
    
    modification = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "task_text": task_text,
        "details": details
    }
    
    data["modifications"].append(modification)
    data["operations_count"] += 1
    
    # Keep last 200 modifications
    if len(data["modifications"]) > 200:
        data["modifications"] = data["modifications"][-200:]
    
    _save_history(data)


def get_recent_interactions(n: int = 15) -> str:
    """Get formatted recent interaction history for prompt context.
    
    Args:
        n: Number of recent interactions to include
    
    Returns:
        Human-readable summary of recent interactions, or empty string if none
    """
    data = _load_history()
    interactions = data["interactions"][-n:]
    
    if not interactions:
        return ""
    
    lines = ["Recent task allocation history:"]
    for inter in interactions:
        ts = inter.get("timestamp", "unknown")[:10]  # Just the date part
        user_input_preview = inter["input"][:80]
        if len(inter["input"]) > 80:
            user_input_preview += "..."
        
        accepted_count = len(inter.get("accepted", []))
        rejected_count = len(inter.get("rejected", []))
        rating = inter.get("rating")
        
        rating_str = f" (rated {rating}/5)" if rating else ""
        rejection_str = f", {rejected_count} rejected" if rejected_count > 0 else ""
        
        lines.append(f"- [{ts}] Input: \"{user_input_preview}\" -> {accepted_count} accepted{rejection_str}{rating_str}")
        
        # Show what was accepted
        for task in inter.get("accepted", [])[:3]:
            lines.append(f"  Assigned: {task.get('date', '?')} - {task.get('task', '?')}")
        
        # Show rejections as important signal
        for task in inter.get("rejected", []):
            lines.append(f"  REJECTED: {task.get('date', '?')} - {task.get('task', '?')}")
    
    return "\n".join(lines)


def get_behavioral_patterns() -> str:
    """Analyze modifications to detect user behavioral patterns.
    
    Returns:
        Human-readable summary of patterns, or empty string if no data
    """
    data = _load_history()
    mods = data["modifications"]
    
    if not mods:
        return ""
    
    # Count action types
    action_counts = {}
    move_details = []
    delete_details = []
    
    for mod in mods:
        action = mod.get("action", "unknown")
        action_counts[action] = action_counts.get(action, 0) + 1
        
        if action == "move":
            move_details.append(mod.get("details", ""))
        elif action == "delete":
            delete_details.append(mod.get("task_text", ""))
    
    lines = ["Observed user behavior patterns:"]
    
    total = sum(action_counts.values())
    for action, count in sorted(action_counts.items(), key=lambda x: -x[1]):
        pct = (count / total * 100) if total > 0 else 0
        lines.append(f"- {action}: {count} times ({pct:.0f}%)")
    
    # Analyze move patterns
    if len(move_details) >= 3:
        lines.append(f"- User has moved {len(move_details)} tasks, suggesting AI date assignments could be improved.")
    
    # Analyze delete patterns
    if len(delete_details) >= 3:
        lines.append(f"- User has deleted {len(delete_details)} AI-assigned tasks, suggesting some tasks were unwanted.")
    
    # Check acceptance rate from interactions
    interactions = data["interactions"]
    if interactions:
        total_proposed = sum(len(i.get("ai_result", [])) for i in interactions)
        total_rejected = sum(len(i.get("rejected", [])) for i in interactions)
        if total_proposed > 0:
            acceptance_rate = ((total_proposed - total_rejected) / total_proposed) * 100
            lines.append(f"- Overall acceptance rate: {acceptance_rate:.0f}% ({total_proposed - total_rejected}/{total_proposed})")
    
    return "\n".join(lines)


def should_ask_rating() -> bool:
    """Check if it's time to ask the user for a rating.
    
    Returns:
        True if operations_count is a multiple of RATING_INTERVAL
    """
    data = _load_history()
    return data["operations_count"] > 0 and data["operations_count"] % RATING_INTERVAL == 0


def save_rating(rating: int, interaction_id: str = None):
    """Save a rating for the most recent or specified interaction.
    
    Args:
        rating: 1-5 satisfaction rating
        interaction_id: Optional specific interaction ID; if None, rates the most recent
    """
    data = _load_history()
    
    if interaction_id:
        for inter in reversed(data["interactions"]):
            if inter["id"] == interaction_id:
                inter["rating"] = rating
                break
    elif data["interactions"]:
        data["interactions"][-1]["rating"] = rating
    
    _save_history(data)


def get_feedback_summary() -> str:
    """Summarize user ratings for prompt context.
    
    Returns:
        Human-readable summary of ratings, or empty string if no ratings
    """
    data = _load_history()
    
    ratings = [i["rating"] for i in data["interactions"] if i.get("rating") is not None]
    
    if not ratings:
        return ""
    
    avg = sum(ratings) / len(ratings)
    recent = ratings[-5:]
    recent_avg = sum(recent) / len(recent) if recent else 0
    
    lines = [
        f"User has rated {len(ratings)} interactions.",
        f"Average satisfaction: {avg:.1f}/5",
        f"Recent trend ({len(recent)} ratings): {recent_avg:.1f}/5",
    ]
    
    if recent_avg < 3:
        lines.append("NOTE: Recent satisfaction is LOW. Pay extra attention to user preferences and patterns.")
    elif recent_avg >= 4:
        lines.append("User is generally satisfied with allocations.")
    
    return "\n".join(lines)
