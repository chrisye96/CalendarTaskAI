"""Tests for main.py GUI startup failure reporting.

Under pythonw a crash during startup is invisible unless it reaches the log,
so the traceback must end up in a log record.
"""
import logging
import sys

import main


def test_startup_failure_logs_traceback(monkeypatch, caplog):
    # Skip the native MessageBoxW so the test never blocks on a dialog.
    monkeypatch.setattr(sys, "platform", "linux")
    try:
        raise RuntimeError("tray exploded")
    except RuntimeError:
        with caplog.at_level(logging.ERROR):
            main._report_gui_startup_failure("startup failed")

    record = next(r for r in caplog.records if r.getMessage() == "startup failed")
    assert record.exc_info and record.exc_info[1].args == ("tray exploded",)
