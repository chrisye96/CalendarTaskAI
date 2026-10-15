"""Tests for tray.py.

Regression: the template submenu used `lambda icon, item, txt=text:`,
which pystray rejects (co_argcount 3 > 2), crashing the tray at startup
whenever templates.json had entries.
"""
from unittest.mock import MagicMock

import tray


def test_template_submenu_builds_and_binds_each_text(monkeypatch):
    import templates
    monkeypatch.setattr(templates, "load_templates", lambda: [
        {"name": "Standup", "text": "daily standup"},
        {"name": "Gym", "text": "every monday gym"},
    ])
    mgr = tray.TrayManager(MagicMock(), MagicMock())
    selected = []
    monkeypatch.setattr(mgr, "_on_template_selected", selected.append)

    menu = mgr._build_templates_submenu()
    for item in menu.items:
        item(None)

    assert [i.text for i in menu.items] == ["Standup", "Gym"]
    assert selected == ["daily standup", "every monday gym"]
