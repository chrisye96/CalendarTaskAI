"""Deterministic time-of-day extraction.

Companion to `task_parser`: where `task_parser.extract_date` strips date
hints, this strips time hints from whatever's left and emits a normalized
`[HH:MM]` (single time) or `[HH:MM-HH:MM]` (range) prefix.

The prefix sits in front of the task text and is stored verbatim in the
DesktopCal database, so the user sees `[09:00] team standup` on their
calendar exactly as written here.

Recognized formats (single time):
  * 24-hour:                9:00, 09:00
  * 12-hour with AM/PM:     9am, 9:30pm, 9 AM
  * Chinese hour:           9点, 9点钟
  * Chinese hour + minute:  9点30, 9点30分
  * Chinese fractional:     9点半 (=:30), 9点一刻 (=:15), 9点三刻 (=:45)
  * Chinese period prefix:  上午9点, 下午3点, 晚上9点, 凌晨2点, 中午12点

Recognized formats (range):
  * Same as above with `-` between two times: `9-10点`, `9:00-10:30`,
    `上午9-11点`, `9am-11am`, `9:30-10:30am`.
  * If the period (am/pm/上午/下午) is on only one side, it applies to
    both sides (e.g. `9-10am` -> 09:00-10:00).

Bias is to FAIL OPEN: anything we can't parse confidently is left alone
rather than producing a wrong time prefix.
"""
from __future__ import annotations

import re

# Chinese period markers and their PM offset.
_PERIOD_PM = {"下午", "晚上"}
_PERIOD_AM = {"上午", "凌晨"}
_PERIOD_NOON = {"中午"}  # 中午12点 -> 12:00, 中午1点 -> 13:00 (hour wrap)

# Chinese minute fractions.
_FRACTION_MINUTES = {
    "半": 30,
    "一刻": 15,
    "三刻": 45,
}

# Boundary helpers. A time hint shouldn't sit inside a longer number/colon
# run (avoids eating "12345" or "9.99" mid-hour-look-alikes).
_LB = r"(?<![0-9])"        # not preceded by digit
_LA = r"(?![0-9:.])"       # not followed by digit, colon, or dot


def _ampm_norm(s: str | None) -> str | None:
    if not s:
        return None
    s = s.lower().replace(".", "").strip()
    if s in ("am", "pm"):
        return s
    return None


def _normalize_hour(hour: int, period: str | None, ampm: str | None) -> int | None:
    """Convert a 12-hour-ish reading to a 24h hour. Returns None if invalid."""
    if hour < 0 or hour > 24:
        return None

    if ampm == "pm":
        if hour == 12:
            return 12
        if 1 <= hour <= 11:
            return hour + 12
        return hour
    if ampm == "am":
        if hour == 12:
            return 0
        return hour

    if period in _PERIOD_PM:
        if hour == 12:
            return 12
        if 1 <= hour <= 11:
            return hour + 12
        return hour
    if period in _PERIOD_AM:
        if hour == 12:
            return 0
        return hour
    if period in _PERIOD_NOON:
        return 12 if hour == 12 else (hour + 12 if 1 <= hour <= 11 else hour)

    return hour


def _format_hm(hour: int, minute: int) -> str:
    return f"{hour:02d}:{minute:02d}"


def _valid_hm(hour: int, minute: int) -> bool:
    return 0 <= hour < 24 and 0 <= minute < 60


# Regex chunks. Boundaries use lookbehind/lookahead so they don't consume
# adjacent characters — important for Chinese, where a time and the task
# text often have no whitespace between them ("9点开会").

_AMPM_RE = r"(?:\s*(?:am|AM|pm|PM|a\.m\.|p\.m\.))"
_PERIOD_RE = r"(?:上午|下午|晚上|凌晨|中午)"

# A "time component": optional period, hours, optional minutes via colon /
# `点[半|一刻|三刻]` / `点(\d+)分?(钟)?`, optional am/pm.
def _component(side: str) -> str:
    return (
        rf"(?P<period{side}>{_PERIOD_RE})?"
        rf"(?P<h{side}>\d{{1,2}})"
        rf"(?:[:：](?P<mc{side}>\d{{2}}))?"                        # 9:00
        rf"(?:点(?P<frac{side}>半|一刻|三刻)?(?:(?P<md{side}>\d{{1,2}})分?)?(?:钟)?)?"  # 9点 / 9点半 / 9点30 / 9点30分 / 9点钟
        rf"(?P<ampm{side}>{_AMPM_RE})?"
    )


_RANGE_RE = re.compile(_LB + _component("a") + r"\s*[-－]\s*" + _component("b") + _LA)
_SINGLE_RE = re.compile(_LB + _component("a") + _LA)


