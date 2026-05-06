"""System tray icon and menu for CalendarTaskAI."""
import os
import sys
import threading
import winreg
from datetime import date

from PIL import Image, ImageDraw, ImageFont
import pystray

from constants import APP_NAME, CONFIG_PATH, PROFILE_PATH
from logger import get_logger

log = get_logger(__name__)


def create_tray_icon() -> Image.Image:
    """Generate a 64x64 tray icon with 'CT' text.
    
    Uses macaron baby blue background with dark blue-gray text for the
    light theme aesthetic.
    
    Returns:
        PIL Image object for the tray icon
    """
    size = 64
    # Macaron baby blue background (#89CFF0)
    img = Image.new('RGBA', (size, size), (137, 207, 240, 255))
    draw = ImageDraw.Draw(img)
    
    # Try to use a nice font, fall back to default
    try:
        font = ImageFont.truetype("segoeui.ttf", 28)
    except (IOError, OSError):
        try:
            font = ImageFont.truetype("arial.ttf", 28)
        except (IOError, OSError):
            font = ImageFont.load_default()
    
    # Draw "CT" centered with dark blue-gray text (#2C3E50)
    text = "CT"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - 2  # Slight offset for visual centering
    draw.text((x, y), text, fill=(44, 62, 80, 255), font=font)
    
    return img


# Registry path for auto-start
AUTOSTART_REG_PATH = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_KEY_NAME = "CalendarTaskAI"


def _has_undoable() -> bool:
    """True if there's a recorded last-add to undo. Used by the tray menu
    to grey out the Undo item when nothing's available."""
    try:
        from last_op import peek_last
        return peek_last() is not None
    except Exception:
        return False


def get_auto_start() -> bool:
    """Check if auto-start is enabled in registry.
    
    Returns:
        True if auto-start is enabled, False otherwise
    """
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_PATH, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, AUTOSTART_KEY_NAME)
            return True
    except FileNotFoundError:
        return False
    except WindowsError:
        return False


def set_auto_start(enable: bool) -> bool:
    """Enable or disable auto-start in registry.
    
    Args:
        enable: True to enable auto-start, False to disable
        
    Returns:
        True if operation succeeded, False otherwise
    """
    try:
        if enable:
            # Get the path to the main script
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                exe_path = sys.executable
            else:
                # Running as script - use pythonw to avoid console window
                python_exe = sys.executable
                pythonw = python_exe.replace("python.exe", "pythonw.exe")
                if os.path.exists(pythonw):
                    python_exe = pythonw
                
                # Get main.py path
                main_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
                exe_path = f'"{python_exe}" "{main_script}"'
            
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_PATH, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, AUTOSTART_KEY_NAME, 0, winreg.REG_SZ, exe_path)
        else:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_PATH, 0, winreg.KEY_WRITE) as key:
                try:
                    winreg.DeleteValue(key, AUTOSTART_KEY_NAME)
                except FileNotFoundError:
                    pass  # Already not set
        return True
    except WindowsError as e:
        log.warning("Failed to modify auto-start registry: %s", e)
        return False


