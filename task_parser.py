"""Deterministic task parser - splits multi-task input and extracts dates using regex/rules.

This module provides rule-based preprocessing WITHOUT any LLM calls.
Design principle: Use deterministic logic first, LLM only as fallback.
"""
import re
from datetime import date, timedelta
import calendar


# Chinese number to int mapping
CHINESE_NUMBERS = {
    '零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
    '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15,
    '十六': 16, '十七': 17, '十八': 18, '十九': 19, '二十': 20,
    '二十一': 21, '二十二': 22, '二十三': 23, '二十四': 24, '二十五': 25,
    '二十六': 26, '二十七': 27, '二十八': 28, '二十九': 29, '三十': 30,
    '三十一': 31,
}

# Weekday mappings (Monday = 0, Sunday = 6)
WEEKDAY_MAP = {
    '一': 0, '二': 1, '三': 2, '四': 3, '五': 4, '六': 5, '日': 6, '天': 6,
    'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
    'friday': 4, 'saturday': 5, 'sunday': 6,
    'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6,
}


def _chinese_to_int(chinese_str: str) -> int:
    """Convert Chinese number string to integer.
    
    Handles: 一, 二, 两, 三...十, 十一...三十一
    Also handles Arabic numerals as strings.
    """
    chinese_str = chinese_str.strip()
    
    # Direct lookup
    if chinese_str in CHINESE_NUMBERS:
        return CHINESE_NUMBERS[chinese_str]
    
    # Try Arabic numeral
    if chinese_str.isdigit():
        return int(chinese_str)
    
    # Handle compound numbers like 二十三 (not in direct map)
    # Pattern: X十Y where X and Y are single digits
    if '十' in chinese_str:
        parts = chinese_str.split('十')
        if len(parts) == 2:
            tens = CHINESE_NUMBERS.get(parts[0], 1) if parts[0] else 1
            ones = CHINESE_NUMBERS.get(parts[1], 0) if parts[1] else 0
            return tens * 10 + ones
    
    return 1  # Default fallback


def _get_next_weekday(reference: date, weekday: int) -> date:
    """Get the next occurrence of a weekday (0=Monday, 6=Sunday).
    
    If today is that weekday, returns next week's occurrence.
    """
    days_ahead = weekday - reference.weekday()
    if days_ahead <= 0:  # Target day already happened this week or is today
        days_ahead += 7
    return reference + timedelta(days=days_ahead)


def _get_this_week_day(reference: date, weekday: int) -> date:
    """Get this week's occurrence of a weekday."""
    days_diff = weekday - reference.weekday()
    return reference + timedelta(days=days_diff)


def _get_next_week_day(reference: date, weekday: int) -> date:
    """Get next week's occurrence of a weekday."""
    # First, find this week's Monday
    days_to_monday = reference.weekday()  # Monday=0
    this_monday = reference - timedelta(days=days_to_monday)
    next_monday = this_monday + timedelta(days=7)
    return next_monday + timedelta(days=weekday)


def _get_month_end(reference: date) -> date:
    """Get the last day of the current month."""
    _, last_day = calendar.monthrange(reference.year, reference.month)
    return date(reference.year, reference.month, last_day)


def _get_month_start(reference: date) -> date:
    """Get 1st of current month, or 1st of next month if past 5th."""
    if reference.day > 5:
        # Return 1st of next month
        if reference.month == 12:
            return date(reference.year + 1, 1, 1)
        return date(reference.year, reference.month + 1, 1)
    return date(reference.year, reference.month, 1)


def _add_months(reference: date, months: int) -> date:
    """Add N months to a date, handling year rollover."""
    new_month = reference.month + months
    new_year = reference.year + (new_month - 1) // 12
    new_month = ((new_month - 1) % 12) + 1
    # Handle day overflow (e.g., Jan 31 + 1 month)
    _, max_day = calendar.monthrange(new_year, new_month)
    new_day = min(reference.day, max_day)
    return date(new_year, new_month, new_day)


def _parse_short_date(month: int, day: int, reference: date) -> date:
    """Parse a short date (month/day only), inferring year.
    
    If the date has passed this year, use next year.
    """
    try:
        target = date(reference.year, month, day)
        if target < reference:
            target = date(reference.year + 1, month, day)
        return target
    except ValueError:
        return None  # Invalid date (e.g., Feb 30)


