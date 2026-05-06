"""Profile management for CalendarTaskAI."""
import os
import sys

from constants import DATA_DIR, PROFILE_PATH


def _ensure_data_dir() -> None:
    """Ensure the data directory exists."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def get_profile_template() -> str:
    """Return the default profile template string.
    
    Returns:
        str: Default profile template in markdown format.
    """
    return """# Personal Profile

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
- Break preferences: 

## Interests & Hobbies
- 

## Scheduling Rules
<!-- Define your personal scheduling rules here. The AI will follow these. -->
<!-- Examples: -->
<!-- - No work tasks on weekends -->
<!-- - Max 3 tasks per workday -->
<!-- - Programming tasks in the morning -->
<!-- - Exercise on Mon/Wed/Fri -->

## Preferences
- Task priority style: (e.g., urgent-first, balanced, deadline-driven)
- Preferred task granularity: (e.g., detailed steps vs high-level goals)
"""


def load_profile() -> str:
    """Read profile.md, return content string.
    
    If profile.md is empty or missing, auto-initialize with the template.
    
    Returns:
        str: Profile content string.
    """
    _ensure_data_dir()
    
    # Check if file exists and has content
    if os.path.exists(PROFILE_PATH):
        try:
            with open(PROFILE_PATH, "r", encoding="utf-8") as f:
                content = f.read()
                if content.strip():
                    return content
        except IOError:
            pass
    
    # Auto-initialize with template if empty or missing
    template = get_profile_template()
    save_profile(template)
    return template


def save_profile(content: str) -> None:
    """Write content to profile.md.
    
    Args:
        content: Profile content to save.
    """
    _ensure_data_dir()
    
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        f.write(content)


def edit_profile() -> None:
    """Open profile.md in system default editor.
    
    On Windows, uses os.startfile to open with default application.
    On other platforms, attempts to use xdg-open or open command.
    """
    _ensure_data_dir()
    
    # Ensure profile exists with template if empty
    load_profile()
    
    if sys.platform == "win32":
        os.startfile(PROFILE_PATH)
    elif sys.platform == "darwin":
        os.system(f'open "{PROFILE_PATH}"')
    else:
        os.system(f'xdg-open "{PROFILE_PATH}"')


def reset_profile() -> None:
    """Reset profile.md to the default template."""
    template = get_profile_template()
    save_profile(template)


if __name__ == "__main__":
    # Test: load and print profile
    profile = load_profile()
    print("Profile loaded:")
    print(profile)
