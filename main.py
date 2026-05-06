"""CalendarTaskAI - main entry point.

Modes:
    No arguments:    GUI mode (tray icon + global hotkey + floating input window)
    With arguments:  CLI mode (e.g. `python main.py today`, `python main.py add "..."`)
"""
import sys


def _enable_dpi_awareness() -> None:
    """Tell Windows we render at native DPI so Tkinter doesn't get blurry on hi-DPI displays.

    Best-effort: silently skips on non-Windows or if the API isn't available.
    Called once at process start, before any tk.Tk() is created.
    """
    if sys.platform != "win32":
        return
    try:
        from ctypes import windll
        # Per-monitor DPI awareness (Win 8.1+). Falls back to system DPI on older versions.
        try:
            windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        except Exception:
            windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def _is_frozen_gui_exe() -> bool:
    """True iff we're running as the no-console GUI exe (`CalendarTaskAI.exe`).

    The bundle ships two exes from the same code (see `CalendarTaskAI.spec`):
    `CalendarTaskAI.exe` is the GUI launcher (`console=False`), and
    `CalendarTaskAI-cli.exe` is the console-attached variant.

    Detection earlier tried `GetConsoleWindow()` to ask Windows "does this
    process have a console the user can see?" — but that question gives
    false positives in non-Windows-console parent shells (e.g. Git Bash
    via winpty), where the CLI exe also has no Windows console. The
    direct, reliable answer is to look at the exe filename: only the GUI
    binary is named `CalendarTaskAI.exe`.
    """
    if not getattr(sys, "frozen", False):
        return False
    import os
    exe = os.path.basename(sys.executable).lower()
    return exe == "calendartaskai.exe"


def _show_use_cli_exe_message(args: list[str]) -> None:
    """Pop a Tk message box telling the user to launch CalendarTaskAI-cli.exe."""
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.withdraw()
    arg_str = " ".join(args)
    messagebox.showinfo(
        "CalendarTaskAI",
        f"You launched the GUI executable with arguments:\n\n"
        f"    CalendarTaskAI.exe {arg_str}\n\n"
        f"This launcher has no console attached, so command output is\n"
        f"discarded. For CLI commands, use the sibling executable:\n\n"
        f"    CalendarTaskAI-cli.exe {arg_str}",
    )
    root.destroy()


def main() -> None:
    """Route to CLI or GUI based on arguments."""
    # Initialize logging early so even import-time errors get captured.
    from logger import setup_logging, get_logger
    setup_logging()
    log = get_logger(__name__)

    if len(sys.argv) > 1:
        if _is_frozen_gui_exe():
            # User invoked the no-console GUI exe with CLI arguments.
            # Click's output would silently disappear; redirect them to
            # the sibling CLI exe instead of letting them see nothing.
            log.warning("GUI exe received CLI args %s; showing redirect message", sys.argv[1:])
            _show_use_cli_exe_message(sys.argv[1:])
            return
        log.debug("CLI mode invoked with %s", sys.argv[1:])
        from cli import cli
        cli()
    else:
        log.debug("GUI mode invoked")
        _enable_dpi_awareness()
        start_gui()


def _ensure_configured_or_run_wizard() -> bool:
    """Make sure an API key is configured before starting the GUI.

    If config is missing, runs the Tkinter setup wizard (NOT the console-based
    interactive_setup, which would deadlock under pythonw with no stdin).

    Returns True if configured (either was already, or wizard succeeded), False
    if the user cancelled the wizard.
    """
    from config_manager import is_configured
    if is_configured():
        return True

    from logger import get_logger
    log = get_logger(__name__)
    log.info("First run / unconfigured: launching setup wizard")

    try:
        from setup_wizard import run_setup_wizard
        return run_setup_wizard()
    except Exception:
        log.exception("Setup wizard failed")
        return False