def split_tasks(raw_input: str) -> list[str]:
    """Split user input into individual task strings using deterministic rules.
    
    Splitting rules (in order):
    1. First split by newlines (\\n, \\r\\n)
    2. For each line, try splitting by these delimiters:
       - Chinese semicolons ；
       - English semicolons ;
       - Chinese enumeration comma 、
    3. Do NOT split by regular commas (，,) or spaces
    
    Args:
        raw_input: Raw user input string
    
    Returns:
        List of individual task strings, stripped and non-empty
    """
    if not raw_input:
        return []
    
    # Step 1: Split by newlines
    lines = re.split(r'\r?\n', raw_input)
    
    tasks = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Step 2: Try splitting by semicolons and enumeration comma
        # Split by ；, ;, or 、
        parts = re.split(r'[；;、]', line)
        
        for part in parts:
            part = part.strip()
            if part:
                tasks.append(part)
    
    return tasks


def extract_date(task_text: str, reference_date: date = None) -> tuple[str | None, str]:
    """Extract a date hint from a task string using regex patterns.
    
    Tries multiple patterns to find date hints at the beginning or end of the task text.
    Returns the date in YYYY-MM-DD format and the cleaned task text.
    
    Args:
        task_text: A single task string
        reference_date: Reference date for relative calculations (defaults to today)
    
    Returns:
        Tuple of (date_str or None, cleaned_task_text)
        - date_str: "YYYY-MM-DD" if date found, None otherwise
        - cleaned_task_text: Task text with date hint removed, stripped
    """
    if not task_text:
        return None, ""
    
    if reference_date is None:
        reference_date = date.today()
    
    task_text = task_text.strip()
    
    # Define patterns with extraction functions
    # Each pattern: (regex, extraction_function, position)
    # position: 'start', 'end', or 'both'
    
    patterns = _build_patterns(reference_date)
    
    for pattern, extractor, position in patterns:
        result = _try_pattern(task_text, pattern, extractor, position, reference_date)
        if result:
            return result
    
    # No date found
    return None, task_text


