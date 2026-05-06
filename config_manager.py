"""Configuration management for CalendarTaskAI."""
import json
import os
from typing import Any, Optional

from constants import CONFIG_PATH, DATA_DIR, DEFAULT_CONFIG


def _ensure_data_dir() -> None:
    """Ensure the data directory exists."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def load_config() -> dict:
    """Read config.json, merge with DEFAULT_CONFIG for missing keys.
    
    Returns:
        dict: Configuration dictionary with all keys from DEFAULT_CONFIG.
    """
    _ensure_data_dir()
    
    config = DEFAULT_CONFIG.copy()
    
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                file_config = json.load(f)
                if isinstance(file_config, dict):
                    config.update(file_config)
        except (json.JSONDecodeError, IOError):
            # Return defaults on error
            pass
    
    return config


def save_config(config: dict) -> None:
    """Write config to config.json with indent=2.
    
    Args:
        config: Configuration dictionary to save.
    """
    _ensure_data_dir()
    
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def get_config(key: str) -> Optional[Any]:
    """Get single config value.
    
    Args:
        key: Configuration key to retrieve.
        
    Returns:
        The configuration value, or None if key doesn't exist.
    """
    config = load_config()
    return config.get(key)


def set_config(key: str, value: Any) -> None:
    """Set single config value and save.
    
    Args:
        key: Configuration key to set.
        value: Value to set for the key.
    """
    config = load_config()
    config[key] = value
    save_config(config)


def is_configured() -> bool:
    """Check if gemini_api_key is non-empty.
    
    Returns:
        bool: True if API key is configured, False otherwise.
    """
    api_key = get_config("gemini_api_key")
    return bool(api_key and api_key.strip())


def interactive_setup() -> dict:
    """Interactive setup wizard. Users can skip fields and exit anytime.
    
    Returns:
        dict: Updated configuration dictionary.
    """
    config = load_config()
    
    print("=" * 50)
    print("CalendarTaskAI Configuration Setup")
    print("Press Enter to keep current value, or type 'q' to save & exit.")
    print("=" * 50)
    
    fields = [
        {
            "key": "gemini_api_key",
            "prompt": "Gemini API Key",
            "description": "Required. Get yours at https://aistudio.google.com/apikey",
            "required": True,
            "sensitive": True,
        },
        {
            "key": "gemini_model",
            "prompt": "Gemini Model",
            "description": "Model to use for task analysis",
            "required": False,
        },
        {
            "key": "hotkey",
            "prompt": "Global Hotkey",
            "description": "Hotkey to open task input window",
            "required": False,
        },
        {
            "key": "db_path",
            "prompt": "Database Path",
            "description": "Path to DesktopCal's calendar.db",
            "required": False,
        },
        {
            "key": "auto_start",
            "prompt": "Auto Start on Boot",
            "description": "Start CalendarTaskAI when Windows starts (true/false)",
            "required": False,
            "type": "bool",
        },
    ]
    
    for field in fields:
        key = field["key"]
        current = config.get(key, "")
        
        # Display current value (mask sensitive fields)
        if field.get("sensitive") and current:
            display_val = "****" + str(current)[-4:]
        else:
            display_val = str(current) if current != "" else "(not set)"
        
        # For bool type
        if field.get("type") == "bool":
            display_val = str(current).lower()
        
        print(f"\n{field['prompt']}")
        print(f"  {field['description']}")
        
        # Show required indicator
        required_tag = " (required)" if field.get("required") else ""
        user_input = input(f"  [{display_val}]{required_tag}: ").strip()
        
        # Check for exit
        if user_input.lower() in ("q", "quit", "exit"):
            print("Saving and exiting setup...")
            save_config(config)
            return config
        
        # Process input
        if user_input:
            if field.get("type") == "bool":
                config[key] = user_input.lower() in ("true", "yes", "1", "y")
            else:
                config[key] = user_input
        elif not current and field.get("required"):
            print(f"  Warning: {field['prompt']} is required but not set.")
    
    save_config(config)
    print("\nConfiguration saved!")
    
    # Show summary
    if not is_configured():
        print("Warning: Gemini API Key is not set. AI features will not work.")
        print("Run 'python main.py config setup' or 'python main.py config set gemini_api_key YOUR_KEY' to set it.")
    else:
        print("Setup complete. You're ready to go!")
    
    return config


if __name__ == "__main__":
    interactive_setup()
