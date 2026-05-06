"""Unit tests for recurring task rules.

Reference date for expansion tests: 2026-05-05 (Tuesday).
"""
import json
from datetime import date
from pathlib import Path

import pytest

import recurring
from recurring import (
    PRE_EXPAND_WEEKS,
    expand_rule,
    extend_all,
    load_rules,
    parse_recurring_rule,
    register_rule,
    save_rules,
)

REF = date(2026, 5, 5)  # Tuesday


# ---------------------------------------------------------------------------
# parse_recurring_rule
# ---------------------------------------------------------------------------

class TestParseChineseWeekly:
    def test_single_weekday(self):
        rule = parse_recurring_rule("每周一健身房")
        assert rule is not None
        assert rule["kind"] == "weekly"
        assert rule["weekdays"] == [0]
        assert rule["task_text"] == "健身房"
        assert rule["time_prefix"] is None

    def test_with_time_prefix(self):
        rule = parse_recurring_rule("每周一 9点 standup")
        assert rule is not None
        assert rule["weekdays"] == [0]
        assert rule["time_prefix"] == "[09:00]"
        assert rule["task_text"] == "standup"

    def test_with_time_range(self):
        rule = parse_recurring_rule("每周三 上午10-11点 团队会议")
        assert rule is not None
        assert rule["weekdays"] == [2]
        assert rule["time_prefix"] == "[10:00-11:00]"
        assert rule["task_text"] == "团队会议"

    def test_glued_weekdays(self):
        rule = parse_recurring_rule("每周一三五 健身")
        assert rule is not None
        assert rule["weekdays"] == [0, 2, 4]

    def test_comma_separated_weekdays(self):
        rule = parse_recurring_rule("每周一、三、五 健身")
        assert rule is not None
        assert rule["weekdays"] == [0, 2, 4]

    def test_dedupes_repeated_weekdays(self):
        rule = parse_recurring_rule("每周一、一 健身")
        assert rule is not None
        assert rule["weekdays"] == [0]

    def test_sunday_via_tian(self):
        rule = parse_recurring_rule("每周天 散步")
        assert rule is not None
        assert rule["weekdays"] == [6]

    def test_sunday_via_ri(self):
        rule = parse_recurring_rule("每周日 散步")
        assert rule is not None
        assert rule["weekdays"] == [6]

    def test_no_body_returns_none(self):
        assert parse_recurring_rule("每周一") is None

    def test_only_time_no_task_returns_none(self):
        # 时间 present but task body empty
        assert parse_recurring_rule("每周一 9点") is None


class TestParseChineseMonthly:
    def test_single_day(self):
        rule = parse_recurring_rule("每月15号 交房租")
        assert rule is not None
        assert rule["kind"] == "monthly"
        assert rule["days_of_month"] == [15]
        assert rule["task_text"] == "交房租"

    def test_with_ri_suffix(self):
        rule = parse_recurring_rule("每月1日 报销")
        assert rule is not None
        assert rule["days_of_month"] == [1]

    def test_with_time(self):
        rule = parse_recurring_rule("每月1号 上午9点 团队会议")
        assert rule is not None
        assert rule["days_of_month"] == [1]
        assert rule["time_prefix"] == "[09:00]"

    def test_invalid_day_returns_none(self):
        assert parse_recurring_rule("每月32号 X") is None

    def test_no_body_returns_none(self):
        assert parse_recurring_rule("每月15号") is None


class TestParseEnglishWeekly:
    def test_every_monday(self):
        rule = parse_recurring_rule("every monday standup")
        assert rule is not None
        assert rule["kind"] == "weekly"
        assert rule["weekdays"] == [0]
        assert rule["task_text"] == "standup"

    def test_every_short_day(self):
        rule = parse_recurring_rule("every fri team review")
        assert rule is not None
        assert rule["weekdays"] == [4]

    def test_weekly_keyword(self):
        rule = parse_recurring_rule("weekly tuesday 1:1")
        assert rule is not None
        assert rule["weekdays"] == [1]

    def test_with_time(self):
        rule = parse_recurring_rule("every monday 9am standup")
        assert rule is not None
        assert rule["weekdays"] == [0]
        assert rule["time_prefix"] == "[09:00]"

    def test_case_insensitive(self):
        rule = parse_recurring_rule("Every Wednesday Sync")
        assert rule is not None
        assert rule["weekdays"] == [2]