def _resolve_side(
    m: re.Match, side: str, period: str | None, ampm: str | None
) -> tuple[int, int] | None:
    """Resolve one side of the parsed match into (hour, minute) 24h."""
    h_str = m.group(f"h{side}")
    if h_str is None:
        return None
    hour = int(h_str)

    mc = m.group(f"mc{side}")
    frac = m.group(f"frac{side}")
    md = m.group(f"md{side}")

    if mc is not None:
        minute = int(mc)
    elif frac is not None:
        minute = _FRACTION_MINUTES[frac]
    elif md is not None:
        minute = int(md)
    else:
        # Bare digit with no minute / colon / 点 / am-pm / period:
        # _has_dian and _is_valid_*_match decide whether to accept the match.
        minute = 0

    norm = _normalize_hour(hour, period, ampm)
    if norm is None or not _valid_hm(norm, minute):
        return None
    return norm, minute


def _has_dian(m: re.Match, side: str) -> bool:
    """Did this side include the Chinese 点 marker?

    A bare `9` followed only by `点` (no minute, no fraction) doesn't fill the
    `frac`/`md` capture groups, so the regex match alone can't tell us. We
    confirm by peeking at the raw input right after the hour digits.
    """
    if m.group(f"frac{side}") is not None or m.group(f"md{side}") is not None:
        return True
    start = m.start(f"h{side}")
    end_candidate = start + len(m.group(f"h{side}"))
    text = m.string
    return "点" in text[end_candidate : end_candidate + 8]


def extract_time(text: str) -> tuple[str | None, str]:
    """Find a time hint in `text` and return (prefix, cleaned_text).

    `prefix` is `"[HH:MM]"`, `"[HH:MM-HH:MM]"`, or `None`.
    `cleaned_text` is `text` with the matched time substring removed and
    whitespace tidied.
    """
    if not text:
        return None, text or ""

    text = text.strip()

    # Try range first (more specific).
    m = _RANGE_RE.search(text)
    if m and _is_valid_range_match(m):
        result = _try_range(m)
        if result is not None:
            prefix, span = result
            return prefix, _strip_span(text, span)

    # Fall back to single.
    for m in _SINGLE_RE.finditer(text):
        if _is_valid_single_match(m):
            result = _try_single(m)
            if result is not None:
                prefix, span = result
                return prefix, _strip_span(text, span)

    return None, text


def _strip_span(text: str, span: tuple[int, int]) -> str:
    cleaned = (text[: span[0]] + " " + text[span[1] :]).strip()
    return re.sub(r"\s+", " ", cleaned)


def _is_valid_single_match(m: re.Match) -> bool:
    """A bare digit is not a time. We need at least one disambiguating marker:
    a colon, 点, am/pm, or a Chinese period prefix. Without any of those, the
    match is just a number and we should not extract it.
    """
    has_colon = m.group("mca") is not None
    has_dian = _has_dian(m, "a")
    has_ampm = m.group("ampma") is not None
    has_period = m.group("perioda") is not None
    return has_colon or has_dian or has_ampm or has_period


def _is_valid_range_match(m: re.Match) -> bool:
    """A range needs at least one side to have a marker. Most of the time
    both sides will, but `9-10点` only has 点 on the right side."""
    return _is_valid_single_match(m) or any(
        m.group(g) is not None
        for g in ("mcb", "fracb", "mdb", "ampmb", "periodb")
    ) or _has_dian(m, "b")


def _try_single(m: re.Match) -> tuple[str, tuple[int, int]] | None:
    period = m.group("perioda")
    ampm = _ampm_norm(m.group("ampma"))
    resolved = _resolve_side(m, "a", period, ampm)
    if resolved is None:
        return None
    prefix = f"[{_format_hm(*resolved)}]"
    return prefix, (m.start(), m.end())


def _try_range(m: re.Match) -> tuple[str, tuple[int, int]] | None:
    period_a = m.group("perioda")
    period_b = m.group("periodb")
    ampm_a = _ampm_norm(m.group("ampma"))
    ampm_b = _ampm_norm(m.group("ampmb"))

    # Period / am-pm sharing across the range.
    if not period_a and period_b:
        period_a = period_b
    elif period_a and not period_b:
        period_b = period_a
    if not ampm_a and ampm_b:
        ampm_a = ampm_b
    elif ampm_a and not ampm_b:
        ampm_b = ampm_a

    a = _resolve_side(m, "a", period_a, ampm_a)
    b = _resolve_side(m, "b", period_b, ampm_b)
    if a is None or b is None:
        return None

    # Reject inverted / nonsense ranges: if start > end overall, this is
    # almost certainly not a time range (e.g. score "5-3").
    a_total = a[0] * 60 + a[1]
    b_total = b[0] * 60 + b[1]
    if b_total < a_total:
        return None

    prefix = f"[{_format_hm(*a)}-{_format_hm(*b)}]"
    return prefix, (m.start(), m.end())
