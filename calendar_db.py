"""
Calendar database operations module.

Handles all SQLite operations for reading/writing to DesktopCal's calendar.db.
"""

import sqlite3
import time
from datetime import datetime, date, timedelta
from typing import Optional

from logger import get_logger

log = get_logger(__name__)


# All LIKE queries in this module use this escape character so that user
# keywords containing `%` or `_` are matched literally instead of acting as
# SQL wildcards. Searching "100%" should not match every row in the table.
_LIKE_ESCAPE = "\\"


def _escape_like(keyword: str) -> str:
    """Escape SQL LIKE wildcards in a user-supplied keyword."""
    return (
        keyword
        .replace(_LIKE_ESCAPE, _LIKE_ESCAPE + _LIKE_ESCAPE)
        .replace("%", _LIKE_ESCAPE + "%")
        .replace("_", _LIKE_ESCAPE + "_")
    )


def _get_db_path() -> str:
    """Get configured db_path, falling back to default."""
    try:
        from constants import DEFAULT_DB_PATH
        from config_manager import get_config
        return get_config("db_path") or DEFAULT_DB_PATH
    except Exception:
        import os
        return os.path.join(os.getenv('APPDATA', ''), 'CalendarTask', 'Db', 'calendar.db')


def _execute_with_retry(func, max_retries: int = 3, delay: float = 0.5):
    """Execute a database function with retry logic for handling locks.
    
    Args:
        func: Function to execute
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
        
    Returns:
        Result of the function
        
    Raises:
        sqlite3.OperationalError: If all retries fail
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            return func()
        except sqlite3.OperationalError as e:
            last_error = e
            if "locked" in str(e).lower() and attempt < max_retries - 1:
                time.sleep(delay)
            else:
                raise
    raise last_error


def _date_to_unique_id(date_str: str) -> str:
    """Convert YYYY-MM-DD to dkcal_mdays_YYYYMMDD.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        
    Returns:
        Unique ID string in dkcal_mdays_YYYYMMDD format
    """
    return f"dkcal_mdays_{date_str.replace('-', '')}"


def _unique_id_to_date(unique_id: str) -> str:
    """Convert dkcal_mdays_YYYYMMDD to YYYY-MM-DD.
    
    Args:
        unique_id: Unique ID in dkcal_mdays_YYYYMMDD format
        
    Returns:
        Date string in YYYY-MM-DD format
    """
    # Extract YYYYMMDD part
    date_part = unique_id.replace("dkcal_mdays_", "")
    return f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"


def _date_to_stime(date_str: str) -> int:
    """Convert YYYY-MM-DD to Unix timestamp (seconds, midnight local time).
    
    Args:
        date_str: Date in YYYY-MM-DD format
        
    Returns:
        Unix timestamp in seconds for midnight local time
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return int(dt.timestamp())


def _parse_tasks(content: str) -> list[dict]:
    """Parse it_content into list of task dictionaries.
    
    Args:
        content: Raw content from it_content field
        
    Returns:
        List of {"text": str, "done": bool} dictionaries
    """
    if not content or not content.strip():
        return []
    
    tasks = []
    lines = content.split("\r\n")
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("[+]"):
            tasks.append({
                "text": line[3:].strip(),
                "done": True
            })
        else:
            tasks.append({
                "text": line,
                "done": False
            })
    
    return tasks


def _tasks_to_content(tasks: list[dict]) -> str:
    """Convert list of task dictionaries back to it_content format.
    
    Args:
        tasks: List of {"text": str, "done": bool} dictionaries
        
    Returns:
        Content string with tasks separated by \\r\\n
    """
    lines = []
    for task in tasks:
        if task["done"]:
            lines.append(f"[+]{task['text']}")
        else:
            lines.append(task["text"])
    return "\r\n".join(lines)


def get_user_mid(db_path: str = None) -> str:
    """Detect u_mid from existing records.
    
    Args:
        db_path: Path to calendar.db, uses default if None
        
    Returns:
        The most common u_mid, or '' if no records exist
    """
    if db_path is None:
        db_path = _get_db_path()
    
    def query():
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("""
                SELECT u_mid, COUNT(*) as cnt 
                FROM item_table 
                WHERE u_mid != '' 
                GROUP BY u_mid 
                ORDER BY cnt DESC 
                LIMIT 1
            """)
            row = cursor.fetchone()
            return row[0] if row else ""
    
    return _execute_with_retry(query)