class TestParseNegative:
    @pytest.mark.parametrize("text", [
        "",
        "买菜",
        "明天买菜",
        "下周一开会",  # one-shot, not recurring (no 每)
        "每年生日",     # not weekly/monthly
        "every once in a while",
    ])
    def test_returns_none(self, text):
        assert parse_recurring_rule(text) is None


# ---------------------------------------------------------------------------
# expand_rule
# ---------------------------------------------------------------------------

class TestExpandWeekly:
    def _rule(self, weekdays, *, time_prefix=None, task_text="task"):
        return {
            "id": "x", "kind": "weekly", "weekdays": weekdays,
            "time_prefix": time_prefix, "task_text": task_text,
        }

    def test_single_weekday_2_weeks(self):
        # REF=Tue 2026-05-05; want every Monday for 14 days
        rule = self._rule([0])  # Monday
        instances = expand_rule(rule, REF, date(2026, 5, 18))
        assert [i["date"] for i in instances] == ["2026-05-11", "2026-05-18"]

    def test_today_matches_when_weekday_is_today(self):
        # Tuesday == REF.weekday() == 1
        rule = self._rule([1])
        instances = expand_rule(rule, REF, REF)
        assert instances == [{"date": "2026-05-05", "task": "task"}]

    def test_multiple_weekdays(self):
        # Mon + Wed + Fri for 7 days starting Tue
        rule = self._rule([0, 2, 4])
        instances = expand_rule(rule, REF, date(2026, 5, 11))
        assert [i["date"] for i in instances] == [
            "2026-05-06",  # Wed
            "2026-05-08",  # Fri
            "2026-05-11",  # Mon
        ]

    def test_time_prefix_attaches(self):
        rule = self._rule([0], time_prefix="[09:00]", task_text="standup")
        instances = expand_rule(rule, date(2026, 5, 11), date(2026, 5, 11))
        assert instances == [{"date": "2026-05-11", "task": "[09:00] standup"}]

    def test_inverted_range_is_empty(self):
        rule = self._rule([0])
        assert expand_rule(rule, date(2026, 5, 18), date(2026, 5, 11)) == []

    def test_no_weekdays_is_empty(self):
        rule = self._rule([])
        assert expand_rule(rule, REF, date(2026, 5, 18)) == []


class TestExpandMonthly:
    def _rule(self, days, *, time_prefix=None, task_text="rent"):
        return {
            "id": "x", "kind": "monthly", "days_of_month": days,
            "time_prefix": time_prefix, "task_text": task_text,
        }

    def test_single_day_across_months(self):
        rule = self._rule([15])
        instances = expand_rule(rule, REF, date(2026, 8, 31))
        assert [i["date"] for i in instances] == [
            "2026-05-15", "2026-06-15", "2026-07-15", "2026-08-15",
        ]

    def test_day_31_skips_short_months(self):
        rule = self._rule([31])
        instances = expand_rule(rule, REF, date(2026, 8, 31))
        # May 31, no 31 in June, no 31 in July (wait, July has 31).
        # June: 30 days, no 31. July: 31 days. August: 31 days.
        assert [i["date"] for i in instances] == [
            "2026-05-31", "2026-07-31", "2026-08-31",
        ]


# ---------------------------------------------------------------------------
# Persistence + extend_all
# ---------------------------------------------------------------------------

