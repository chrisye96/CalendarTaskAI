"""First-run setup wizard (Tkinter dialog).

Replaces the old console-based `interactive_setup()` for GUI mode. Under
`pythonw` the old flow deadlocks because there is no stdin; this module gives
the user a real window to fill in.

Phase 0 implementation: functional, minimal styling. Phase 1 will replace
this with a polished design via the ui-ux-pro-max skill.
"""
from __future__ import annotations

import tkinter as tk
import webbrowser
from tkinter import ttk
from typing import Optional

from config_manager import load_config, save_config
from logger import get_logger

log = get_logger(__name__)

# Provider metadata: where users go to get an API key.
_PROVIDER_INFO = {
    "gemini": {
        "label": "Google Gemini",
        "key_url": "https://aistudio.google.com/apikey",
        "key_field": "gemini_api_key",
    },
    "deepseek": {
        "label": "DeepSeek",
        "key_url": "https://platform.deepseek.com/api_keys",
        "key_field": "deepseek_api_key",
    },
}


def run_setup_wizard() -> bool:
    """Show the setup dialog. Blocks until the user submits or cancels.

    Returns True on success (config written), False on cancel.
    """
    wizard = _SetupWizard()
    wizard.run()
    return wizard.completed


class _SetupWizard:
    """Modal Tkinter dialog for first-run BYOK configuration."""

    def __init__(self) -> None:
        self.completed = False
        self.root = tk.Tk()
        self.root.title("CalendarTaskAI - First-run Setup")
        self.root.geometry("520x420")
        self.root.resizable(False, False)

        # Center on screen.
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 520) // 2
        y = (self.root.winfo_screenheight() - 420) // 2
        self.root.geometry(f"+{x}+{y}")

        config = load_config()
        self._provider_var = tk.StringVar(value=config.get("llm_provider", "gemini"))
        self._key_var = tk.StringVar(value="")

        self._build_ui()

        # Close-window-button = cancel
        self.root.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _build_ui(self) -> None:
        pad = {"padx": 18, "pady": 8}
        title = ttk.Label(
            self.root,
            text="Welcome to CalendarTaskAI",
            font=("Segoe UI", 14, "bold"),
        )
        title.pack(anchor="w", padx=18, pady=(18, 4))

        subtitle = ttk.Label(
            self.root,
            text=(
                "CalendarTaskAI uses an LLM to schedule tasks intelligently.\n"
                "Bring your own API key (BYOK) — your key stays on this machine."
            ),
            justify="left",
            foreground="#555",
        )
        subtitle.pack(anchor="w", padx=18)

        # Provider picker
        provider_frame = ttk.LabelFrame(self.root, text="LLM Provider")
        provider_frame.pack(fill="x", **pad)

        for pid, info in _PROVIDER_INFO.items():
            ttk.Radiobutton(
                provider_frame,
                text=info["label"],
                value=pid,
                variable=self._provider_var,
                command=self._refresh_provider_hint,
            ).pack(anchor="w", padx=10, pady=2)

        # API key input
        key_frame = ttk.LabelFrame(self.root, text="API Key")
        key_frame.pack(fill="x", **pad)

        # readonly trick to suppress Chrome/Edge autofill on password fields
        self._key_entry = ttk.Entry(
            key_frame, textvariable=self._key_var, show="*", width=60
        )
        self._key_entry.configure(state="readonly")
        self._key_entry.pack(fill="x", padx=10, pady=(8, 4))
        self._key_entry.bind("<FocusIn>", lambda _e: self._key_entry.configure(state="normal"))

        hint_row = ttk.Frame(key_frame)
        hint_row.pack(fill="x", padx=10, pady=(0, 8))

        self._hint_label = ttk.Label(
            hint_row, text="", foreground="#0066cc", cursor="hand2"
        )
        self._hint_label.pack(side="left")
        self._hint_label.bind("<Button-1>", self._open_key_url)

        ttk.Label(
            hint_row,
            text="Stored locally in %APPDATA%\\CalendarTaskAI\\data\\config.json",
            foreground="#888",
        ).pack(side="right")

        self._refresh_provider_hint()

        # Status / error line
        self._status_var = tk.StringVar(value="")
        ttk.Label(
            self.root, textvariable=self._status_var, foreground="#c00"
        ).pack(anchor="w", padx=18)

        # Buttons
        btn_row = ttk.Frame(self.root)
        btn_row.pack(side="bottom", fill="x", padx=18, pady=18)

        ttk.Button(btn_row, text="Cancel", command=self._on_cancel).pack(side="right")
        ttk.Button(btn_row, text="Save", command=self._on_save, default="active").pack(
            side="right", padx=(0, 8)
        )

        # Enter key submits
        self.root.bind("<Return>", lambda _e: self._on_save())
        self.root.bind("<Escape>", lambda _e: self._on_cancel())

    def _refresh_provider_hint(self) -> None:
        info = _PROVIDER_INFO[self._provider_var.get()]
        self._hint_label.configure(text=f"Get a {info['label']} API key →")

    def _open_key_url(self, _event=None) -> None:
        info = _PROVIDER_INFO[self._provider_var.get()]
        try:
            webbrowser.open(info["key_url"])
        except Exception:
            log.exception("Failed to open URL %s", info["key_url"])

    def _on_save(self) -> None:
        provider = self._provider_var.get()
        key = self._key_var.get().strip()

        if not key:
            self._status_var.set("API key is required.")
            return

        config = load_config()
        config["llm_provider"] = provider
        config[_PROVIDER_INFO[provider]["key_field"]] = key
        try:
            save_config(config)
        except Exception as e:
            log.exception("Failed to save config")
            self._status_var.set(f"Could not save config: {e}")
            return

        log.info("Setup wizard completed (provider=%s)", provider)
        self.completed = True
        self.root.destroy()

    def _on_cancel(self) -> None:
        log.info("Setup wizard cancelled")
        self.completed = False
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    # Manual test
    ok = run_setup_wizard()
    print("completed:", ok)