def _build_patterns(reference: date) -> list:
    """Build list of (regex, extractor_func, position) patterns."""
    patterns = []
    
    # === Chinese relative dates (exact matches) ===
    
    # 今天/今日/今晚
    patterns.append((
        r'(今天|今日|今晚)',
        lambda m, ref: ref,
        'both'
    ))
    
    # 明天/明日
    patterns.append((
        r'(明天|明日)',
        lambda m, ref: ref + timedelta(days=1),
        'both'
    ))
    
    # 后天
    patterns.append((
        r'(后天)',
        lambda m, ref: ref + timedelta(days=2),
        'both'
    ))
    
    # 大后天
    patterns.append((
        r'(大后天)',
        lambda m, ref: ref + timedelta(days=3),
        'both'
    ))
    
    # === Chinese relative periods ===
    
    # 下周一 through 下周日/下周天
    patterns.append((
        r'(下周([一二三四五六日天]))',
        lambda m, ref: _get_next_week_day(ref, WEEKDAY_MAP[m.group(2)]),
        'both'
    ))
    
    # 下周 (no day specified = next Monday)
    patterns.append((
        r'(下周)(?![一二三四五六日天])',
        lambda m, ref: _get_next_week_day(ref, 0),
        'both'
    ))
    
    # 这周一 through 这周日/这周天/这周末
    patterns.append((
        r'(这周([一二三四五六日天]))',
        lambda m, ref: _get_this_week_day(ref, WEEKDAY_MAP[m.group(2)]),
        'both'
    ))
    
    # 这周末 = this Saturday
    patterns.append((
        r'(这周末)',
        lambda m, ref: _get_this_week_day(ref, 5),
        'both'
    ))
    
    # 下个月 = 1st of next month
    patterns.append((
        r'(下个月)',
        lambda m, ref: _add_months(date(ref.year, ref.month, 1), 1),
        'both'
    ))
    
    # 这个月 = 1st of current month (or next if past 5th)
    patterns.append((
        r'(这个月)',
        lambda m, ref: _get_month_start(ref),
        'both'
    ))
    
    # 月底 = last day of current month
    patterns.append((
        r'(月底)',
        lambda m, ref: _get_month_end(ref),
        'both'
    ))
    
    # 月初 = 1st of month (context-aware)
    patterns.append((
        r'(月初)',
        lambda m, ref: _get_month_start(ref),
        'both'
    ))
    
    # === Day of week patterns ===
    
    # 周一~周日 (next occurrence)
    patterns.append((
        r'(周([一二三四五六日天]))',
        lambda m, ref: _get_next_weekday(ref, WEEKDAY_MAP[m.group(2)]),
        'both'
    ))
    
    # 星期一~星期日/星期天
    patterns.append((
        r'(星期([一二三四五六日天]))',
        lambda m, ref: _get_next_weekday(ref, WEEKDAY_MAP[m.group(2)]),
        'both'
    ))
    
    # 礼拜一~礼拜日/礼拜天
    patterns.append((
        r'(礼拜([一二三四五六日天]))',
        lambda m, ref: _get_next_weekday(ref, WEEKDAY_MAP[m.group(2)]),
        'both'
    ))
    
    # === Relative expressions with numbers ===
    
    # N天后/N天内 (Arabic or Chinese numbers)
    patterns.append((
        r'((\d+|[一二两三四五六七八九十]+)天[后内])',
        lambda m, ref: ref + timedelta(days=_chinese_to_int(m.group(2))),
        'both'
    ))
    
    # N周后
    patterns.append((
        r'((\d+|[一二两三四五六七八九十]+)周后)',
        lambda m, ref: ref + timedelta(weeks=_chinese_to_int(m.group(2))),
        'both'
    ))
    
    # N个月后
    patterns.append((
        r'((\d+|[一二两三四五六七八九十]+)个月后)',
        lambda m, ref: _add_months(ref, _chinese_to_int(m.group(2))),
        'both'
    ))
    
    # === Full date formats (with year) ===
    
    # 2026年3月25日
    patterns.append((
        r'((\d{4})年(\d{1,2})月(\d{1,2})日?)',
        lambda m, ref: _safe_date(int(m.group(2)), int(m.group(3)), int(m.group(4))),
        'both'
    ))
    
    # 2026-03-25 or 2026-3-25
    patterns.append((
        r'((\d{4})-(\d{1,2})-(\d{1,2}))',
        lambda m, ref: _safe_date(int(m.group(2)), int(m.group(3)), int(m.group(4))),
        'both'
    ))
    
    # 2026.03.25 or 2026.3.25
    patterns.append((
        r'((\d{4})\.(\d{1,2})\.(\d{1,2}))',
        lambda m, ref: _safe_date(int(m.group(2)), int(m.group(3)), int(m.group(4))),
        'both'
    ))
    
    # 2026/03/25 or 2026/3/25
    patterns.append((
        r'((\d{4})/(\d{1,2})/(\d{1,2}))',
        lambda m, ref: _safe_date(int(m.group(2)), int(m.group(3)), int(m.group(4))),
        'both'
    ))
    
    # === Short date formats (without year) ===
    
    # 3月25日 or 3月25
    patterns.append((
        r'((\d{1,2})月(\d{1,2})日?)',
        lambda m, ref: _parse_short_date(int(m.group(2)), int(m.group(3)), ref),
        'both'
    ))
    
    # 4-digit MMDD format: 0325
    patterns.append((
        r'(?<![/\-\.年\d])((\d{2})(\d{2}))(?![/\-\.])',
        lambda m, ref: _parse_short_date(int(m.group(2)), int(m.group(3)), ref) 
                       if 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(3)) <= 31 else None,
        'both'
    ))
    
    # 3.25 format (must not be part of year format)
    patterns.append((
        r'(?<!\d)((\d{1,2})\.(\d{1,2}))(?!\.\d)',
        lambda m, ref: _parse_short_date(int(m.group(2)), int(m.group(3)), ref)
                       if 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(3)) <= 31 else None,
        'both'
    ))
    
    # 3/25 format
    patterns.append((
        r'(?<!\d)((\d{1,2})/(\d{1,2}))(?!/)',
        lambda m, ref: _parse_short_date(int(m.group(2)), int(m.group(3)), ref)
                       if 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(3)) <= 31 else None,
        'both'
    ))
    
    # 3-25 format (must not be part of year format)
    patterns.append((
        r'(?<!\d)((\d{1,2})-(\d{1,2}))(?!-)',
        lambda m, ref: _parse_short_date(int(m.group(2)), int(m.group(3)), ref)
                       if 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(3)) <= 31 else None,
        'both'
    ))
    
    # === English dates ===
    
    # today/tonight
    patterns.append((
        r'(?i)(today|tonight)',
        lambda m, ref: ref,
        'both'
    ))
    
    # tomorrow
    patterns.append((
        r'(?i)(tomorrow)',
        lambda m, ref: ref + timedelta(days=1),
        'both'
    ))
    
    # next week (no day = Monday)
    patterns.append((
        r'(?i)(next\s+week)(?!\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun))',
        lambda m, ref: _get_next_week_day(ref, 0),
        'both'
    ))
    
    # next monday/tuesday/etc
    patterns.append((
        r'(?i)(next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun))',
        lambda m, ref: _get_next_week_day(ref, WEEKDAY_MAP[m.group(2).lower()]),
        'both'
    ))
    
    # in N days
    patterns.append((
        r'(?i)(in\s+(\d+)\s+days?)',
        lambda m, ref: ref + timedelta(days=int(m.group(2))),
        'both'
    ))
    
    # in N weeks
    patterns.append((
        r'(?i)(in\s+(\d+)\s+weeks?)',
        lambda m, ref: ref + timedelta(weeks=int(m.group(2))),
        'both'
    ))
    
    # end of month
    patterns.append((
        r'(?i)(end\s+of\s+month)',
        lambda m, ref: _get_month_end(ref),
        'both'
    ))
    
    return patterns


