"""First-run setup wizard.

Replaces the old console-based `interactive_setup()` for GUI mode. Under
`pythonw` that flow deadlocks because there's no stdin; here the user gets
a proper window.

Layout (light macaron theme, matched to TaskInputWindow):
  - Title bar (accent blue)
  - Provider section: radio "cards" with name + tagline
  - API key section: masked entry, "Get key" link, "Test connection" button
  - Status line: ✓ / ⚠ / ✗ icon + text
  - Footer: Cancel / Save

Test connection runs `LLMProvider.test_connection()` in a background thread
so the UI doesn't freeze; the result is reported on the main thread via
`root.after(0, ...)`.
"""
from __future__ import annotations

import threading
import tkinter as tk
import webbrowser

from config_manager import load_config, save_config
from logger import get_logger
from providers import NotConfigured, get_provider, list_providers
from theme import current_theme

log = get_logger(__name__)

# Refreshed at the top of `run_setup_wizard()` so the wizard always opens
# with whatever theme is currently configured (including post-tray-switch).
# All `T["..."]` references throughout this module read from this dict.
T: dict[str, str] = current_theme()

# Where each provider sends users to claim a key, and which config field
# stores it. Order here matches `providers.registry._REGISTRY`.
_PROVIDER_META = {
    "gemini": {
        "tagline": "Google. Free tier; default for new users.",
        "key_url": "https://aistudio.google.com/apikey",
        "key_field": "gemini_api_key",
    },
    "openai": {
        "tagline": "OpenAI ChatGPT. Paid; widely available.",
        "key_url": "https://platform.openai.com/api-keys",
        "key_field": "openai_api_key",
    },
    "claude": {
        "tagline": "Anthropic Claude. Paid; strong at long context.",
        "key_url": "https://console.anthropic.com/settings/keys",
        "key_field": "claude_api_key",
    },
    "grok": {
        "tagline": "xAI Grok. Paid; SuperGrok / X account-aligned.",
        "key_url": "https://console.x.ai/",
        "key_field": "grok_api_key",
    },
    "mistral": {
        "tagline": "Mistral AI. EU-hosted; open-weight lineage.",
        "key_url": "https://console.mistral.ai/api-keys",
        "key_field": "mistral_api_key",
    },
    "deepseek": {
        "tagline": "DeepSeek. Cheap; auto flash/pro tier switch.",
        "key_url": "https://platform.deepseek.com/api_keys",
        "key_field": "deepseek_api_key",
    },
    "kimi": {
        "tagline": "Moonshot Kimi. Free tier; mainland-China-friendly.",
        "key_url": "https://platform.moonshot.cn/console/api-keys",
        "key_field": "kimi_api_key",
    },
    "qwen": {
        "tagline": "Alibaba Qwen via DashScope. Mainland-friendly.",
        "key_url": "https://bailian.console.aliyun.com/?tab=model#/api-key",
        "key_field": "qwen_api_key",
    },
    "glm": {
        "tagline": "Zhipu GLM (Z.ai). Tops Chinese benchmarks.",
        "key_url": "https://open.bigmodel.cn/usercenter/apikeys",
        "key_field": "glm_api_key",
    },
    "openrouter": {
        "tagline": "300+ models behind one key (auto-route by default).",
        "key_url": "https://openrouter.ai/keys",
        "key_field": "openrouter_api_key",
    },
}


def run_setup_wizard() -> bool:
    """Show the wizard. Blocks. Returns True if the user saved a config."""
    # Refresh the module-level T so a tray-menu theme switch picks up on
    # the next wizard open without an app restart.
    global T
    T = current_theme()
    wizard = _SetupWizard()
    wizard.run()
    return wizard.completed


