"""Unit tests for the deterministic task parser.

Reference date: 2026-05-05 (Tuesday). All relative-date assertions are
computed against this reference so the suite is hermetic and won't drift
with the wall clock.
"""
from datetime import date

import pytest

from task_parser import extract_date, preprocess_input, split_tasks

REF = date(2026, 5, 5)  # Tuesday


# ---------------------------------------------------------------------------
# split_tasks
# ---------------------------------------------------------------------------

class TestSplitTasks:
    def test_empty_input_returns_empty_list(self):
        assert split_tasks("") == []
        assert split_tasks("   ") == []

    def test_newline_splits(self):
        assert split_tasks("买菜\n洗衣服") == ["买菜", "洗衣服"]

    def test_crlf_splits(self):
        assert split_tasks("买菜\r\n洗衣服") == ["买菜", "洗衣服"]

    def test_chinese_semicolon_splits(self):
        assert split_tasks("买菜；洗衣服；打扫") == ["买菜", "洗衣服", "打扫"]

    def test_english_semicolon_splits(self):
        assert split_tasks("buy groceries; do laundry") == ["buy groceries", "do laundry"]

    def test_chinese_enumeration_comma_splits(self):
        assert split_tasks("买菜、洗衣服、打扫") == ["买菜", "洗衣服", "打扫"]

    def test_regular_comma_does_not_split(self):
        # Per design: regular commas are NOT separators (would mangle prose).
        assert split_tasks("买菜, 然后洗衣服") == ["买菜, 然后洗衣服"]

    def test_space_does_not_split_long_phrases(self):
        # Spaces don't split: "完成项目报告" stays one task.
        assert split_tasks("完成项目报告") == ["完成项目报告"]

    def test_mixed_separators(self):
        assert split_tasks("买菜\n洗衣服；打扫、做饭") == ["买菜", "洗衣服", "打扫", "做饭"]

    def test_blank_segments_dropped(self):
        assert split_tasks("买菜；；洗衣服") == ["买菜", "洗衣服"]


# ---------------------------------------------------------------------------
# extract_date - Chinese relative
# ---------------------------------------------------------------------------

class TestChineseRelativeDates:
    @pytest.mark.parametrize("token, expected", [
        ("今天", "2026-05-05"),
        ("今日", "2026-05-05"),
        ("今晚", "2026-05-05"),
        ("明天", "2026-05-06"),
        ("明日", "2026-05-06"),
        ("后天", "2026-05-07"),
        ("大后天", "2026-05-08"),
    ])
    def test_relative_day_at_start(self, token, expected):
        d, txt = extract_date(f"{token}买菜", REF)
        assert d == expected
        assert txt == "买菜"

    @pytest.mark.parametrize("token, expected", [
        ("今天", "2026-05-05"),
        ("明天", "2026-05-06"),
        ("后天", "2026-05-07"),
    ])
    def test_relative_day_at_end(self, token, expected):
        d, txt = extract_date(f"买菜 {token}", REF)
        assert d == expected
        assert txt == "买菜"


# ---------------------------------------------------------------------------
# extract_date - week / month
# ---------------------------------------------------------------------------

class TestWeekAndMonth:
    def test_next_week_alone_means_next_monday(self):
        # REF=Tue 2026-05-05; next Monday = 2026-05-11
        d, _ = extract_date("下周开会", REF)
        assert d == "2026-05-11"

    def test_next_week_specific_day(self):
        # next Wednesday = 2026-05-13
        d, _ = extract_date("下周三开会", REF)
        assert d == "2026-05-13"

    def test_this_week_specific_day(self):
        # this Wednesday: REF=Tue, +1 day = 2026-05-06
        d, _ = extract_date("这周三开会", REF)
        assert d == "2026-05-06"

    def test_this_weekend_is_saturday(self):
        d, _ = extract_date("这周末聚餐", REF)
        assert d == "2026-05-09"

    def test_next_month_is_first(self):
        d, _ = extract_date("下个月报告", REF)
        assert d == "2026-06-01"

    def test_month_end(self):
        d, _ = extract_date("月底交报告", REF)
        assert d == "2026-05-31"


# ---------------------------------------------------------------------------
# extract_date - day-of-week
# ---------------------------------------------------------------------------

class TestDayOfWeek:
    @pytest.mark.parametrize("token, expected", [
        # REF=Tue 2026-05-05. The "next occurrence" rule gives the upcoming
        # Wed/Thu/.../Sun and skips today (Tue) to next week's Tuesday.
        ("周一", "2026-05-11"),
        ("周二", "2026-05-12"),
        ("周三", "2026-05-06"),
        ("周日", "2026-05-10"),
        ("星期三", "2026-05-06"),
        ("礼拜天", "2026-05-10"),
    ])
    def test_weekday_at_end(self, token, expected):
        d, _ = extract_date(f"开会 {token}", REF)
        assert d == expected