def start_gui() -> None:
    """Start the GUI application: tray icon, global hotkey, hidden Tk root."""
    import tkinter as tk
    from logger import get_logger

    log = get_logger(__name__)
    log.info("CalendarTaskAI %s starting (GUI mode)", _app_version())

    # 1. Make sure we have an API key (run wizard if not).
    if not _ensure_configured_or_run_wizard():
        log.warning("Setup not completed; exiting")
        return

    from config_manager import load_config
    config = load_config()

    # 2. Auto-retry pending failed requests on startup.
    if config.get("retry_on_startup", True):
        try:
            from retry_queue import load_pending, retry_all
            pending = load_pending()
            if pending:
                log.info("Retrying %d pending request(s)...", len(pending))
                result = retry_all(config)
                log.info("Retry done: %d ok, %d failed", result["success"], result["failed"])
        except Exception:
            log.exception("Startup retry failed")

    # 3. Top up recurring rules so we always have ~12 weeks of future
    # instances written to the calendar DB. Idempotent on a given day.
    try:
        from recurring import extend_all
        from calendar_db import write_tasks
        new_instances = extend_all()
        if new_instances:
            log.info(
                "Recurring extend: writing %d new instance(s) to calendar",
                len(new_instances),
            )
            write_tasks(new_instances)
    except Exception:
        log.exception("Recurring extend failed at startup")

    # 4. Hidden Tk root for tray + windows.
    root = tk.Tk()
    root.withdraw()

    def _handle_tk_exception(exc_type, exc_value, exc_tb):
        import traceback
        msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        log.error("Unhandled Tk exception:\n%s", msg)

    root.report_callback_exception = lambda *args: _handle_tk_exception(*args)

    # 4. Build the input window and tray.
    from ui import TaskInputWindow
    input_window = TaskInputWindow(root)

    from tray import TrayManager
    tray = TrayManager(root, input_window)
    tray.start()

    # 5. Register the global hotkey (best-effort: app still works without it).
    hotkey = config.get("hotkey", "ctrl+alt+space")
    hotkey_registered = False
    try:
        import keyboard

        def on_hotkey():
            root.after(0, input_window.show)

        keyboard.add_hotkey(hotkey, on_hotkey)
        hotkey_registered = True
        log.info("Hotkey '%s' registered", hotkey)
    except ImportError:
        log.warning("'keyboard' module not installed; global hotkey disabled")
    except Exception as e:
        log.warning("Failed to register hotkey '%s': %s (try running as admin)", hotkey, e)

    # 6. Clean shutdown.
    def on_quit():
        log.info("Shutting down")
        if hotkey_registered:
            try:
                import keyboard
                keyboard.unhook_all()
            except Exception:
                log.exception("hotkey unhook failed")
        tray.stop()
        input_window.destroy()
        root.quit()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_quit)

    log.info("CalendarTaskAI is running. Hotkey=%s", hotkey if hotkey_registered else "(disabled)")

    # 7. Mainloop.
    try:
        root.mainloop()
    except KeyboardInterrupt:
        log.info("Interrupted by user")
        on_quit()


def _app_version() -> str:
    try:
        from constants import APP_VERSION
        return APP_VERSION
    except Exception:
        return "unknown"


def check_dependencies() -> bool:
    """Quick check that runtime dependencies are importable. GUI mode only."""
    missing = []
    for name, pip_name in [
        ("PIL", "Pillow"),
        ("pystray", "pystray"),
        ("keyboard", "keyboard (optional, for global hotkey)"),
        ("google.genai", "google-genai"),
        ("click", "click"),
    ]:
        try:
            __import__(name)
        except ImportError:
            missing.append(pip_name)

    if missing:
        # Print to stderr so this is visible from a console; logger may not be set up yet.
        sys.stderr.write("Missing dependencies:\n")
        for dep in missing:
            sys.stderr.write(f"  - {dep}\n")
        sys.stderr.write("\nInstall with: pip install -r requirements.txt\n")
        return False
    return True


if __name__ == "__main__":
    if len(sys.argv) == 1:
        if not check_dependencies():
            sys.exit(1)
    main()