def _safe_date(year: int, month: int, day: int) -> date | None:
    """Safely create a date, returning None if invalid."""
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _try_pattern(text: str, pattern: str, extractor, position: str, reference: date) -> tuple[str, str] | None:
    """Try to match a pattern at start or end of text.
    
    Returns (date_str, cleaned_text) if matched, None otherwise.
    """
    # Check if pattern has case-insensitive flag
    flags = 0
    if pattern.startswith('(?i)'):
        flags = re.IGNORECASE
        pattern = pattern[4:]  # Remove the (?i) prefix
    
    # Try at start
    if position in ('start', 'both'):
        # Match at start, possibly followed by space/separator
        start_pattern = r'^' + pattern + r'[\s,，:：]?'
        match = re.search(start_pattern, text, flags)
        if match:
            result_date = extractor(match, reference)
            if result_date:
                cleaned = text[match.end():].strip()
                return result_date.isoformat(), cleaned
    
    # Try at end
    if position in ('end', 'both'):
        # Match at end, possibly preceded by space/separator
        end_pattern = r'[\s,，:：]?' + pattern + r'$'
        match = re.search(end_pattern, text, flags)
        if match:
            result_date = extractor(match, reference)
            if result_date:
                cleaned = text[:match.start()].strip()
                return result_date.isoformat(), cleaned
    
    return None


def preprocess_input(
    raw_input: str, reference_date: date = None
) -> tuple[list[dict], list[str], list[dict]]:
    """Preprocess user input using deterministic rules.

    Pipeline per task:
        split → try recurring → else (extract_date → extract_time → reassemble)

    Args:
        raw_input: Raw user input containing one or more tasks.
        reference_date: Reference date for relative date calculations
            (defaults to today).

    Returns:
        Tuple of `(resolved, unresolved, pending_recurring)`:

        * `resolved`: tasks with a pinned date. Includes BOTH single-shot
          tasks parsed deterministically AND every expanded instance of a
          recurring rule detected in this input.
        * `unresolved`: task texts (possibly with a `[HH:MM]` prefix) that
          still need the LLM to assign a date.
        * `pending_recurring`: recurring rule dicts whose instances have
          been included in `resolved`. The CALLER is responsible for
          calling `recurring.register_rule` for each of these AFTER the
          user confirms the batch — registering before confirmation would
          persist rules the user might reject.
    """
    from time_parser import extract_time
    from recurring import (
        PRE_EXPAND_WEEKS,
        expand_rule,
        parse_recurring_rule,
    )

    tasks = split_tasks(raw_input)
    resolved: list[dict] = []
    unresolved: list[str] = []
    pending_recurring: list[dict] = []

    ref_d = reference_date or date.today()
    expand_end = ref_d + timedelta(weeks=PRE_EXPAND_WEEKS)

    for task in tasks:
        # Recurring patterns short-circuit everything else: they expand
        # straight into `resolved` and the rule is recorded for the caller
        # to register on confirm.
        rule = parse_recurring_rule(task)
        if rule is not None:
            instances = expand_rule(rule, ref_d, expand_end)
            if instances:
                rule["last_expanded_through"] = expand_end.isoformat()
                resolved.extend(instances)
                pending_recurring.append(rule)
            continue

        date_str, after_date = extract_date(task, reference_date)
        time_prefix, after_time = extract_time(after_date)

        text = after_time.strip()
        if time_prefix:
            text = f"{time_prefix} {text}".strip()

        if not text:
            continue

        if date_str:
            resolved.append({"date": date_str, "task": text})
        else:
            unresolved.append(text)

    return resolved, unresolved, pending_recurring