# ---------------------------------------------------------------------------
# extract_date - relative N day/week/month
# ---------------------------------------------------------------------------

class TestRelativeNumeric:
    @pytest.mark.parametrize("token, expected", [
        ("3天后", "2026-05-08"),
        ("三天后", "2026-05-08"),
        ("2周后", "2026-05-19"),
        ("两周后", "2026-05-19"),
        ("1个月后", "2026-06-05"),
    ])
    def test_relative_n(self, token, expected):
        d, _ = extract_date(f"{token}面试", REF)
        assert d == expected


# ---------------------------------------------------------------------------
# extract_date - full date
# ---------------------------------------------------------------------------

class TestFullDate:
    @pytest.mark.parametrize("token, expected", [
        ("2026年3月25日", "2026-03-25"),
        ("2026-03-25", "2026-03-25"),
        ("2026.03.25", "2026-03-25"),
        ("2026/03/25", "2026-03-25"),
        ("2027-01-15", "2027-01-15"),
    ])
    def test_full_date(self, token, expected):
        d, _ = extract_date(f"{token} 报告", REF)
        assert d == expected


# ---------------------------------------------------------------------------
# extract_date - short date (year inferred)
# ---------------------------------------------------------------------------

class TestShortDate:
    def test_short_date_in_future_this_year(self):
        # REF=2026-05-05; "8月15日" is later this year -> 2026
        d, _ = extract_date("8月15日 旅行", REF)
        assert d == "2026-08-15"

    def test_short_date_in_past_rolls_to_next_year(self):
        # "3月25日" already passed -> 2027
        d, _ = extract_date("3月25日 报告", REF)
        assert d == "2027-03-25"

    def test_mmdd_4_digit_format(self):
        # 0815 -> Aug 15 of this/next year
        d, _ = extract_date("0815 旅行", REF)
        assert d == "2026-08-15"


# ---------------------------------------------------------------------------
# extract_date - English
# ---------------------------------------------------------------------------

class TestEnglishDates:
    @pytest.mark.parametrize("token, expected", [
        ("today", "2026-05-05"),
        ("tonight", "2026-05-05"),
        ("tomorrow", "2026-05-06"),
        ("end of month", "2026-05-31"),
    ])
    def test_english_relative(self, token, expected):
        d, _ = extract_date(f"buy groceries {token}", REF)
        assert d == expected

    def test_in_n_days(self):
        d, _ = extract_date("ship release in 3 days", REF)
        assert d == "2026-05-08"

    def test_next_monday(self):
        d, _ = extract_date("standup next monday", REF)
        assert d == "2026-05-11"

    def test_next_week_alone(self):
        d, _ = extract_date("review next week", REF)
        assert d == "2026-05-11"


# ---------------------------------------------------------------------------
# extract_date - non-matches
# ---------------------------------------------------------------------------

class TestNoDate:
    def test_pure_text_returns_none(self):
        d, txt = extract_date("写报告初稿", REF)
        assert d is None
        assert txt == "写报告初稿"

    def test_invalid_short_date_does_not_match(self):
        # "买50000股票": leading "5" forms 5-digit number; the MMDD regex
        # has a digit-lookbehind/ahead so it shouldn't fire.
        d, txt = extract_date("买50000股票", REF)
        assert d is None
        assert "50000" in txt

    def test_empty_returns_empty(self):
        d, txt = extract_date("", REF)
        assert d is None
        assert txt == ""


# ---------------------------------------------------------------------------
# preprocess_input integration
# ---------------------------------------------------------------------------

class TestPreprocessInput:
    def test_all_resolved(self):
        resolved, unresolved = preprocess_input("明天买菜；后天聚餐", REF)
        assert unresolved == []
        assert {"date": "2026-05-06", "task": "买菜"} in resolved
        assert {"date": "2026-05-07", "task": "聚餐"} in resolved

    def test_mixed_resolved_and_unresolved(self):
        resolved, unresolved = preprocess_input("明天买菜；写报告初稿", REF)
        assert resolved == [{"date": "2026-05-06", "task": "买菜"}]
        assert unresolved == ["写报告初稿"]

    def test_all_unresolved(self):
        resolved, unresolved = preprocess_input("写报告初稿；准备演讲材料", REF)
        assert resolved == []
        assert sorted(unresolved) == ["写报告初稿", "准备演讲材料"]

    def test_full_date_with_year(self):
        resolved, unresolved = preprocess_input("2026年12月1日 体检", REF)
        assert resolved == [{"date": "2026-12-01", "task": "体检"}]
        assert unresolved == []
