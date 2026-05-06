r"""Smoke + unit tests for Phase 3a modules.

Each test points the module at a temp directory via monkeypatch so it
doesn't poke the user's real %APPDATA%\CalendarTaskAI data.
"""
import json
from pathlib import Path

import pytest

import last_op
import templates


# ---------------------------------------------------------------------------
# last_op
# ---------------------------------------------------------------------------

class TestLastOp:
    @pytest.fixture(autouse=True)
    def isolated_paths(self, tmp_path, monkeypatch):
        monkeypatch.setattr(last_op, "DATA_DIR", str(tmp_path))
        monkeypatch.setattr(last_op, "LAST_OP_PATH", str(tmp_path / "last_op.json"))

    def test_peek_returns_none_when_empty(self):
        assert last_op.peek_last() is None

    def test_record_then_peek_round_trips(self):
        items = [{"date": "2026-05-05", "task": "buy groceries"}]
        last_op.record_last_add(items)
        record = last_op.peek_last()
        assert record is not None
        assert record["tasks"] == items
        assert "timestamp" in record

    def test_record_empty_is_a_no_op(self):
        last_op.record_last_add([])
        assert last_op.peek_last() is None

    def test_clear_removes_record(self):
        last_op.record_last_add([{"date": "2026-05-05", "task": "x"}])
        last_op.clear()
        assert last_op.peek_last() is None

    def test_undo_with_no_record_returns_zero(self):
        count, msg = last_op.undo_last_add()
        assert count == 0
        assert "Nothing to undo" in msg


# ---------------------------------------------------------------------------
# templates
# ---------------------------------------------------------------------------

class TestTemplates:
    @pytest.fixture(autouse=True)
    def isolated_paths(self, tmp_path, monkeypatch):
        monkeypatch.setattr(templates, "DATA_DIR", str(tmp_path))
        monkeypatch.setattr(templates, "TEMPLATES_PATH", str(tmp_path / "templates.json"))

    def test_first_load_seeds_builtins(self, tmp_path):
        loaded = templates.load_templates()
        assert len(loaded) == len(templates.BUILTIN_TEMPLATES)
        names = {t["name"] for t in loaded}
        assert "Standup" in names
        # File should exist now.
        assert (tmp_path / "templates.json").exists()

    def test_subsequent_load_returns_user_edits(self, tmp_path):
        # Pretend the user removed all builtins and added a custom one.
        custom = [{"name": "My template", "text": "do the thing"}]
        templates.save_templates(custom)
        assert templates.load_templates() == custom

    def test_corrupt_file_falls_back_to_builtins(self, tmp_path):
        (tmp_path / "templates.json").write_text("not json", encoding="utf-8")
        loaded = templates.load_templates()
        assert any(t["name"] == "Standup" for t in loaded)

    def test_non_list_file_falls_back_to_builtins(self, tmp_path):
        (tmp_path / "templates.json").write_text(json.dumps({"a": 1}), encoding="utf-8")
        loaded = templates.load_templates()
        assert any(t["name"] == "Standup" for t in loaded)


# ---------------------------------------------------------------------------
# backup (without DB; we mock get_tasks_in_range)
# ---------------------------------------------------------------------------

