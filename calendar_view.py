"""Mini calendar heatmap window.

Tray-launched popup that shows a 6-week × 7-day grid for the current month,
each cell coloured by task density (GitHub-contributions style). Clicking a
cell pops a small panel with that day's tasks.

The heatmap palette is provided by `theme.py` as five `heat_0..heat_4`
tokens, light/dark variants in lockstep with the rest of the app.
"""
from __future__ import annotations

import calendar as _cal
import tkinter as tk
from datetime import date, timedelta

from logger import get_logger

log = get_logger(__name__)

# Density bucket thresholds (UPPER bound of each bucket). A day with N total
# tasks (done + pending) falls into the bucket whose threshold N first
# satisfies. The 5th bucket has no upper bound.
_BUCKET_THRESHOLDS = (0, 2, 4, 7)


def density_bucket(task_count: int) -> int:
    """Map a task count to a 0..4 heat-stop index.

    >>> density_bucket(0)
    0
    >>> density_bucket(2)
    1
    >>> density_bucket(3)
    2
    >>> density_bucket(7)
    3
    >>> density_bucket(20)
    4
    """
    if task_count <= 0:
        return 0
    for i, threshold in enumerate(_BUCKET_THRESHOLDS):
        if task_count <= threshold:
            return i
    return 4


def _use_accent_text_for_bucket(bucket: int) -> bool:
    """True if cells of this bucket should render the day number with the
    theme's `accent_text` token instead of the plain `fg` token.

    The `accent_text` token is the per-theme contrast flip color used on
    accent-colored backgrounds: it is dark navy in the light theme and
    dark slate in the dark theme. (Both themes happen to use a dark
    accent_text because their accent backgrounds are mid-blue tones that
    look best with dark text on top.)

    Stops 0-2 are subtle (white-to-pale-blue), so `fg` reads naturally.
    Stops 3-4 are saturated blues where the dark `accent_text` gives the
    AA-passing contrast verified by `tests/test_calendar_view.py`.
    """
    return bucket >= 3


# ---------------------------------------------------------------------------
# Window
# ---------------------------------------------------------------------------