def get_tasks_for_date(date_str: str, db_path: str = None) -> list[dict]:
    """Get tasks for a specific date.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        db_path: Path to calendar.db, uses default if None
        
    Returns:
        List of {"text": str, "done": bool} dictionaries
    """
    if db_path is None:
        db_path = _get_db_path()
    
    unique_id = _date_to_unique_id(date_str)
    
    def query():
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "SELECT it_content FROM item_table WHERE it_unique_id = ?",
                (unique_id,)
            )
            row = cursor.fetchone()
            if row and row[0]:
                return _parse_tasks(row[0])
            return []
    
    return _execute_with_retry(query)


def get_tasks_in_range(start_date: str, end_date: str, db_path: str = None) -> dict:
    """Get tasks for a date range.
    
    Args:
        start_date: Start date in YYYY-MM-DD format (inclusive)
        end_date: End date in YYYY-MM-DD format (inclusive)
        db_path: Path to calendar.db, uses default if None
        
    Returns:
        Dictionary mapping date strings to lists of task dictionaries
        {date_str: [{"text": str, "done": bool}, ...]}
    """
    if db_path is None:
        db_path = _get_db_path()
    
    start_unique = _date_to_unique_id(start_date)
    end_unique = _date_to_unique_id(end_date)
    
    def query():
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("""
                SELECT it_unique_id, it_content 
                FROM item_table 
                WHERE it_unique_id >= ? AND it_unique_id <= ?
                  AND it_unique_id LIKE 'dkcal_mdays_%'
            """, (start_unique, end_unique))
            
            result = {}
            for row in cursor.fetchall():
                unique_id, content = row
                date_str = _unique_id_to_date(unique_id)
                tasks = _parse_tasks(content) if content else []
                if tasks:  # Only include dates that have tasks
                    result[date_str] = tasks
            return result
    
    return _execute_with_retry(query)


def write_tasks(tasks: list[dict], db_path: str = None) -> int:
    """Write tasks to calendar.db.
    
    Uses APPEND strategy: if date already has content, append with \\r\\n.
    
    Args:
        tasks: List of {"date": "YYYY-MM-DD", "task": "text"} dictionaries
        db_path: Path to calendar.db, uses default if None
        
    Returns:
        Number of tasks written
    """
    if db_path is None:
        db_path = _get_db_path()
    
    if not tasks:
        return 0
    
    # Group tasks by date
    tasks_by_date = {}
    for task in tasks:
        date_str = task["date"]
        if date_str not in tasks_by_date:
            tasks_by_date[date_str] = []
        tasks_by_date[date_str].append(task["task"])
    
    # Detect u_mid once
    u_mid = get_user_mid(db_path)
    
    def write():
        count = 0
        with sqlite3.connect(db_path) as conn:
            for date_str, task_texts in tasks_by_date.items():
                unique_id = _date_to_unique_id(date_str)
                stime = _date_to_stime(date_str)
                new_content = "\r\n".join(task_texts)
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Check if record exists
                cursor = conn.execute(
                    "SELECT it_id, it_content FROM item_table WHERE it_unique_id = ? AND u_mid = ?",
                    (unique_id, u_mid)
                )
                row = cursor.fetchone()
                
                if row:
                    # Update existing record
                    it_id, existing_content = row
                    if existing_content and existing_content.strip():
                        updated_content = existing_content + "\r\n" + new_content
                    else:
                        updated_content = new_content
                    
                    conn.execute("""
                        UPDATE item_table 
                        SET it_content = ?, it_mdate = ?
                        WHERE it_id = ?
                    """, (updated_content, now, it_id))
                else:
                    # Insert new record
                    conn.execute("""
                        INSERT INTO item_table 
                        (u_id, pj_id, u_mid, it_unique_id, it_bgcolor, it_content, 
                         it_history, it_appinfo, it_cdate, it_mdate, it_stime, it_mtime, group_id)
                        VALUES (0, 0, ?, ?, '', ?, '', '', ?, ?, ?, 0, '')
                    """, (u_mid, unique_id, new_content, now, now, stime))
                
                count += len(task_texts)
            
            conn.commit()
        return count
    
    return _execute_with_retry(write)