class TestBackup:
    @pytest.fixture(autouse=True)
    def isolated_paths(self, tmp_path, monkeypatch):
        # Repoint ALL the file paths that backup.py reads from.
        import backup
        import config_manager
        import calendar_db

        # Simulate a user data dir
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        monkeypatch.setattr(backup, "PROFILE_PATH", str(data_dir / "profile.md"))
        monkeypatch.setattr(backup, "HISTORY_PATH", str(data_dir / "history.json"))
        monkeypatch.setattr(backup, "TEMPLATES_PATH", str(data_dir / "templates.json"))
        monkeypatch.setattr(backup, "RECURRING_PATH", str(data_dir / "recurring.json"))
        monkeypatch.setattr(backup, "CONFIG_PATH", str(data_dir / "config.json"))
        monkeypatch.setattr(config_manager, "DATA_DIR", str(data_dir))
        monkeypatch.setattr(config_manager, "CONFIG_PATH", str(data_dir / "config.json"))

        # No DB -> empty tasks
        monkeypatch.setattr(calendar_db, "get_tasks_in_range",
                            lambda *_a, **_kw: {})

        # Seed some user data
        (data_dir / "profile.md").write_text("# my profile\n- role: dev", encoding="utf-8")
        (data_dir / "history.json").write_text(
            json.dumps({"interactions": [{"id": "x"}], "modifications": [], "operations_count": 1}),
            encoding="utf-8",
        )
        (data_dir / "templates.json").write_text(
            json.dumps([{"name": "T1", "text": "..."}]), encoding="utf-8"
        )
        # Config with API keys to verify redaction
        config_manager.save_config({
            "llm_provider": "gemini",
            "gemini_api_key": "secret-gemini-key",
            "deepseek_api_key": "secret-deepseek-key",
            "hotkey": "ctrl+alt+space",
        })

    def test_create_backup_includes_all_sections(self):
        from backup import create_backup
        b = create_backup()
        assert b["schema_version"] == 1
        assert "created_at" in b
        assert "app_version" in b
        assert b["profile"].startswith("# my profile")
        assert b["history"]["operations_count"] == 1
        assert b["templates"][0]["name"] == "T1"
        assert b["recurring"] == []
        assert b["tasks"] == {}

    def test_api_keys_are_redacted(self):
        from backup import create_backup, REDACTED_TOKEN
        b = create_backup()
        assert b["config"]["gemini_api_key"] == REDACTED_TOKEN
        assert b["config"]["deepseek_api_key"] == REDACTED_TOKEN
        # Non-secret fields preserved verbatim.
        assert b["config"]["llm_provider"] == "gemini"
        assert b["config"]["hotkey"] == "ctrl+alt+space"

    def test_restore_overwrites_profile_history_templates(self, tmp_path):
        from backup import create_backup, restore_backup

        # Create a backup of the seeded state, then mutate state, then restore.
        b = create_backup()

        # Mutate
        import backup
        Path(backup.PROFILE_PATH).write_text("DIFFERENT", encoding="utf-8")
        Path(backup.TEMPLATES_PATH).write_text(json.dumps([{"name": "OTHER"}]), encoding="utf-8")

        counts = restore_backup(b)
        assert counts["profile"] == 1
        assert counts["history"] == 1
        assert counts["templates"] == 1

        assert Path(backup.PROFILE_PATH).read_text(encoding="utf-8").startswith("# my profile")
        assert "T1" in Path(backup.TEMPLATES_PATH).read_text(encoding="utf-8")

    def test_restore_preserves_existing_api_keys_when_overwrite_config(self):
        from backup import create_backup, restore_backup
        from config_manager import load_config

        b = create_backup()
        # Sanity: backup has REDACTED tokens
        from backup import REDACTED_TOKEN
        assert b["config"]["gemini_api_key"] == REDACTED_TOKEN

        restore_backup(b, overwrite_config=True)

        # After restore the local config still has the real keys
        cfg = load_config()
        assert cfg["gemini_api_key"] == "secret-gemini-key"
        assert cfg["deepseek_api_key"] == "secret-deepseek-key"

    def test_restore_rejects_unknown_schema_version(self):
        from backup import restore_backup
        with pytest.raises(ValueError, match="schema_version"):
            restore_backup({"schema_version": 99})


# ---------------------------------------------------------------------------
# task_parser integration: time-of-day prefix attaches to resolved + unresolved
# ---------------------------------------------------------------------------

class TestTimePipeline:
    """End-to-end: preprocess_input should attach [HH:MM] prefixes for tasks
    that have BOTH a date hint and a time hint, AND for tasks that only have
    a time hint (those land in unresolved with the prefix already in place)."""

    def test_date_and_time_combined(self):
        from datetime import date
        from task_parser import preprocess_input
        ref = date(2026, 5, 5)
        resolved, unresolved, recurring = preprocess_input("明天9点开会", ref)
        assert resolved == [{"date": "2026-05-06", "task": "[09:00] 开会"}]
        assert unresolved == []
        assert recurring == []

    def test_time_only_lands_unresolved_with_prefix(self):
        from datetime import date
        from task_parser import preprocess_input
        ref = date(2026, 5, 5)
        _, unresolved, _ = preprocess_input("9点开会", ref)
        assert unresolved == ["[09:00] 开会"]

    def test_range_through_pipeline(self):
        from datetime import date
        from task_parser import preprocess_input
        ref = date(2026, 5, 5)
        resolved, _, _ = preprocess_input("今天 上午10-11点 sprint review", ref)
        assert resolved == [{"date": "2026-05-05", "task": "[10:00-11:00] sprint review"}]