class _SetupWizard:
    def __init__(self) -> None:
        self.completed = False

        self.root = tk.Tk()
        self.root.title("CalendarTaskAI — Setup")
        self.root.geometry("560x600")
        self.root.resizable(False, False)
        self.root.configure(bg=T["bg"])

        # Center on screen
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 560) // 2
        y = (self.root.winfo_screenheight() - 600) // 2
        self.root.geometry(f"+{x}+{y}")

        config = load_config()
        self._provider_var = tk.StringVar(value=config.get("llm_provider", "gemini"))
        self._provider_var.trace_add("write", lambda *_: self._on_provider_change())
        self._key_var = tk.StringVar(value="")

        # Pre-populate the key for the currently selected provider, if any
        meta = _PROVIDER_META[self._provider_var.get()]
        existing = config.get(meta["key_field"], "")
        if existing:
            self._key_var.set(existing)

        # Status state for the test-connection result
        self._status_kind = "info"  # "info" | "ok" | "warn" | "error"
        self._test_thread: threading.Thread | None = None

        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self._on_cancel)

    # ---------------------------------------------------------------- build

    def _build(self) -> None:
        self._build_titlebar()

        body = tk.Frame(self.root, bg=T["bg"])
        body.pack(fill="both", expand=True, padx=24, pady=(8, 0))

        # Subtitle
        tk.Label(
            body,
            text=("Bring your own LLM API key. The key is stored only on this\n"
                  "machine, in %APPDATA%\\CalendarTaskAI\\data\\config.json."),
            bg=T["bg"], fg=T["fg_muted"],
            font=("Segoe UI", 9), justify="left",
        ).pack(anchor="w", pady=(8, 14))

        self._build_provider_section(body)
        self._build_key_section(body)
        self._build_status_line(body)
        self._build_footer()

        self.root.bind("<Return>", lambda _e: self._on_save())
        self.root.bind("<Escape>", lambda _e: self._on_cancel())

    def _build_titlebar(self) -> None:
        bar = tk.Frame(self.root, bg=T["title_bg"], height=56)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Label(
            bar,
            text="Welcome to CalendarTaskAI",
            bg=T["title_bg"], fg=T["title_fg"],
            font=("Segoe UI", 14, "bold"),
        ).pack(side="left", padx=20)

    def _build_provider_section(self, parent: tk.Widget) -> None:
        tk.Label(
            parent, text="LLM Provider",
            bg=T["bg"], fg=T["fg"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 6))

        # Scrollable container so the wizard fits 720p screens even with
        # 10+ providers. Canvas holds the cards Frame; vertical scrollbar
        # appears on the right. ~300px height lets the user see roughly 5
        # cards at once and scroll for the rest.
        outer = tk.Frame(parent, bg=T["bg"])
        outer.pack(fill="x")

        canvas = tk.Canvas(
            outer, bg=T["bg"], highlightthickness=0, height=300,
        )
        scrollbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="x", expand=True)
        scrollbar.pack(side="right", fill="y")

        cards_frame = tk.Frame(canvas, bg=T["bg"])
        # `anchor="nw"` and explicit width-syncing keep cards full-width
        # inside the canvas regardless of the outer frame's reported size.
        window_id = canvas.create_window((0, 0), window=cards_frame, anchor="nw")

        def _sync_width(event):
            canvas.itemconfigure(window_id, width=event.width)
        canvas.bind("<Configure>", _sync_width)

        def _update_scrollregion(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
        cards_frame.bind("<Configure>", _update_scrollregion)

        # Mousewheel scrolls the canvas as long as the wizard has focus.
        # We bind on the wizard root instead of `bind_all` + Enter/Leave
        # because (a) Tk's <Leave> fires when the cursor crosses into any
        # child widget, which would silently disable scrolling over the
        # provider cards, and (b) bind_all leaks past root destruction if
        # the wizard is closed while the cursor is over the canvas. Since
        # the wizard has no other scrollable region, scoping to root is
        # both simpler and correct.
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-event.delta / 120), "units")
        self.root.bind("<MouseWheel>", _on_mousewheel)

        self._provider_cards: dict[str, tk.Frame] = {}
        for pid, display in list_providers():
            card = self._make_provider_card(cards_frame, pid, display)
            card.pack(fill="x", pady=4, padx=2)
            self._provider_cards[pid] = card

        self._refresh_provider_cards()

    def _make_provider_card(self, parent: tk.Widget, pid: str, display: str) -> tk.Frame:
        meta = _PROVIDER_META.get(pid, {})
        tagline = meta.get("tagline", "")

        # Card with subtle border; selected card gets a stronger border
        card = tk.Frame(parent, bg=T["surface"], highlightthickness=1,
                        highlightbackground=T["border"])

        inner = tk.Frame(card, bg=T["surface"])
        inner.pack(fill="x", padx=14, pady=10)

        rb = tk.Radiobutton(
            inner, text=display, value=pid, variable=self._provider_var,
            bg=T["surface"], fg=T["fg"],
            activebackground=T["surface"], activeforeground=T["fg"],
            selectcolor=T["surface"],
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
        )
        rb.pack(anchor="w")

        if tagline:
            tk.Label(
                inner, text=tagline,
                bg=T["surface"], fg=T["fg_muted"],
                font=("Segoe UI", 9),
            ).pack(anchor="w", padx=22)

        # Click anywhere on the card to select that provider
        for w in (card, inner):
            w.bind("<Button-1>", lambda _e, p=pid: self._provider_var.set(p))
        return card

    def _build_key_section(self, parent: tk.Widget) -> None:
        tk.Label(
            parent, text="API Key",
            bg=T["bg"], fg=T["fg"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(14, 6))

        row = tk.Frame(parent, bg=T["bg"])
        row.pack(fill="x")

        # Use a `readonly` trick to suppress browser autofill for password
        # fields; the entry becomes editable on first focus.
        self._key_entry = tk.Entry(
            row, textvariable=self._key_var, show="•", width=40,
            bg=T["surface"], fg=T["fg"],
            insertbackground=T["fg"],
            relief="flat", highlightthickness=1,
            highlightbackground=T["border"], highlightcolor=T["border_strong"],
            font=("Segoe UI", 10),
        )
        self._key_entry.configure(state="readonly")
        self._key_entry.pack(side="left", fill="x", expand=True, ipady=6)
        self._key_entry.bind(
            "<FocusIn>", lambda _e: self._key_entry.configure(state="normal"))
        self._key_var.trace_add("write", lambda *_: self._reset_status())

        self._test_btn = tk.Button(
            row, text="Test", command=self._on_test,
            bg=T["surface_alt"], fg=T["fg"],
            activebackground=T["border"], activeforeground=T["fg"],
            relief="flat", cursor="hand2",
            font=("Segoe UI", 9), padx=14, pady=4,
        )
        self._test_btn.pack(side="left", padx=(8, 0))

        # Helper row: link to provider key page + storage reassurance
        helper = tk.Frame(parent, bg=T["bg"])
        helper.pack(fill="x", pady=(6, 0))

        self._key_link = tk.Label(
            helper, text="", bg=T["bg"], fg=T["link"],
            cursor="hand2", font=("Segoe UI", 9, "underline"),
        )
        self._key_link.pack(side="left")
        self._key_link.bind("<Button-1>", self._open_key_url)

        tk.Label(
            helper,
            text="🔒 stored locally only",
            bg=T["bg"], fg=T["fg_muted"],
            font=("Segoe UI", 8),
        ).pack(side="right")

        self._refresh_key_link()

    def _build_status_line(self, parent: tk.Widget) -> None:
        self._status_var = tk.StringVar(value="Click Test to verify your key.")
        self._status_label = tk.Label(
            parent, textvariable=self._status_var,
            bg=T["bg"], fg=T["fg_muted"],
            font=("Segoe UI", 9), anchor="w", justify="left",
        )
        self._status_label.pack(fill="x", pady=(16, 0))

    def _build_footer(self) -> None:
        footer = tk.Frame(self.root, bg=T["bg"])
        footer.pack(side="bottom", fill="x", padx=24, pady=18)

        save = tk.Button(
            footer, text="Save", command=self._on_save,
            bg=T["accent"], fg=T["accent_text"],
            activebackground=T["accent_dark"], activeforeground=T["accent_text"],
            relief="flat", cursor="hand2",
            font=("Segoe UI", 10, "bold"), padx=22, pady=6,
        )
        save.pack(side="right")

        cancel = tk.Button(
            footer, text="Cancel", command=self._on_cancel,
            bg=T["surface_alt"], fg=T["fg"],
            activebackground=T["border"], activeforeground=T["fg"],
            relief="flat", cursor="hand2",
            font=("Segoe UI", 10), padx=18, pady=6,
        )
        cancel.pack(side="right", padx=(0, 8))

    # ----------------------------------------------------------- callbacks

    def _on_provider_change(self) -> None:
        self._refresh_provider_cards()
        self._refresh_key_link()

        # Populate the key field with whatever's already stored for this
        # provider, so revisiting the wizard preserves prior keys.
        cfg = load_config()
        meta = _PROVIDER_META[self._provider_var.get()]
        self._key_var.set(cfg.get(meta["key_field"], ""))
        self._reset_status()

    def _refresh_provider_cards(self) -> None:
        active = self._provider_var.get()
        for pid, card in self._provider_cards.items():
            color = T["border_strong"] if pid == active else T["border"]
            card.configure(highlightbackground=color, highlightcolor=color)

    def _refresh_key_link(self) -> None:
        meta = _PROVIDER_META[self._provider_var.get()]
        provider_label = next((d for p, d in list_providers()
                               if p == self._provider_var.get()), "")
        self._key_link.configure(text=f"Get a {provider_label} API key →")
        self._key_link._url = meta["key_url"]  # stash for the click handler

    def _open_key_url(self, _event=None) -> None:
        url = getattr(self._key_link, "_url", None)
        if not url:
            return
        try:
            webbrowser.open(url)
        except Exception:
            log.exception("Failed to open URL %s", url)

    def _reset_status(self) -> None:
        self._set_status("Click Test to verify your key.", kind="info")

    def _set_status(self, text: str, *, kind: str) -> None:
        icon = {"ok": "✓ ", "warn": "⚠ ", "error": "✗ ", "info": ""}.get(kind, "")
        color = {
            "ok": T["success"],
            "warn": T["warning"],
            "error": T["error"],
            "info": T["fg_muted"],
        }.get(kind, T["fg_muted"])
        self._status_kind = kind
        self._status_var.set(icon + text)
        self._status_label.configure(fg=color)

    def _on_test(self) -> None:
        if self._test_thread and self._test_thread.is_alive():
            return  # guard against double-click

        key = self._key_var.get().strip()
        if not key:
            self._set_status("Enter an API key first.", kind="warn")
            return

        # Build a transient provider with the in-flight values (don't persist
        # to disk just because the user clicked Test).
        cfg = self._build_transient_config(key)
        self._test_btn.configure(text="Testing…", state="disabled")
        self._set_status("Contacting the provider...", kind="info")

        def _worker():
            try:
                provider = get_provider(cfg)
                ok, msg = provider.test_connection()
            except NotConfigured as e:
                ok, msg = False, str(e)
            except Exception as e:  # connection / SDK / parse
                log.exception("Test connection failed")
                ok, msg = False, f"{type(e).__name__}: {e}"

            def _apply():
                self._test_btn.configure(text="Test", state="normal")
                self._set_status(msg, kind="ok" if ok else "error")

            self.root.after(0, _apply)

        self._test_thread = threading.Thread(target=_worker, daemon=True)
        self._test_thread.start()

    def _build_transient_config(self, key: str) -> dict:
        """Compose a config dict with the in-flight key for the active
        provider, leaving everything else at defaults from disk."""
        cfg = load_config()
        cfg["llm_provider"] = self._provider_var.get()
        meta = _PROVIDER_META[self._provider_var.get()]
        cfg[meta["key_field"]] = key
        return cfg

    def _on_save(self) -> None:
        provider = self._provider_var.get()
        key = self._key_var.get().strip()
        if not key:
            self._set_status("API key is required.", kind="error")
            return

        cfg = load_config()
        cfg["llm_provider"] = provider
        cfg[_PROVIDER_META[provider]["key_field"]] = key

        try:
            save_config(cfg)
        except Exception as e:
            log.exception("Failed to save config")
            self._set_status(f"Could not save: {e}", kind="error")
            return

        log.info("Setup wizard completed (provider=%s)", provider)
        self.completed = True
        self.root.destroy()

    def _on_cancel(self) -> None:
        log.info("Setup wizard cancelled")
        self.completed = False
        self.root.destroy()

    # -------------------------------------------------------------- driver

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    print("completed:", run_setup_wizard())