def mark_done(keyword: str, db_path: str = None) -> list[str]:
    """Mark tasks matching keyword as done (add [+] prefix).
    
    Args:
        keyword: Search keyword for case-insensitive partial match
        db_path: Path to calendar.db, uses default if None
        
    Returns:
        List of matched task texts that were marked as done
    """
    if db_path is None:
        db_path = _get_db_path()
    
    keyword_lower = keyword.lower()
    matched = []
    
    def update():
        nonlocal matched
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "SELECT it_id, it_content FROM item_table WHERE it_content LIKE ? ESCAPE '\\'",
                (f"%{_escape_like(keyword)}%",)
            )
            
            for row in cursor.fetchall():
                it_id, content = row
                if not content:
                    continue
                
                tasks = _parse_tasks(content)
                modified = False
                
                for task in tasks:
                    # Match against text without [+] prefix, case-insensitive
                    if keyword_lower in task["text"].lower() and not task["done"]:
                        task["done"] = True
                        matched.append(task["text"])
                        modified = True
                
                if modified:
                    new_content = _tasks_to_content(tasks)
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    conn.execute(
                        "UPDATE item_table SET it_content = ?, it_mdate = ? WHERE it_id = ?",
                        (new_content, now, it_id)
                    )
            
            conn.commit()
        return matched
    
    return _execute_with_retry(update)


def mark_undone(keyword: str, db_path: str = None) -> list[str]:
    """Mark tasks matching keyword as undone (remove [+] prefix).
    
    Args:
        keyword: Search keyword for case-insensitive partial match
        db_path: Path to calendar.db, uses default if None
        
    Returns:
        List of matched task texts that were marked as undone
    """
    if db_path is None:
        db_path = _get_db_path()
    
    keyword_lower = keyword.lower()
    matched = []
    
    def update():
        nonlocal matched
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "SELECT it_id, it_content FROM item_table WHERE it_content LIKE ? ESCAPE '\\'",
                (f"%{_escape_like(keyword)}%",)
            )
            
            for row in cursor.fetchall():
                it_id, content = row
                if not content:
                    continue
                
                tasks = _parse_tasks(content)
                modified = False
                
                for task in tasks:
                    if keyword_lower in task["text"].lower() and task["done"]:
                        task["done"] = False
                        matched.append(task["text"])
                        modified = True
                
                if modified:
                    new_content = _tasks_to_content(tasks)
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    conn.execute(
                        "UPDATE item_table SET it_content = ?, it_mdate = ? WHERE it_id = ?",
                        (new_content, now, it_id)
                    )
            
            conn.commit()
        return matched
    
    return _execute_with_retry(update)


def delete_task(keyword: str, db_path: str = None) -> list[str]:
    """Delete task lines matching keyword.
    
    If removing all lines from a date, keep the record but with empty content.
    
    Args:
        keyword: Search keyword for case-insensitive partial match
        db_path: Path to calendar.db, uses default if None
        
    Returns:
        List of deleted task texts
    """
    if db_path is None:
        db_path = _get_db_path()
    
    keyword_lower = keyword.lower()
    deleted = []
    
    def update():
        nonlocal deleted
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "SELECT it_id, it_content FROM item_table WHERE it_content LIKE ? ESCAPE '\\'",
                (f"%{_escape_like(keyword)}%",)
            )
            
            for row in cursor.fetchall():
                it_id, content = row
                if not content:
                    continue
                
                tasks = _parse_tasks(content)
                remaining = []
                
                for task in tasks:
                    if keyword_lower in task["text"].lower():
                        deleted.append(task["text"])
                    else:
                        remaining.append(task)
                
                if len(remaining) != len(tasks):
                    new_content = _tasks_to_content(remaining)
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    conn.execute(
                        "UPDATE item_table SET it_content = ?, it_mdate = ? WHERE it_id = ?",
                        (new_content, now, it_id)
                    )
            
            conn.commit()
        return deleted
    
    return _execute_with_retry(update)


