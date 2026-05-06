"""Unit tests for time_parser.extract_time."""
from time_parser import extract_time


# ---------------------------------------------------------------------------
# Single time, English
# ---------------------------------------------------------------------------

class TestEnglishSingle:
    def test_24h_colon(self):
        prefix, rest = extract_time("9:00 standup")
        assert prefix == "[09:00]"
        assert rest == "standup"

    def test_24h_zero_padded(self):
        prefix, rest = extract_time("09:00 daily")
        assert prefix == "[09:00]"
        assert rest == "daily"

    def test_24h_late(self):
        prefix, rest = extract_time("21:30 wind down")
        assert prefix == "[21:30]"
        assert rest == "wind down"

    def test_pm_no_minutes(self):
        prefix, rest = extract_time("3pm meeting")
        assert prefix == "[15:00]"
        assert rest == "meeting"

    def test_am_no_minutes(self):
        prefix, rest = extract_time("9am call")
        assert prefix == "[09:00]"
        assert rest == "call"

    def test_pm_with_colon(self):
        prefix, rest = extract_time("3:30pm meeting")
        assert prefix == "[15:30]"
        assert rest == "meeting"

    def test_12am_is_midnight(self):
        prefix, _ = extract_time("12am task")
        assert prefix == "[00:00]"

    def test_12pm_is_noon(self):
        prefix, _ = extract_time("12pm lunch")
        assert prefix == "[12:00]"


# ---------------------------------------------------------------------------
# Single time, Chinese
# ---------------------------------------------------------------------------

class TestChineseSingle:
    def test_dot_only(self):
        prefix, rest = extract_time("9点开会")
        assert prefix == "[09:00]"
        assert rest == "开会"

    def test_dot_with_zhong(self):
        prefix, rest = extract_time("9点钟开会")
        assert prefix == "[09:00]"
        assert rest == "开会"

    def test_dot_with_minutes(self):
        prefix, rest = extract_time("9点30开会")
        assert prefix == "[09:30]"
        assert rest == "开会"

    def test_dot_with_minutes_fen(self):
        prefix, rest = extract_time("9点45分会议")
        assert prefix == "[09:45]"
        assert rest == "会议"

    def test_half(self):
        prefix, rest = extract_time("9点半开会")
        assert prefix == "[09:30]"
        assert rest == "开会"

    def test_quarter(self):
        prefix, rest = extract_time("9点一刻开会")
        assert prefix == "[09:15]"
        assert rest == "开会"

    def test_three_quarter(self):
        prefix, rest = extract_time("9点三刻开会")
        assert prefix == "[09:45]"
        assert rest == "开会"

    def test_shangwu_morning(self):
        prefix, rest = extract_time("上午9点开会")
        assert prefix == "[09:00]"
        assert rest == "开会"

    def test_xiawu_afternoon(self):
        prefix, rest = extract_time("下午3点开会")
        assert prefix == "[15:00]"
        assert rest == "开会"

    def test_wanshang_evening(self):
        prefix, rest = extract_time("晚上9点睡觉")
        assert prefix == "[21:00]"
        assert rest == "睡觉"

    def test_lingchen_dawn(self):
        prefix, rest = extract_time("凌晨2点起床")
        assert prefix == "[02:00]"
        assert rest == "起床"

    def test_zhongwu_noon(self):
        prefix, rest = extract_time("中午12点吃饭")
        assert prefix == "[12:00]"
        assert rest == "吃饭"


# ---------------------------------------------------------------------------
# Ranges
# ---------------------------------------------------------------------------

class TestRanges:
    def test_chinese_dash_dian(self):
        prefix, rest = extract_time("9-10点开会")
        assert prefix == "[09:00-10:00]"
        assert rest == "开会"

    def test_chinese_dian_dash_dian(self):
        prefix, rest = extract_time("9点-10点开会")
        assert prefix == "[09:00-10:00]"
        assert rest == "开会"

    def test_chinese_with_minutes(self):
        prefix, rest = extract_time("9点30-10点 standup")
        assert prefix == "[09:30-10:00]"
        assert rest == "standup"

    def test_period_applies_to_both(self):
        prefix, rest = extract_time("下午3-5点讨论")
        assert prefix == "[15:00-17:00]"
        assert rest == "讨论"

    def test_morning_range(self):
        prefix, rest = extract_time("上午9-11点会议")
        assert prefix == "[09:00-11:00]"
        assert rest == "会议"

    def test_24h_colon_range(self):
        prefix, rest = extract_time("9:00-10:30 review")
        assert prefix == "[09:00-10:30]"
        assert rest == "review"

    def test_ampm_range_explicit(self):
        prefix, rest = extract_time("9am-11am sprint planning")
        assert prefix == "[09:00-11:00]"
        assert rest == "sprint planning"

    def test_ampm_range_shared(self):
        # `am` only on right side; both sides should use it.
        prefix, rest = extract_time("9-11am sprint")
        assert prefix == "[09:00-11:00]"
        assert rest == "sprint"

    def test_inverted_range_is_rejected(self):
        # 5-3 makes no sense; we should fail-open and return no time.
        prefix, rest = extract_time("5-3 weird")
        assert prefix is None


# ---------------------------------------------------------------------------
# Negative / no-time cases
# ---------------------------------------------------------------------------

class TestNoTime:
    def test_pure_text_chinese(self):
        prefix, rest = extract_time("买菜")
        assert prefix is None
        assert rest == "买菜"

    def test_pure_text_english(self):
        prefix, rest = extract_time("complete report")
        assert prefix is None
        assert rest == "complete report"

    def test_empty(self):
        prefix, rest = extract_time("")
        assert prefix is None
        assert rest == ""

    def test_currency_not_time(self):
        # "9块钱" is currency, not a time
        prefix, rest = extract_time("买9块钱的菜")
        assert prefix is None


# ---------------------------------------------------------------------------
# Time at end / middle / start of text
# ---------------------------------------------------------------------------

class TestPosition:
    def test_time_at_end(self):
        prefix, rest = extract_time("standup 9am")
        assert prefix == "[09:00]"
        assert rest == "standup"

    def test_time_in_middle(self):
        prefix, rest = extract_time("daily 9:00 standup")
        assert prefix == "[09:00]"
        assert rest == "daily standup"

    def test_chinese_time_at_end(self):
        prefix, rest = extract_time("开会 下午3点")
        assert prefix == "[15:00]"
        assert rest == "开会"