class CalendarHeatmapWindow:
    """Stateful Toplevel showing a 6-week heatmap. Single instance per app."""

    CELL_W = 56
    CELL_H = 48
    HEADER_H = 40
    WEEKDAY_H = 24
    GUTTER = 2

    def __init__(self, parent: tk.Misc | None = None) -> None:
        self.parent = parent
        self.root: tk.Toplevel | None = None
        self._is_shown = False

        # Currently displayed month, expressed as the 1st of that month.
        # Defaults to today's month at every show().
        self._anchor: date = date.today().replace(day=1)

        # Cells indexed by ISO date string -> (frame, label) for live update.
        self._cells: dict[str, tuple[tk.Frame, tk.Label]] = {}

        # Theme tokens, refreshed at every (re)build. Same pattern as ui.py.
        self._t: dict[str, str] = {}

    # -- public API ----------------------------------------------------

    def show(self) -> None:
        """Open the window (or raise it to front if already open)."""
        if self.parent is not None:
            self.parent.after(0, self._do_show)
        else:
            self._do_show()

    def destroy(self) -> None:
        """Tear down the window. Next show() rebuilds with fresh theme."""
        if self.root is not None:
            try:
                self.root.destroy()
            except Exception:
                log.exception("Calendar window destroy failed")
        self.root = None
        self._is_shown = False

    # -- build flow ----------------------------------------------------

    def _do_show(self) -> None:
        if self.root is None:
            self._build()
        else:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        self._is_shown = True

    def _build(self) -> None:
        from theme import current_theme
        self._t = current_theme()

        if self.parent is not None:
            self.root = tk.Toplevel(self.parent)
        else:
            self.root = tk.Tk()
        self.root.title("CalendarTaskAI - Calendar")
        self.root.configure(bg=self._t["bg"])
        self.root.attributes("-topmost", True)
        self.root.bind("<Escape>", lambda _e: self._close())
        self.root.protocol("WM_DELETE_WINDOW", self._close)

        # Anchor to today's month every time the window is built.
        self._anchor = date.today().replace(day=1)

        self._build_header()
        self._build_weekday_row()
        self._grid_frame = tk.Frame(self.root, bg=self._t["bg"])
        self._grid_frame.pack(padx=12, pady=(0, 12))
        self._render_grid()

        # Centre on the screen.
        self.root.update_idletasks()
        w = self.root.winfo_reqwidth()
        h = self.root.winfo_reqheight()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _build_header(self) -> None:
        bar = tk.Frame(self.root, bg=self._t["bg"])
        bar.pack(fill="x", padx=12, pady=(12, 6))

        prev_btn = tk.Button(
            bar, text="◀", command=lambda: self._shift_month(-1),
            bg=self._t["surface_alt"], fg=self._t["fg"],
            activebackground=self._t["border"], activeforeground=self._t["fg"],
            relief="flat", cursor="hand2", width=3,
            font=("Segoe UI", 10),
        )
        prev_btn.pack(side="left")

        self._title_var = tk.StringVar(value=self._anchor.strftime("%B %Y"))
        tk.Label(
            bar, textvariable=self._title_var,
            bg=self._t["bg"], fg=self._t["fg"],
            font=("Segoe UI", 12, "bold"),
        ).pack(side="left", padx=12)

        next_btn = tk.Button(
            bar, text="▶", command=lambda: self._shift_month(+1),
            bg=self._t["surface_alt"], fg=self._t["fg"],
            activebackground=self._t["border"], activeforeground=self._t["fg"],
            relief="flat", cursor="hand2", width=3,
            font=("Segoe UI", 10),
        )
        next_btn.pack(side="left")

        self._today_btn = tk.Button(
            bar, text="Today", command=self._goto_today,
            bg=self._t["accent"], fg=self._t["accent_text"],
            activebackground=self._t["accent_dark"],
            activeforeground=self._t["accent_text"],
            relief="flat", cursor="hand2",
            font=("Segoe UI", 9, "bold"), padx=12, pady=4,
        )
        self._today_btn.pack(side="right")
        self._sync_today_button()

    def _build_weekday_row(self) -> None:
        row = tk.Frame(self.root, bg=self._t["bg"])
        row.pack(padx=12, pady=(0, 4))
        # Mon..Sun, matching Python's weekday() ordering. The grid below
        # uses the same ordering, so column N here always lines up with
        # column N in the grid.
        for label in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"):
            tk.Label(
                row, text=label,
                bg=self._t["bg"], fg=self._t["fg_muted"],
                font=("Segoe UI", 9),
                width=6,
            ).pack(side="left", padx=(self.GUTTER, self.GUTTER))

    # -- grid render ---------------------------------------------------

    def _render_grid(self) -> None:
        for child in self._grid_frame.winfo_children():
            child.destroy()
        self._cells.clear()

        # Pull task counts for the visible window. The 6×7 = 42-day window
        # always starts on the Monday on/before the 1st of the anchor month.
        first_visible = _grid_start(self._anchor)
        last_visible = first_visible + timedelta(days=41)

        from calendar_db import get_tasks_in_range
        try:
            tasks_by_date = get_tasks_in_range(
                first_visible.isoformat(), last_visible.isoformat()
            )
        except Exception:
            log.exception("Calendar heatmap: failed to read tasks")
            tasks_by_date = {}

        today = date.today()

        for week in range(6):
            row = tk.Frame(self._grid_frame, bg=self._t["bg"])
            row.pack()
            for weekday in range(7):
                day = first_visible + timedelta(days=week * 7 + weekday)
                count = len(tasks_by_date.get(day.isoformat(), []))
                self._make_cell(row, day, count, today=day == today)

        self._title_var.set(self._anchor.strftime("%B %Y"))
        self._sync_today_button()

    def _make_cell(self, row: tk.Frame, day: date, count: int, today: bool) -> None:
        bucket = density_bucket(count)
        bg = self._t[f"heat_{bucket}"]
        in_month = day.month == self._anchor.month

        # Day-number text colour:
        #  * stops 3-4 -> accent_text (white-ish on dark, dark navy on light)
        #  * stops 0-2 -> fg
        # Out-of-month days dim further to fg_subtle, but only when on the
        # lighter stops (0-2); on saturated stops the contrast is still fine.
        if _use_accent_text_for_bucket(bucket):
            fg = self._t["accent_text"]
        elif not in_month:
            fg = self._t["fg_subtle"]
        else:
            fg = self._t["fg"]

        # Today gets a 2px ring without disturbing the density bg. We
        # implement the ring with `highlightthickness` + a coloured
        # `highlightbackground`; Tkinter actually draws this 2px stroke.
        ring_w = 2 if today else 1
        ring_color = self._t["border_strong"] if today else self._t["border"]

        cell = tk.Frame(
            row, bg=bg,
            highlightthickness=ring_w, highlightbackground=ring_color,
            width=self.CELL_W, height=self.CELL_H,
        )
        cell.pack_propagate(False)
        cell.pack(side="left", padx=self.GUTTER, pady=self.GUTTER)

        label = tk.Label(
            cell, text=str(day.day),
            bg=bg, fg=fg,
            font=("Segoe UI", 10, "bold" if today else "normal"),
            cursor="hand2",
            anchor="ne", padx=6, pady=4,
        )
        label.pack(fill="both", expand=True)

        # Click: open the day popup. Bind to BOTH cell and label so the
        # whole rectangle is reactive.
        for w in (cell, label):
            w.bind("<Button-1>", lambda _e, d=day: self._open_day_popup(d))
            # Cheap hover affordance: stronger border on enter, normal on leave.
            w.bind("<Enter>", lambda _e, c=cell, t=today: self._on_cell_enter(c, t))
            w.bind("<Leave>", lambda _e, c=cell, t=today: self._on_cell_leave(c, t))

        self._cells[day.isoformat()] = (cell, label)

    def _on_cell_enter(self, cell: tk.Frame, today: bool) -> None:
        # Don't recolour the today ring on hover; it has its own meaning.
        if not today:
            cell.configure(highlightbackground=self._t["accent_dark"])

    def _on_cell_leave(self, cell: tk.Frame, today: bool) -> None:
        if not today:
            cell.configure(highlightbackground=self._t["border"])

    # -- nav -----------------------------------------------------------

    def _shift_month(self, delta: int) -> None:
        m = self._anchor.month - 1 + delta
        y = self._anchor.year + m // 12
        m = m % 12 + 1
        self._anchor = date(y, m, 1)
        self._render_grid()

    def _goto_today(self) -> None:
        new_anchor = date.today().replace(day=1)
        if new_anchor == self._anchor:
            return
        self._anchor = new_anchor
        self._render_grid()

    def _sync_today_button(self) -> None:
        """Disable Today button when already on this month."""
        if not hasattr(self, "_today_btn"):
            return
        if self._anchor == date.today().replace(day=1):
            self._today_btn.configure(
                state="disabled",
                bg=self._t["disabled_bg"], fg=self._t["disabled_fg"],
                cursor="arrow",
            )
        else:
            self._today_btn.configure(
                state="normal",
                bg=self._t["accent"], fg=self._t["accent_text"],
                cursor="hand2",
            )

    # -- day popup -----------------------------------------------------

    def _open_day_popup(self, day: date) -> None:
        from calendar_db import get_tasks_for_date
        try:
            tasks = get_tasks_for_date(day.isoformat())
        except Exception:
            log.exception("Calendar heatmap: failed to read day tasks for %s", day)
            tasks = []

        popup = tk.Toplevel(self.root)
        popup.title(day.strftime("%A, %B %d"))
        popup.configure(bg=self._t["bg"])
        popup.attributes("-topmost", True)
        popup.bind("<Escape>", lambda _e: popup.destroy())

        tk.Label(
            popup, text=day.strftime("%A, %B %d, %Y"),
            bg=self._t["bg"], fg=self._t["fg"],
            font=("Segoe UI", 11, "bold"),
            anchor="w", padx=14, pady=(12, 6),
        ).pack(fill="x")

        body = tk.Frame(popup, bg=self._t["surface"])
        body.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        if not tasks:
            tk.Label(
                body, text="No tasks scheduled.",
                bg=self._t["surface"], fg=self._t["fg_muted"],
                font=("Segoe UI", 10),
                anchor="w", padx=10, pady=10,
            ).pack(fill="x")
        else:
            for t in tasks:
                checkbox = "✓" if t.get("done") else "○"
                fg_col = self._t["fg_muted"] if t.get("done") else self._t["fg"]
                tk.Label(
                    body, text=f"  {checkbox}  {t['text']}",
                    bg=self._t["surface"], fg=fg_col,
                    font=("Segoe UI", 10),
                    anchor="w", padx=10, pady=4, justify="left",
                    wraplength=320,
                ).pack(fill="x")

        # Position the popup near the cell that opened it. Center on screen
        # is the simplest correct fallback.
        popup.update_idletasks()
        w = popup.winfo_reqwidth()
        h = popup.winfo_reqheight()
        sw = popup.winfo_screenwidth()
        sh = popup.winfo_screenheight()
        popup.geometry(f"{max(w, 320)}x{max(h, 120)}+{(sw - w) // 2}+{(sh - h) // 2}")

    # -- close ---------------------------------------------------------

    def _close(self) -> None:
        self._is_shown = False
        if self.root is not None:
            try:
                self.root.withdraw()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Date-math helper (pure, separately testable)
# ---------------------------------------------------------------------------

def _grid_start(anchor: date) -> date:
    """Return the Monday on or before the 1st of `anchor`'s month.

    The 6-week heatmap always starts on a Monday so the seven weekday
    columns line up with the weekday header row. If the 1st is a Monday
    we return it directly; otherwise we step back 1..6 days.
    """
    first = anchor.replace(day=1)
    # weekday(): Mon=0, Sun=6. Step back exactly that many days.
    return first - timedelta(days=first.weekday())