def move_task(keyword: str, target_date: str, db_path: str = None) -> list[str]:
    """Move tasks matching keyword to target_date.
    
    Remove from source date, append to target date.
    
    Args:
        keyword: Search keyword for case-insensitive partial match
        target_date: Target date in YYYY-MM-DD format
        db_path: Path to calendar.db, uses default if None
        
    Returns:
        List of moved task texts
    """
    if db_path is None:
        db_path = _get_db_path()
    
    keyword_lower = keyword.lower()
    moved = []
    
    def update():
        nonlocal moved
        with sqlite3.connect(db_path) as conn:
            # First, find and remove matching tasks from source dates
            cursor = conn.execute(
                "SELECT it_id, it_content FROM item_table WHERE it_content LIKE ? ESCAPE '\\'",
                (f"%{_escape_like(keyword)}%",)
            )
            
            tasks_to_move = []
            
            for row in cursor.fetchall():
                it_id, content = row
                if not content:
                    continue
                
                tasks = _parse_tasks(content)
                remaining = []
                
                for task in tasks:
                    if keyword_lower in task["text"].lower():
                        tasks_to_move.append(task)
                        moved.append(task["text"])
                    else:
                        remaining.append(task)
                
                if len(remaining) != len(tasks):
                    new_content = _tasks_to_content(remaining)
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    conn.execute(
                        "UPDATE item_table SET it_content = ?, it_mdate = ? WHERE it_id = ?",
                        (new_content, now, it_id)
                    )
            
            # Now add tasks to target date
            if tasks_to_move:
                target_unique_id = _date_to_unique_id(target_date)
                u_mid = get_user_mid(db_path)
                stime = _date_to_stime(target_date)
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Check if target date record exists
                cursor = conn.execute(
                    "SELECT it_id, it_content FROM item_table WHERE it_unique_id = ? AND u_mid = ?",
                    (target_unique_id, u_mid)
                )
                row = cursor.fetchone()
                
                new_task_content = _tasks_to_content(tasks_to_move)
                
                if row:
                    it_id, existing_content = row
                    if existing_content and existing_content.strip():
                        updated_content = existing_content + "\r\n" + new_task_content
                    else:
                        updated_content = new_task_content
                    
                    conn.execute(
                        "UPDATE item_table SET it_content = ?, it_mdate = ? WHERE it_id = ?",
                        (updated_content, now, it_id)
                    )
                else:
                    conn.execute("""
                        INSERT INTO item_table 
                        (u_id, pj_id, u_mid, it_unique_id, it_bgcolor, it_content, 
                         it_history, it_appinfo, it_cdate, it_mdate, it_stime, it_mtime, group_id)
                        VALUES (0, 0, ?, ?, '', ?, '', '', ?, ?, ?, 0, '')
                    """, (u_mid, target_unique_id, new_task_content, now, now, stime))
            
            conn.commit()
        return moved
    
    return _execute_with_retry(update)


def search_tasks(keyword: str, db_path: str = None) -> list[dict]:
    """Search all tasks for keyword.
    
    Args:
        keyword: Search keyword for case-insensitive partial match
        db_path: Path to calendar.db, uses default if None
        
    Returns:
        List of {"date": "YYYY-MM-DD", "text": str, "done": bool} dictionaries
    """
    if db_path is None:
        db_path = _get_db_path()
    
    keyword_lower = keyword.lower()
    results = []
    
    def query():
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                """SELECT it_unique_id, it_content
                   FROM item_table
                   WHERE it_content LIKE ? ESCAPE '\\'
                     AND it_unique_id LIKE 'dkcal_mdays_%'""",
                (f"%{_escape_like(keyword)}%",)
            )
            
            for row in cursor.fetchall():
                unique_id, content = row
                if not content:
                    continue
                
                date_str = _unique_id_to_date(unique_id)
                tasks = _parse_tasks(content)
                
                for task in tasks:
                    if keyword_lower in task["text"].lower():
                        results.append({
                            "date": date_str,
                            "text": task["text"],
                            "done": task["done"]
                        })
        
        return results
    
    return _execute_with_retry(query)


def export_tasks(start_date: str, end_date: str, fmt: str = "md", db_path: str = None) -> str:
    """Export tasks in date range as formatted text.
    
    Args:
        start_date: Start date in YYYY-MM-DD format (inclusive)
        end_date: End date in YYYY-MM-DD format (inclusive)
        fmt: Output format, 'md' for Markdown or 'txt' for plain text
        db_path: Path to calendar.db, uses default if None
        
    Returns:
        Formatted string with tasks
    """
    tasks_by_date = get_tasks_in_range(start_date, end_date, db_path)
    
    if not tasks_by_date:
        return f"No tasks found between {start_date} and {end_date}."
    
    # Sort dates
    sorted_dates = sorted(tasks_by_date.keys())
    
    lines = []
    
    if fmt == "md":
        lines.append(f"# Tasks from {start_date} to {end_date}\n")
        
        for date_str in sorted_dates:
            tasks = tasks_by_date[date_str]
            lines.append(f"## {date_str}\n")
            
            for task in tasks:
                checkbox = "[x]" if task["done"] else "[ ]"
                lines.append(f"- {checkbox} {task['text']}")
            
            lines.append("")  # Empty line between dates
    else:
        lines.append(f"Tasks from {start_date} to {end_date}")
        lines.append("=" * 40)
        lines.append("")
        
        for date_str in sorted_dates:
            tasks = tasks_by_date[date_str]
            lines.append(f"{date_str}")
            lines.append("-" * 20)
            
            for task in tasks:
                status = "[DONE]" if task["done"] else "[    ]"
                lines.append(f"  {status} {task['text']}")
            
            lines.append("")
    
    return "\n".join(lines)