class TestPersistenceAndExtend:
    @pytest.fixture(autouse=True)
    def isolated_paths(self, tmp_path, monkeypatch):
        monkeypatch.setattr(recurring, "DATA_DIR", str(tmp_path))
        monkeypatch.setattr(recurring, "RECURRING_PATH", str(tmp_path / "recurring.json"))

    def test_save_then_load_round_trip(self):
        rules = [parse_recurring_rule("每周一 健身")]
        save_rules(rules)
        loaded = load_rules()
        assert len(loaded) == 1
        assert loaded[0]["task_text"] == "健身"

    def test_load_returns_empty_when_missing(self):
        assert load_rules() == []

    def test_load_returns_empty_on_corrupt_json(self, tmp_path):
        Path(recurring.RECURRING_PATH).write_text("not json", encoding="utf-8")
        assert load_rules() == []

    def test_load_returns_empty_when_not_a_list(self, tmp_path):
        Path(recurring.RECURRING_PATH).write_text(json.dumps({"a": 1}), encoding="utf-8")
        assert load_rules() == []

    def test_register_rule_appends(self):
        rule = parse_recurring_rule("每周一 健身")
        register_rule(rule)
        assert len(load_rules()) == 1

    def test_register_rule_dedupes_by_id(self):
        rule = parse_recurring_rule("每周一 健身")
        register_rule(rule)
        register_rule(rule)  # same id
        assert len(load_rules()) == 1

    def test_extend_all_with_no_rules_returns_empty(self):
        assert extend_all(REF) == []

    def test_extend_all_first_call_expands_full_window(self):
        rule = parse_recurring_rule("每周一 健身")
        register_rule(rule)
        new_instances = extend_all(REF)
        # 12 weeks × 1 weekday = 12 instances, give or take edge weeks
        assert 11 <= len(new_instances) <= 13

    def test_extend_all_idempotent_same_day(self):
        rule = parse_recurring_rule("每周一 健身")
        register_rule(rule)
        extend_all(REF)
        # Calling again on the same day should produce no new instances.
        assert extend_all(REF) == []

    def test_extend_all_advances_window_on_later_call(self):
        rule = parse_recurring_rule("每周一 健身")
        register_rule(rule)
        extend_all(REF)
        # One week later, the rolling 12-week window now includes one new
        # Monday; we should see exactly that one.
        future_ref = date(2026, 5, 12)
        new_instances = extend_all(future_ref)
        assert len(new_instances) == 1
        assert new_instances[0]["task"] == "健身"


# ---------------------------------------------------------------------------
# Integration: preprocess_input with a recurring rule
# ---------------------------------------------------------------------------

class TestPreprocessIntegration:
    @pytest.fixture(autouse=True)
    def isolated_paths(self, tmp_path, monkeypatch):
        # Recurring writes are gated on register_rule, but parse+expand do
        # NOT touch disk. Still, isolate paths for safety.
        monkeypatch.setattr(recurring, "DATA_DIR", str(tmp_path))
        monkeypatch.setattr(recurring, "RECURRING_PATH", str(tmp_path / "recurring.json"))

    def test_recurring_input_lands_in_resolved(self):
        from task_parser import preprocess_input

        resolved, unresolved, pending = preprocess_input("每周一 健身房", REF)

        assert unresolved == []
        # 12 weeks × 1 weekday ≈ 12 (could be 12 depending on calendar edges)
        assert 11 <= len(resolved) <= 13
        assert all(item["task"] == "健身房" for item in resolved)
        # Pending rule should be present, NOT yet persisted.
        assert len(pending) == 1
        assert pending[0]["original_text"] == "每周一 健身房"
        assert load_rules() == []  # not registered

    def test_mixed_recurring_and_oneshot(self):
        from task_parser import preprocess_input

        resolved, unresolved, pending = preprocess_input(
            "每周一 健身房\n明天买菜\n写报告", REF,
        )

        assert any(item.get("task") == "买菜" for item in resolved)
        assert "写报告" in unresolved
        assert len(pending) == 1
