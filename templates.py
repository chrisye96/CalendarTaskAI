"""Task input templates: pre-canned text snippets the user can drop into
the input window with one click.

A template is just `{name, text, builtin?}`. The built-ins ship with the app
and are seeded into `data/templates.json` on first read; users edit that
file directly to add custom templates (no UI for it in Phase 3 — keeps the
surface small).

Round-trip behavior:
  * On first read, if templates.json doesn't exist, write the built-ins.
  * If templates.json exists, return whatever's in it (don't re-merge
    built-ins; users may have intentionally removed one).
  * If the user wants the built-ins back, deleting templates.json rebuilds
    them on next launch.
"""
from __future__ import annotations

import json
import os

from constants import DATA_DIR, TEMPLATES_PATH
from logger import get_logger

log = get_logger(__name__)


# Each template is shown by `name` in the tray submenu and dropped into the
# input window verbatim by `text`. Multi-line values are encouraged: each
# line becomes a separate task once the user submits.
BUILTIN_TEMPLATES: list[dict] = [
    {
        "name": "Standup",
        "builtin": True,
        "text": "昨天完成: \n今天计划: \n阻塞: ",
    },
    {
        "name": "周报",
        "builtin": True,
        "text": "本周进展: \n下周计划: \n风险与依赖: ",
    },
    {
        "name": "Sprint planning",
        "builtin": True,
        "text": "Sprint 目标: \n本期故事: \n人力分配: ",
    },
    {
        "name": "健身计划",
        "builtin": True,
        "text": "周一 推日 (胸/肩/三头)\n周三 拉日 (背/二头)\n周五 腿日",
    },
    {
        "name": "读书清单",
        "builtin": True,
        "text": "正在读: \n计划读: \n已读: ",
    },
]


def _ensure_dir() -> None:
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)


def load_templates() -> list[dict]:
    """Return the templates list. Seeds the file with builtins on first call."""
    _ensure_dir()
    if not os.path.exists(TEMPLATES_PATH):
        save_templates(BUILTIN_TEMPLATES)
        return list(BUILTIN_TEMPLATES)

    try:
        with open(TEMPLATES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        log.warning("templates.json is not a list; falling back to builtins")
    except Exception:
        log.exception("Failed to read templates.json; falling back to builtins")

    return list(BUILTIN_TEMPLATES)


def save_templates(templates: list[dict]) -> None:
    """Write templates back to disk."""
    _ensure_dir()
    try:
        with open(TEMPLATES_PATH, "w", encoding="utf-8") as f:
            json.dump(templates, f, ensure_ascii=False, indent=2)
    except Exception:
        log.exception("Failed to save templates.json")
