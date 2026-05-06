"""Tkinter floating window UI for CalendarTaskAI - Macaron Light Blue Theme."""
import os
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk

from logger import get_logger

log = get_logger(__name__)


def _get_desktopcal_path() -> str | None:
    """Locate desktopcal.exe.

    Tries (in order):
    1. PowerShell Get-CimInstance to read the path of any running desktopcal.exe.
       (Replaces the deprecated `wmic` which is being removed from Win11 24H2+.)
    2. Inferred sibling of the configured calendar.db path.

    Returns the path or None.
    """
    # Method 1: query running process via PowerShell CIM
    try:
        ps_cmd = (
            "Get-CimInstance Win32_Process "
            "-Filter \"Name LIKE '%desktopcal%'\" "
            "| Select-Object -First 1 -ExpandProperty ExecutablePath"
        )
        result = subprocess.run(
            ['powershell', '-NoProfile', '-NonInteractive', '-Command', ps_cmd],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        out = (result.stdout or "").strip()
        if result.returncode == 0 and out and out.lower().endswith('.exe'):
            return out
    except Exception:
        log.debug("PowerShell CIM lookup for desktopcal.exe failed", exc_info=True)

    # Method 2: infer from the configured DB path. db_path looks like
    # C:\...\CalendarTask\Db\calendar.db; the exe sits one directory up.
    try:
        from constants import DEFAULT_DB_PATH
        from config_manager import get_config
        db_path = get_config("db_path") or DEFAULT_DB_PATH
        calendar_task_dir = os.path.dirname(os.path.dirname(db_path))
        exe_path = os.path.join(calendar_task_dir, "desktopcal.exe")
        if os.path.exists(exe_path):
            return exe_path
    except Exception:
        log.debug("desktopcal.exe path inference from db_path failed", exc_info=True)

    return None


def restart_desktopcal() -> tuple[bool, str]:
    """Force-restart DesktopCal so it picks up DB changes.

    SAFETY: this kills DesktopCal with /F, which discards any unsaved state
    the user may have in OTHER DesktopCal panels. Therefore it only runs when
    the user opts in via `auto_restart_desktopcal: true` in config.json.
    Otherwise, returns (False, 'disabled') and the UI prompts the user to
    refresh DesktopCal manually.

    Returns (success, message).
    """
    try:
        from config_manager import get_config
        if not get_config("auto_restart_desktopcal"):
            return False, "disabled"
    except Exception:
        log.debug("Could not read auto_restart_desktopcal flag; treating as disabled",
                  exc_info=True)
        return False, "disabled"

    exe_path = _get_desktopcal_path()
    if not exe_path:
        return False, "DesktopCal path not found"

    try:
        subprocess.run(
            ['taskkill', '/IM', 'desktopcal.exe', '/F'],
            capture_output=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        time.sleep(0.5)
        subprocess.Popen(
            [exe_path],
            cwd=os.path.dirname(exe_path),
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
        )
        log.info("Restarted DesktopCal")
        return True, "DesktopCal restarted"
    except subprocess.TimeoutExpired:
        log.warning("Timeout restarting DesktopCal")
        return False, "Timeout while restarting"
    except Exception as e:
        log.exception("Failed to restart DesktopCal")
        return False, str(e)


class TaskInputWindow:
    """Floating topmost window for task input and confirmation."""
    
    # Macaron Light Blue Theme
    BG_COLOR = "#F5F9FC"          # Very light blue-gray background
    FG_COLOR = "#2C3E50"          # Dark blue-gray text
    ACCENT_COLOR = "#89CFF0"      # Macaron baby blue (primary accent)
    ACCENT_DARK = "#6BB8E0"       # Slightly darker blue (hover states)
    ACCENT_LIGHT = "#D4EEFF"      # Very pale blue (subtle highlights)
    BUTTON_BG = "#E3F2FD"         # Pale blue button background
    BUTTON_HOVER = "#BBDEFB"      # Slightly darker on hover
    BUTTON_TEXT = "#2C3E50"       # Dark text on light buttons
    ERROR_COLOR = "#E57373"       # Soft red
    SUCCESS_COLOR = "#81C784"     # Soft green
    SUCCESS_DARK = "#66BB6A"      # Darker green for hover
    BORDER_COLOR = "#B3D9F2"      # Light blue border
    TEXT_BG = "#FFFFFF"           # Pure white for text areas
    PLACEHOLDER_COLOR = "#90A4AE" # Muted gray for placeholders
    STATUS_COLOR = "#78909C"      # Blue gray for status text
    STAR_COLOR = "#FFD54F"        # Warm yellow for stars
    TITLE_BG = "#89CFF0"          # Macaron blue title bar
    TITLE_FG = "#FFFFFF"          # White text on title bar
    DISABLED_BG = "#CFD8DC"       # Gray for disabled buttons
    DISABLED_FG = "#90A4AE"       # Muted text for disabled
    
    def __init__(self, parent=None):
        """Initialize the input window.
        
        Args:
            parent: Optional tkinter parent window
        """
        self.parent = parent
        self.root = None
        self._is_shown = False
        self._drag_data = {"x": 0, "y": 0}
        self._current_view = "input"  # "input", "confirm", or "rating"
        self._ai_result = None
        self._user_input = ""
        self._interaction_id = None
        self._analyzing = False
        self._confirm_done = False
        
    def _create_window(self):
        """Create the window if it doesn't exist."""
        if self.root is not None:
            return
            
        if self.parent:
            self.root = tk.Toplevel(self.parent)
        else:
            self.root = tk.Tk()
        
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.98)
        
        # Center on screen
        width, height = 520, 420
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Border frame (1px border effect)
        self.border_frame = tk.Frame(self.root, bg=self.BORDER_COLOR)
        self.border_frame.pack(fill=tk.BOTH, expand=True)
        
        # Main container with padding for border effect
        self.main_frame = tk.Frame(self.border_frame, bg=self.BG_COLOR)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        # Build UI
        self._build_title_bar()
        self._build_input_view()
        self._build_confirm_view()
        self._build_rating_view()
        
        # Start with input view
        self._show_input_view()
        
        # Bindings
        self.root.bind('<Escape>', self._on_cancel)
        self.root.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
    def _build_title_bar(self):
        """Build custom title bar with drag support."""
        self.title_bar = tk.Frame(self.main_frame, bg=self.TITLE_BG, height=36)
        self.title_bar.pack(fill=tk.X)
        self.title_bar.pack_propagate(False)
        
        # Title label
        title_label = tk.Label(
            self.title_bar, 
            text="CalendarTaskAI",
            bg=self.TITLE_BG, 
            fg=self.TITLE_FG,
            font=("Segoe UI", 11, "bold")
        )
        title_label.pack(side=tk.LEFT, padx=12)
        
        # Close button
        self.close_btn = tk.Label(
            self.title_bar,
            text="✕",
            bg=self.TITLE_BG,
            fg=self.TITLE_FG,
            font=("Segoe UI", 13),
            cursor="hand2",
            padx=12
        )
        self.close_btn.pack(side=tk.RIGHT)
        self.close_btn.bind('<Button-1>', self._on_cancel)
        self.close_btn.bind('<Enter>', lambda e: self.close_btn.config(bg=self.ERROR_COLOR))
        self.close_btn.bind('<Leave>', lambda e: self.close_btn.config(bg=self.TITLE_BG))
        
        # Drag bindings
        for widget in [self.title_bar, title_label]:
            widget.bind('<Button-1>', self._start_drag)
            widget.bind('<B1-Motion>', self._on_drag)
            
    def _start_drag(self, event):
        """Start window dragging."""
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        
    def _on_drag(self, event):
        """Handle window dragging."""
        x = self.root.winfo_x() + (event.x - self._drag_data["x"])
        y = self.root.winfo_y() + (event.y - self._drag_data["y"])
        self.root.geometry(f"+{x}+{y}")
    
    def _create_button(self, parent, text, command, bg=None, fg=None, 
                       hover_bg=None, width=None, is_primary=False, is_success=False):
        """Create a styled button with hover effects.
        
        Args:
            parent: Parent widget
            text: Button text
            command: Click callback
            bg: Background color (default: BUTTON_BG)
            fg: Foreground color (default: BUTTON_TEXT)
            hover_bg: Hover background color
            width: Optional fixed width
            is_primary: Use accent colors
            is_success: Use success colors
            
        Returns:
            The button widget
        """
        if is_primary:
            bg = bg or self.ACCENT_COLOR
            fg = fg or "#FFFFFF"
            hover_bg = hover_bg or self.ACCENT_DARK
        elif is_success:
            bg = bg or self.SUCCESS_COLOR
            fg = fg or "#FFFFFF"
            hover_bg = hover_bg or self.SUCCESS_DARK
        else:
            bg = bg or self.BUTTON_BG
            fg = fg or self.BUTTON_TEXT
            hover_bg = hover_bg or self.BUTTON_HOVER
        
        btn = tk.Button(
            parent,
            text=text,
            bg=bg,
            fg=fg,
            activebackground=hover_bg,
            activeforeground=fg,
            font=("Segoe UI", 9),
            relief=tk.FLAT,
            padx=14,
            pady=6,
            cursor="hand2",
            command=command,
            borderwidth=0,
            highlightthickness=0
        )
        
        if width:
            btn.config(width=width)
        
        # Store original colors for hover effects
        btn._bg = bg
        btn._hover_bg = hover_bg
        btn._fg = fg
        
        # Bind hover effects
        btn.bind('<Enter>', lambda e, b=btn: self._on_button_enter(b))
        btn.bind('<Leave>', lambda e, b=btn: self._on_button_leave(b))
        
        return btn
    
    def _on_button_enter(self, btn):
        """Handle button hover enter."""
        if btn.cget('state') != tk.DISABLED:
            btn.config(bg=btn._hover_bg)
    
    def _on_button_leave(self, btn):
        """Handle button hover leave."""
        if btn.cget('state') != tk.DISABLED:
            btn.config(bg=btn._bg)
    
    def _set_button_enabled(self, btn, enabled):
        """Enable or disable a button with proper styling."""
        if enabled:
            btn.config(state=tk.NORMAL, bg=btn._bg, fg=btn._fg, cursor="hand2")
        else:
            btn.config(state=tk.DISABLED, bg=self.DISABLED_BG, fg=self.DISABLED_FG, cursor="arrow")
        
    def _build_input_view(self):
        """Build the task input view."""
        self.input_frame = tk.Frame(self.main_frame, bg=self.BG_COLOR)
        
        # CRITICAL: Pack bottom bar FIRST to reserve space, then content fills remaining
        # Bottom bar
        bottom = tk.Frame(self.input_frame, bg=self.BG_COLOR)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=(10, 15))
        
        # Status label
        self.status_label = tk.Label(
            bottom,
            text="Ready",
            bg=self.BG_COLOR,
            fg=self.STATUS_COLOR,
            font=("Segoe UI", 9),
            anchor="w"
        )
        self.status_label.pack(side=tk.LEFT)
        
        # Buttons frame
        btn_frame = tk.Frame(bottom, bg=self.BG_COLOR)
        btn_frame.pack(side=tk.RIGHT)
        
        # Clear button
        self.clear_btn = self._create_button(
            btn_frame, "Clear (Ctrl+L)", self._on_clear
        )
        self.clear_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # Paste button
        self.paste_btn = self._create_button(
            btn_frame, "Paste (Ctrl+V)", self._on_paste
        )
        self.paste_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # Cancel button
        self.cancel_btn = self._create_button(
            btn_frame, "Cancel (Esc)", self._on_cancel
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # Submit button (primary action)
        self.submit_btn = self._create_button(
            btn_frame, "Submit (Ctrl+Enter)", self._on_submit, is_primary=True
        )
        self.submit_btn.pack(side=tk.LEFT)
        
        # Content area - packed AFTER bottom bar
        content = tk.Frame(self.input_frame, bg=self.BG_COLOR)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=(15, 0))
        
        # Instructions
        instr = tk.Label(
            content,
            text="Enter your tasks below:",
            bg=self.BG_COLOR,
            fg=self.FG_COLOR,
            font=("Segoe UI", 10),
            anchor="w"
        )
        instr.pack(fill=tk.X, pady=(0, 8))
        
        # Text input with border frame
        text_border = tk.Frame(content, bg=self.BORDER_COLOR)
        text_border.pack(fill=tk.BOTH, expand=True)
        
        text_inner = tk.Frame(text_border, bg=self.TEXT_BG)
        text_inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(text_inner, bg=self.BG_COLOR, troughcolor=self.TEXT_BG)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.text = tk.Text(
            text_inner,
            bg=self.TEXT_BG,
            fg=self.FG_COLOR,
            insertbackground=self.FG_COLOR,
            font=("Segoe UI", 11),
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            relief=tk.FLAT,
            padx=12,
            pady=10,
            borderwidth=0,
            highlightthickness=0
        )
        self.text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.text.yview)
        
        # Placeholder
        self._placeholder_text = "Enter your tasks here, one per line..."
        self._show_placeholder()
        self.text.bind('<FocusIn>', self._on_text_focus_in)
        self.text.bind('<FocusOut>', self._on_text_focus_out)
        self.text.bind('<Control-Return>', self._on_submit)
            
    def _build_confirm_view(self):
        """Build the confirmation view."""
        self.confirm_frame = tk.Frame(self.main_frame, bg=self.BG_COLOR)
        
        # CRITICAL: Pack bottom bar FIRST to reserve space
        # Bottom bar
        bottom = tk.Frame(self.confirm_frame, bg=self.BG_COLOR)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=(10, 15))
        
        # Status
        self.confirm_status = tk.Label(
            bottom,
            text="",
            bg=self.BG_COLOR,
            fg=self.STATUS_COLOR,
            font=("Segoe UI", 9),
            anchor="w"
        )
        self.confirm_status.pack(side=tk.LEFT)
        
        # Buttons
        btn_frame = tk.Frame(bottom, bg=self.BG_COLOR)
        btn_frame.pack(side=tk.RIGHT)
        
        # Edit button - go back to input view
        self.edit_btn = self._create_button(
            btn_frame, "Edit (Ctrl+E)", self._on_edit
        )
        self.edit_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # Cancel/Reject button
        self.reject_btn = self._create_button(
            btn_frame, "Cancel (Esc)", self._on_reject
        )
        self.reject_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # Confirm button (success action)
        self.confirm_btn = self._create_button(
            btn_frame, "Confirm (Enter)", self._on_confirm, is_success=True
        )
        self.confirm_btn.pack(side=tk.LEFT)
        
        # Content area - packed AFTER bottom bar
        content = tk.Frame(self.confirm_frame, bg=self.BG_COLOR)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=(15, 0))
        
        # Header row with title and copy button
        header_row = tk.Frame(content, bg=self.BG_COLOR)
        header_row.pack(fill=tk.X, pady=(0, 10))
        
        header = tk.Label(
            header_row,
            text="AI Task Allocation",
            bg=self.BG_COLOR,
            fg=self.FG_COLOR,
            font=("Segoe UI", 12, "bold"),
            anchor="w"
        )
        header.pack(side=tk.LEFT)
        
        # Copy button in header
        self.copy_btn = self._create_button(
            header_row, "Copy (Ctrl+C)", self._on_copy
        )
        self.copy_btn.pack(side=tk.RIGHT)
        
        # Task list frame with border
        list_border = tk.Frame(content, bg=self.BORDER_COLOR)
        list_border.pack(fill=tk.BOTH, expand=True)
        
        list_inner = tk.Frame(list_border, bg=self.TEXT_BG)
        list_inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        scrollbar = tk.Scrollbar(list_inner, bg=self.BG_COLOR, troughcolor=self.TEXT_BG)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.task_list = tk.Text(
            list_inner,
            bg=self.TEXT_BG,
            fg=self.FG_COLOR,
            font=("Consolas", 10),
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            relief=tk.FLAT,
            padx=12,
            pady=10,
            state=tk.DISABLED,
            borderwidth=0,
            highlightthickness=0
        )
        self.task_list.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.task_list.yview)
        
    def _build_rating_view(self):
        """Build the rating view."""
        self.rating_frame = tk.Frame(self.main_frame, bg=self.BG_COLOR)
        
        # CRITICAL: Pack bottom bar FIRST to reserve space
        # Bottom bar with Skip button
        bottom = tk.Frame(self.rating_frame, bg=self.BG_COLOR)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=(10, 15))
        
        # Skip button centered in bottom
        self.skip_btn = self._create_button(
            bottom, "Skip (Esc)", self._close
        )
        self.skip_btn.pack()
        
        # Content - packed AFTER bottom bar
        content = tk.Frame(self.rating_frame, bg=self.BG_COLOR)
        content.pack(expand=True)
        
        # Message
        msg = tk.Label(
            content,
            text="How satisfied are you with this allocation?",
            bg=self.BG_COLOR,
            fg=self.FG_COLOR,
            font=("Segoe UI", 12)
        )
        msg.pack(pady=(0, 25))
        
        # Rating hint
        hint = tk.Label(
            content,
            text="Press 1-5 to rate quickly",
            bg=self.BG_COLOR,
            fg=self.STATUS_COLOR,
            font=("Segoe UI", 9)
        )
        hint.pack(pady=(0, 10))
        
        # Star buttons
        stars_frame = tk.Frame(content, bg=self.BG_COLOR)
        stars_frame.pack()
        
        self.star_buttons = []
        for i in range(1, 6):
            btn = tk.Button(
                stars_frame,
                text="★",
                bg=self.BG_COLOR,
                fg=self.STATUS_COLOR,
                activebackground=self.BG_COLOR,
                activeforeground=self.STAR_COLOR,
                font=("Segoe UI", 24),
                relief=tk.FLAT,
                width=2,
                cursor="hand2",
                command=lambda r=i: self._on_rate(r),
                borderwidth=0,
                highlightthickness=0
            )
            btn.pack(side=tk.LEFT, padx=5)
            btn.bind('<Enter>', lambda e, b=btn, n=i: self._highlight_stars(n))
            btn.bind('<Leave>', lambda e: self._reset_stars())
            self.star_buttons.append(btn)
        
    def _highlight_stars(self, n):
        """Highlight stars up to n."""
        for i, btn in enumerate(self.star_buttons):
            if i < n:
                btn.config(fg=self.STAR_COLOR)
            else:
                btn.config(fg=self.STATUS_COLOR)
                
    def _reset_stars(self):
        """Reset star colors."""
        for btn in self.star_buttons:
            btn.config(fg=self.STATUS_COLOR)
    
    # ==================== Keyboard Shortcuts ====================
    
    def _bind_input_shortcuts(self):
        """Bind keyboard shortcuts for input view."""
        self.root.bind('<Control-l>', lambda e: self._on_clear())
        self.root.bind('<Control-L>', lambda e: self._on_clear())
        # Note: Ctrl+V is handled natively by Text widget
        # Ctrl+Enter already bound in text widget
        
    def _unbind_input_shortcuts(self):
        """Unbind input view shortcuts."""
        self.root.unbind('<Control-l>')
        self.root.unbind('<Control-L>')
        
    def _bind_confirm_shortcuts(self):
        """Bind keyboard shortcuts for confirm view."""
        self.root.bind('<Return>', lambda e: self._on_confirm_key())
        self.root.bind('<Control-Return>', lambda e: self._on_confirm_key())
        self.root.bind('<Control-e>', lambda e: self._on_edit())
        self.root.bind('<Control-E>', lambda e: self._on_edit())
        self.root.bind('<Control-c>', lambda e: self._on_copy_key())
        self.root.bind('<Control-C>', lambda e: self._on_copy_key())
        
    def _unbind_confirm_shortcuts(self):
        """Unbind confirm view shortcuts."""
        self.root.unbind('<Return>')
        self.root.unbind('<Control-Return>')
        self.root.unbind('<Control-e>')
        self.root.unbind('<Control-E>')
        self.root.unbind('<Control-c>')
        self.root.unbind('<Control-C>')
        
    def _bind_rating_shortcuts(self):
        """Bind keyboard shortcuts for rating view."""
        self.root.bind('<Return>', lambda e: self._close())
        for i in range(1, 6):
            self.root.bind(str(i), lambda e, r=i: self._on_rate(r))
            
    def _unbind_rating_shortcuts(self):
        """Unbind rating view shortcuts."""
        self.root.unbind('<Return>')
        for i in range(1, 6):
            self.root.unbind(str(i))
    
    def _on_confirm_key(self):
        """Handle confirm via keyboard (checks if enabled)."""
        if not self._confirm_done:
            self._on_confirm()
            
    def _on_copy_key(self):
        """Handle copy via keyboard and prevent event propagation."""
        self._on_copy()
        return "break"  # Prevent default Ctrl+C behavior
            
    def _show_placeholder(self):
        """Show placeholder text."""
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", self._placeholder_text)
        self.text.config(fg=self.PLACEHOLDER_COLOR)
        
    def _on_text_focus_in(self, event=None):
        """Clear placeholder on focus."""
        if self.text.get("1.0", "end-1c") == self._placeholder_text:
            self.text.delete("1.0", tk.END)
            self.text.config(fg=self.FG_COLOR)
            
    def _on_text_focus_out(self, event=None):
        """Restore placeholder if empty."""
        if not self.text.get("1.0", "end-1c").strip():
            self._show_placeholder()
    
    def _on_clear(self):
        """Clear the text input area."""
        self.text.delete("1.0", tk.END)
        self._show_placeholder()
        self.text.focus_set()
    
    def _on_paste(self):
        """Paste clipboard content into text area."""
        try:
            # Clear placeholder if present
            if self.text.get("1.0", "end-1c") == self._placeholder_text:
                self.text.delete("1.0", tk.END)
                self.text.config(fg=self.FG_COLOR)
            
            clipboard_text = self.root.clipboard_get()
            self.text.insert(tk.END, clipboard_text)
            self.text.focus_set()
        except tk.TclError:
            # Clipboard is empty or contains non-text data
            self._set_status("Clipboard is empty", self.ERROR_COLOR)
    
    def _on_edit(self):
        """Go back to input view with original text preserved."""
        self._show_input_view()
        # Restore the original user input
        self.text.config(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        if self._user_input:
            self.text.insert("1.0", self._user_input)
            self.text.config(fg=self.FG_COLOR)
        else:
            self._show_placeholder()
        self._set_status("Ready")
        self._set_input_enabled(True)
        self.text.focus_set()
    
    def _on_copy(self):
        """Copy the AI allocation result to clipboard."""
        if self._ai_result:
            lines = []
            for task in self._ai_result:
                lines.append(f"{task['date']}  {task['task']}")
            text = "\n".join(lines)
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.confirm_status.config(text="Copied to clipboard!", fg=self.SUCCESS_COLOR)
            # Reset status after a moment
            self.root.after(2000, lambda: self.confirm_status.config(
                text=f"{len(self._ai_result)} task(s) to be added", fg=self.STATUS_COLOR
            ) if self._current_view == "confirm" and not self._confirm_done else None)
            
    def _show_input_view(self):
        """Show the input view."""
        self.confirm_frame.pack_forget()
        self.rating_frame.pack_forget()
        self.input_frame.pack(fill=tk.BOTH, expand=True)
        self._current_view = "input"
        # Update keyboard shortcuts
        self._unbind_confirm_shortcuts()
        self._unbind_rating_shortcuts()
        self._bind_input_shortcuts()
        
    def _show_confirm_view(self):
        """Show the confirmation view."""
        self.input_frame.pack_forget()
        self.rating_frame.pack_forget()
        self.confirm_frame.pack(fill=tk.BOTH, expand=True)
        self._current_view = "confirm"
        # Update keyboard shortcuts
        self._unbind_input_shortcuts()
        self._unbind_rating_shortcuts()
        self._bind_confirm_shortcuts()
        
    def _show_rating_view(self):
        """Show the rating view."""
        self.input_frame.pack_forget()
        self.confirm_frame.pack_forget()
        self.rating_frame.pack(fill=tk.BOTH, expand=True)
        self._current_view = "rating"
        # Update keyboard shortcuts
        self._unbind_input_shortcuts()
        self._unbind_confirm_shortcuts()
        self._bind_rating_shortcuts()
        
    def _set_status(self, text, color=None):
        """Update status label."""
        self.status_label.config(text=text, fg=color or self.STATUS_COLOR)
        
    def _set_input_enabled(self, enabled):
        """Enable or disable input controls."""
        self._analyzing = not enabled
        state = tk.NORMAL if enabled else tk.DISABLED
        self.text.config(state=state)
        self._set_button_enabled(self.submit_btn, enabled)
        self._set_button_enabled(self.clear_btn, enabled)
        self._set_button_enabled(self.paste_btn, enabled)
        
    def _animate_analyzing(self):
        """Animate the analyzing status with dots."""
        if self._analyzing and self._current_view == "input":
            current = self.status_label.cget("text")
            if current.startswith("Analyzing"):
                dots = current.count(".")
                dots = (dots % 3) + 1
                self.status_label.config(text="Analyzing" + "." * dots)
                self.root.after(400, self._animate_analyzing)
        
    def _on_submit(self, event=None):
        """Handle submit button click."""
        text = self.text.get("1.0", "end-1c").strip()
        if not text or text == self._placeholder_text:
            self._set_status("Please enter at least one task.", self.ERROR_COLOR)
            return
            
        # Check if configured
        from config_manager import is_configured
        if not is_configured():
            self._set_status("Error: API key not configured.", self.ERROR_COLOR)
            return
        
        self._user_input = text
        self._set_status("Analyzing...", self.ACCENT_COLOR)
        self._set_input_enabled(False)
        self._animate_analyzing()
        
        # Run AI call in background thread
        threading.Thread(target=self._call_ai, args=(text,), daemon=True).start()
        
    def _call_ai(self, text):
        """Call AI to analyze tasks (runs in background thread)."""
        try:
            from config_manager import load_config
            from ai_client import analyze_tasks
            
            config = load_config()
            result = analyze_tasks(text, config)
            self.root.after(0, self._show_confirm, text, result)
        except Exception as e:
            from retry_queue import save_pending
            save_pending(text)
            self.root.after(0, self._show_error, str(e))
            
    def _show_confirm(self, user_input, result):
        """Show confirmation dialog with AI results."""
        self._ai_result = result
        self._user_input = user_input
        self._confirm_done = False
        self._analyzing = False
        
        # Populate task list
        self.task_list.config(state=tk.NORMAL)
        self.task_list.delete("1.0", tk.END)
        
        # Header
        self.task_list.insert(tk.END, f"{'Date':<14}Task\n")
        self.task_list.insert(tk.END, "─" * 45 + "\n")
        
        # Tasks
        for task in result:
            self.task_list.insert(tk.END, f"{task['date']:<14}{task['task']}\n")
            
        self.task_list.config(state=tk.DISABLED)
        self.confirm_status.config(text=f"{len(result)} task(s) to be added", fg=self.STATUS_COLOR)
        
        # Enable confirm view buttons
        self._set_button_enabled(self.confirm_btn, True)
        self._set_button_enabled(self.reject_btn, True)
        self._set_button_enabled(self.edit_btn, True)
        self._set_button_enabled(self.copy_btn, True)
        
        self._show_confirm_view()
        
    def _show_error(self, error_msg):
        """Show error message and re-enable input."""
        self._analyzing = False
        self._set_status(f"Error: {error_msg}", self.ERROR_COLOR)
        self._set_input_enabled(True)
        
    def _on_confirm(self):
        """Handle confirm button click."""
        if not self._ai_result or self._confirm_done:
            return
            
        try:
            from calendar_db import write_tasks
            from history import log_interaction, should_ask_rating
            
            # Disable buttons immediately to prevent double-click
            self._confirm_done = True
            self._set_button_enabled(self.confirm_btn, False)
            self._set_button_enabled(self.reject_btn, False)
            self._set_button_enabled(self.edit_btn, False)
            
            # Write to database
            count = write_tasks(self._ai_result)
            
            # Log interaction
            self._interaction_id = log_interaction(
                self._user_input, 
                self._ai_result, 
                accepted_tasks=self._ai_result
            )
            
            # Show success message; whether DesktopCal auto-refreshes depends on
            # the auto_restart_desktopcal config flag (off by default, see ui.restart_desktopcal).
            self.confirm_status.config(
                text=f"Tasks written! ({count} added) - Switch DesktopCal pages to refresh",
                fg=self.SUCCESS_COLOR
            )

            def do_restart():
                success, msg = restart_desktopcal()
                if msg == "disabled":
                    return  # leave the existing manual-refresh message
                def update_status():
                    if success:
                        self.confirm_status.config(
                            text=f"Tasks written! ({count} added) - Calendar refreshed",
                            fg=self.SUCCESS_COLOR
                        )
                    else:
                        self.confirm_status.config(
                            text=f"Tasks written! ({count} added) - Please refresh DesktopCal manually",
                            fg=self.STATUS_COLOR
                        )
                if self.root:
                    self.root.after(0, update_status)

            threading.Thread(target=do_restart, daemon=True).start()
            
            # Check if should ask for rating
            if should_ask_rating():
                self.root.after(2500, self._show_rating_view)
            else:
                self.root.after(2500, self._close)
                
        except Exception as e:
            self._confirm_done = False
            self._set_button_enabled(self.confirm_btn, True)
            self._set_button_enabled(self.reject_btn, True)
            self._set_button_enabled(self.edit_btn, True)
            self.confirm_status.config(text=f"Error: {e}", fg=self.ERROR_COLOR)
            
    def _on_reject(self):
        """Handle reject/cancel button click."""
        if self._ai_result:
            from history import log_interaction
            log_interaction(
                self._user_input,
                self._ai_result,
                accepted_tasks=[],
                rejected_tasks=self._ai_result
            )
        self._close()
        
    def _on_rate(self, rating):
        """Handle rating selection."""
        from history import save_rating
        save_rating(rating, self._interaction_id)
        self._close()
        
    def _on_cancel(self, event=None):
        """Handle cancel/close."""
        if self._current_view == "confirm" and self._ai_result and not self._confirm_done:
            self._on_reject()
        else:
            self._close()
            
    def _close(self):
        """Close/hide the window."""
        if self.root:
            self.root.withdraw()
            self._is_shown = False
            self._reset_state()
            
    def _reset_state(self):
        """Reset window state for next use."""
        self._ai_result = None
        self._user_input = ""
        self._interaction_id = None
        self._analyzing = False
        self._confirm_done = False
        
        # Reset input view
        self.text.config(state=tk.NORMAL, fg=self.FG_COLOR)
        self.text.delete("1.0", tk.END)
        self._show_placeholder()
        self._set_status("Ready")
        self._set_input_enabled(True)
        
        # Reset confirm view buttons
        self._set_button_enabled(self.confirm_btn, True)
        self._set_button_enabled(self.reject_btn, True)
        self._set_button_enabled(self.edit_btn, True)
        self._set_button_enabled(self.copy_btn, True)
        self._reset_stars()
        
        # Show input view
        self._show_input_view()
        
    def show(self):
        """Thread-safe method to show the input window."""
        if self.parent:
            self.parent.after(0, self._do_show)
        else:
            self._do_show()
            
    def _do_show(self):
        """Actually show the window (must be called from main thread)."""
        self._create_window()
        
        if not self._is_shown:
            # Re-center on screen
            self.root.update_idletasks()
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            x = (screen_w - width) // 2
            y = (screen_h - height) // 2
            self.root.geometry(f"+{x}+{y}")
            
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.text.focus_set()
        self._is_shown = True
        
    def destroy(self):
        """Destroy the window completely."""
        if self.root:
            self.root.destroy()
            self.root = None
            self._is_shown = False


if __name__ == "__main__":
    # Test the window
    root = tk.Tk()
    root.withdraw()
    
    window = TaskInputWindow(root)
    window.show()
    
    root.mainloop()