class TrayManager:
    """Manages the system tray icon and menu."""
    
    def __init__(self, root, input_window):
        """Initialize the tray manager.

        Args:
            root: Tkinter root window for thread-safe callbacks.
            input_window: The TaskInputWindow instance. Tray actions call
                `.show()` for plain "Add Task" and `.show_with_text(...)`
                for template selections.
        """
        self.root = root
        self._input_window = input_window
        # Backward-compatible alias used by _on_add_task; keeps the contract
        # of "open the window" in one place even if input_window changes.
        self.show_window_callback = input_window.show
        # Lazily-built calendar heatmap window. Same instance is reused
        # across opens so the user's view state (current month) persists
        # across hide / show cycles.
        self._calendar_window = None
        self.icon = None
        self._thread = None
        self._running = False
        
    def _create_menu(self):
        """Create the tray menu.

        Templates submenu is built fresh each time the menu opens so that
        edits to data/templates.json are reflected without restarting the app.
        """
        return pystray.Menu(
            pystray.MenuItem("Add Task", self._on_add_task, default=True),
            pystray.MenuItem("Add from template", self._build_templates_submenu()),
            pystray.MenuItem("Today's Tasks", self._on_show_today),
            pystray.MenuItem("Calendar view", self._on_open_calendar),
            pystray.MenuItem(
                "Undo last add",
                self._on_undo_last_add,
                # Greyed out (not interactable) when nothing to undo.
                # `enabled=` is recomputed each time the menu is opened.
                enabled=lambda item: _has_undoable(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Retry Pending", self._on_retry_pending),
            pystray.MenuItem("Config", self._on_open_config),
            pystray.MenuItem("Profile", self._on_open_profile),
            pystray.MenuItem("Theme", self._build_theme_submenu()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Auto Start",
                self._on_toggle_autostart,
                checked=lambda item: get_auto_start()
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._on_quit)
        )

    def _build_theme_submenu(self):
        """Three-option Theme submenu: Light / Dark / Follow System.

        Each click writes the chosen value to `config["theme"]` and rebuilds
        the input window (and any open setup wizard's next render) so the
        new palette takes effect without an app restart.
        """
        def _is_choice(value):
            try:
                from config_manager import get_config
                return (get_config("theme") or "system") == value
            except Exception:
                return value == "system"

        return pystray.Menu(
            pystray.MenuItem(
                "Light",
                lambda icon, item: self._on_theme_change("light"),
                checked=lambda item: _is_choice("light"),
                radio=True,
            ),
            pystray.MenuItem(
                "Dark",
                lambda icon, item: self._on_theme_change("dark"),
                checked=lambda item: _is_choice("dark"),
                radio=True,
            ),
            pystray.MenuItem(
                "Follow System",
                lambda icon, item: self._on_theme_change("system"),
                checked=lambda item: _is_choice("system"),
                radio=True,
            ),
        )

    def _on_theme_change(self, value: str):
        """Persist the new theme and rebuild the input window if it's hidden.

        Live theme changes in Tkinter aren't supported by the framework
        directly. We force a rebuild by destroying the input window's
        underlying Tk root; the next `show()` call recreates it with
        whatever theme is then active. If the window is currently visible,
        we DON'T destroy it (would yank it out from under the user); the
        switch takes effect on the next close+reopen.
        """
        from config_manager import set_config
        try:
            set_config("theme", value)
            log.info("Theme changed to %s", value)
        except Exception:
            log.exception("Failed to persist theme=%s", value)
            return

        # Rebuild on the Tk thread.
        def rebuild():
            # Input window: hide-aware destroy.
            window = getattr(self, "_input_window", None)
            if window is not None:
                if getattr(window, "_is_shown", False):
                    setattr(window, "_theme_dirty", True)
                else:
                    try:
                        window.destroy()
                    except Exception:
                        log.exception("Failed to destroy input window for theme rebuild")

            # Calendar window: simpler — destroy unconditionally if it exists.
            # The user can't be "mid-task" in the calendar view, so a yank
            # is acceptable; next open rebuilds with the new palette.
            cal = self._calendar_window
            if cal is not None:
                try:
                    cal.destroy()
                except Exception:
                    log.exception("Failed to destroy calendar window for theme rebuild")

        self.root.after(0, rebuild)

    def _build_templates_submenu(self):
        """Build the 'Add from template' submenu.

        Returns a callable so pystray re-evaluates it each open, picking up
        any edits to data/templates.json without restarting the app.
        """
        def make_menu():
            from templates import load_templates
            try:
                templates = load_templates()
            except Exception:
                log.exception("Failed to load templates")
                templates = []

            if not templates:
                return pystray.Menu(
                    pystray.MenuItem("(no templates configured)", None, enabled=False)
                )

            items = []
            for tpl in templates:
                name = tpl.get("name") or "(unnamed)"
                text = tpl.get("text", "")
                # `lambda` capture: bind text via default arg.
                items.append(pystray.MenuItem(
                    name,
                    lambda icon, item, txt=text: self._on_template_selected(txt),
                ))
            return pystray.Menu(*items)

        return make_menu()

    def _on_template_selected(self, text: str):
        """Open the input window with `text` pre-filled."""
        # show_window_callback is bound to TaskInputWindow.show; we need the
        # show_with_text variant. Stash the window via an attribute set in
        # main.py so we can reach the right method.
        window = getattr(self, "_input_window", None)
        if window is not None and hasattr(window, "show_with_text"):
            self.root.after(0, lambda: window.show_with_text(text))
        else:
            # Fall back to plain show if the input window wasn't registered.
            self.root.after(0, self.show_window_callback)
        
    def _on_add_task(self, icon=None, item=None):
        """Handle 'Add Task' menu click."""
        self.root.after(0, self.show_window_callback)

    def _on_undo_last_add(self, icon=None, item=None):
        """Handle 'Undo last add' menu click."""
        def run():
            from tkinter import messagebox
            from last_op import undo_last_add
            count, msg = undo_last_add()
            kind = "info" if count else "warning"
            (messagebox.showinfo if count else messagebox.showwarning)(
                "Undo", msg, parent=self.root,
            )
        self.root.after(0, run)
        
    def _on_open_calendar(self, icon=None, item=None):
        """Handle 'Calendar view' menu click.

        Lazily constructs the heatmap window on first open and reuses the
        same instance afterwards so the user's view state (current month,
        any open day popup) persists across show / hide cycles.
        """
        def open_window():
            try:
                if self._calendar_window is None:
                    from calendar_view import CalendarHeatmapWindow
                    self._calendar_window = CalendarHeatmapWindow(self.root)
                self._calendar_window.show()
            except Exception:
                log.exception("Failed to open calendar heatmap")
        self.root.after(0, open_window)

    def _on_show_today(self, icon=None, item=None):
        """Handle 'Today's Tasks' menu click."""
        def show():
            try:
                from calendar_db import get_tasks_for_date
                from tkinter import messagebox
                
                today_str = date.today().isoformat()
                tasks = get_tasks_for_date(today_str)
                
                if not tasks:
                    messagebox.showinfo(
                        "Today's Tasks",
                        f"No tasks for {today_str}",
                        parent=self.root
                    )
                else:
                    lines = [f"Tasks for {today_str}:", ""]
                    for task in tasks:
                        checkbox = "✓" if task["done"] else "○"
                        lines.append(f"  {checkbox} {task['text']}")
                    
                    messagebox.showinfo(
                        "Today's Tasks",
                        "\n".join(lines),
                        parent=self.root
                    )
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror(
                    "Error",
                    f"Failed to load tasks: {e}",
                    parent=self.root
                )
        
        self.root.after(0, show)
        
    def _on_retry_pending(self, icon=None, item=None):
        """Handle 'Retry Pending' menu click."""
        def retry():
            try:
                from config_manager import load_config, is_configured
                from retry_queue import load_pending, retry_all
                from tkinter import messagebox
                
                if not is_configured():
                    messagebox.showwarning(
                        "Not Configured",
                        "API key not configured. Please run setup first.",
                        parent=self.root
                    )
                    return
                
                pending = load_pending()
                if not pending:
                    messagebox.showinfo(
                        "Retry Pending",
                        "No pending requests to retry.",
                        parent=self.root
                    )
                    return
                
                config = load_config()
                result = retry_all(config)
                
                messagebox.showinfo(
                    "Retry Complete",
                    f"Success: {result['success']}\nFailed: {result['failed']}",
                    parent=self.root
                )
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror(
                    "Retry Failed",
                    f"Error: {e}",
                    parent=self.root
                )
        
        self.root.after(0, retry)
        
    def _on_open_config(self, icon=None, item=None):
        """Handle 'Config' menu click - open config.json in editor."""
        try:
            os.startfile(CONFIG_PATH)
        except Exception as e:
            log.warning("Failed to open config: %s", e)
            
    def _on_open_profile(self, icon=None, item=None):
        """Handle 'Profile' menu click - open profile.md in editor."""
        try:
            # Ensure profile exists
            from profile_manager import load_profile
            load_profile()
            os.startfile(PROFILE_PATH)
        except Exception as e:
            log.warning("Failed to open profile: %s", e)
            
    def _on_toggle_autostart(self, icon=None, item=None):
        """Handle 'Auto Start' menu toggle."""
        current = get_auto_start()
        set_auto_start(not current)
        
        # Update config to match
        from config_manager import set_config
        set_config("auto_start", not current)
        
    def _on_quit(self, icon=None, item=None):
        """Handle 'Quit' menu click."""
        self.stop()
        self.root.after(0, self.root.quit)
        
    def start(self):
        """Start the tray icon in a background thread."""
        if self._running:
            return
            
        self._running = True
        self.icon = pystray.Icon(
            APP_NAME,
            create_tray_icon(),
            APP_NAME,
            menu=self._create_menu()
        )
        
        # Run in background thread
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        
    def _run(self):
        """Run the tray icon (called in background thread)."""
        try:
            self.icon.run()
        except Exception:
            log.exception("Tray icon error")
        finally:
            self._running = False
            
    def stop(self):
        """Stop the tray icon."""
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
        self._running = False


if __name__ == "__main__":
    # Test the tray icon
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()

    class _StubWindow:
        def show(self, *_):
            from tkinter import messagebox
            messagebox.showinfo("Test", "Add Task menu clicked!", parent=root)

        def show_with_text(self, text):
            from tkinter import messagebox
            messagebox.showinfo("Test", f"Template selected:\n\n{text}", parent=root)

    tray = TrayManager(root, _StubWindow())
    tray.start()
    
    print("Tray icon started. Right-click to see menu.")
    print("Press Ctrl+C to exit.")
    
    root.mainloop()
