"""Recurring task rules: weekly / monthly patterns, pre-expanded.

Strategy (per PROJECT_DECISIONS.md D1, option A + C):
  * When a user types a recurring pattern, we parse it into a rule and
    immediately expand the next 12 weeks of instances. Those instances
    flow through the normal confirm view; the user sees what's being
    written and can cancel.
  * The rule itself is saved to `data/recurring.json` ONLY after the user
    confirms (in `ui._on_confirm` / `cli.add`). Cancelling drops it.
  * On every app startup, `extend_all()` tops up each saved rule's
    expansion window so we always have ~12 weeks ahead.

Supported patterns (all in Chinese or English):
  * Weekly:   每周一  /  每周一三五  /  每周一、三、五  /  every monday
  * Monthly:  每月15号  /  每月1日

Time-of-day prefix on the rule body is preserved by reusing the
`time_parser.extract_time` machinery (so `每周一 9点 健身房` becomes a
rule whose expanded instances all start with `[09:00] 健身房`).

Out of scope for now (would need cron-style parsing): biweekly, weekday
ranges, multi-day-of-month, "every other Tuesday", etc. Future work.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import date, datetime, timedelta

from constants import DATA_DIR, RECURRING_PATH
from logger import get_logger

log = get_logger(__name__)

# How far ahead we keep the rolling expansion. 12 weeks ≈ 3 months: long
# enough to be useful, short enough that the user's calendar isn't flooded.
PRE_EXPAND_WEEKS = 12

# Schema version for the JSON file. Bump if the rule shape changes.
SCHEMA_VERSION = 1

# Chinese weekday characters → Python weekday() (Mon=0..Sun=6).
_WEEKDAY_CN: dict[str, int] = {
    "一": 0, "二": 1, "三": 2, "四": 3,
    "五": 4, "六": 5, "日": 6, "天": 6,
}

# English weekday tokens.
_WEEKDAY_EN: dict[str, int] = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

# 每周X[、X、X] body
_WEEKLY_CN = re.compile(
    r"^每周(?P<wdays>[一二三四五六日天]+(?:\s*[、,，]\s*[一二三四五六日天])*)"
    r"\s*(?P<rest>.+)$"
)

# 每月N号 / 每月N日 body
_MONTHLY_CN = re.compile(
    r"^每月(?P<day>\d{1,2})[号日]\s*(?P<rest>.+)$"
)

# every monday|tue|... body
_WEEKLY_EN = re.compile(
    r"^(?:every|weekly)\s+(?P<wday>monday|tuesday|wednesday|thursday|friday|"
    r"saturday|sunday|mon|tue|wed|thu|fri|sat|sun)\s+(?P<rest>.+)$",
    re.IGNORECASE,
)


def parse_recurring_rule(text: str) -> dict | None:
    """Try to parse `text` as a recurring rule.

    Returns a rule dict on success, or None if the text isn't a recognized
    recurring pattern. The dict has no `last_expanded_through` set yet —
    the caller (preprocess) fills that in after expanding.
    """
    if not text:
        return None
    text = text.strip()

    # 每周X
    m = _WEEKLY_CN.match(text)
    if m:
        weekdays: list[int] = []
        for ch in m.group("wdays"):
            if ch in _WEEKDAY_CN:
                wd = _WEEKDAY_CN[ch]
                if wd not in weekdays:
                    weekdays.append(wd)
        if not weekdays:
            return None
        rest = m.group("rest").strip()
        rule = _build_body(rest)
        if rule is None:
            return None
        return _new_rule(text, kind="weekly", weekdays=sorted(weekdays), **rule)

    # 每月N号/日
    m = _MONTHLY_CN.match(text)
    if m:
        day = int(m.group("day"))
        if not 1 <= day <= 31:
            return None
        rest = m.group("rest").strip()
        rule = _build_body(rest)
        if rule is None:
            return None
        return _new_rule(text, kind="monthly", days_of_month=[day], **rule)

    # English weekly
    m = _WEEKLY_EN.match(text)
    if m:
        wd = _WEEKDAY_EN[m.group("wday").lower()]
        rest = m.group("rest").strip()
        rule = _build_body(rest)
        if rule is None:
            return None
        return _new_rule(text, kind="weekly", weekdays=[wd], **rule)

    return None


def _build_body(rest: str) -> dict | None:
    """Pull a time prefix out of the rule body if present, return
    `{time_prefix, task_text}` or None if the body is empty."""
    from time_parser import extract_time

    if not rest.strip():
        return None
    time_prefix, task_text = extract_time(rest)
    task_text = task_text.strip()
    if not task_text:
        return None
    return {"time_prefix": time_prefix, "task_text": task_text}


def _new_rule(
    original_text: str,
    *,
    kind: str,
    weekdays: list[int] | None = None,
    days_of_month: list[int] | None = None,
    time_prefix: str | None = None,
    task_text: str,
) -> dict:
    rule = {
        "id": str(uuid.uuid4()),
        "schema_version": SCHEMA_VERSION,
        "original_text": original_text,
        "kind": kind,
        "time_prefix": time_prefix,
        "task_text": task_text,
        "created_at": datetime.now().isoformat(),
        "last_expanded_through": None,
    }
    if weekdays is not None:
        rule["weekdays"] = weekdays
    if days_of_month is not None:
        rule["days_of_month"] = days_of_month
    return rule


# ---------------------------------------------------------------------------
# Expansion
# ---------------------------------------------------------------------------

def expand_rule(rule: dict, from_date: date, to_date: date) -> list[dict]:
    """Generate `{date, task}` instances for `rule` between `from_date` and
    `to_date` (inclusive). Pure: no I/O.
    """
    if from_date > to_date:
        return []

    body = rule["task_text"]
    prefix = rule.get("time_prefix")
    task_text = f"{prefix} {body}".strip() if prefix else body

    instances: list[dict] = []
    if rule["kind"] == "weekly":
        weekdays = set(rule.get("weekdays", []))
        if not weekdays:
            return []
        d = from_date
        while d <= to_date:
            if d.weekday() in weekdays:
                instances.append({"date": d.isoformat(), "task": task_text})
            d += timedelta(days=1)
    elif rule["kind"] == "monthly":
        days = set(rule.get("days_of_month", []))
        if not days:
            return []
        d = from_date
        while d <= to_date:
            if d.day in days:
                instances.append({"date": d.isoformat(), "task": task_text})
            d += timedelta(days=1)
    return instances


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def load_rules() -> list[dict]:
    """Read `recurring.json`. Returns [] when missing or malformed."""
    if not os.path.exists(RECURRING_PATH):
        return []
    try:
        with open(RECURRING_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        log.warning("recurring.json is not a list; returning empty")
        return []
    except Exception:
        log.exception("Failed to load recurring rules")
        return []


def save_rules(rules: list[dict]) -> None:
    """Persist the full rules list, atomically replacing whatever's there."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(RECURRING_PATH, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)


def register_rule(rule: dict) -> None:
    """Append `rule` to the saved rules list.

    Called from the confirm path (`ui._on_confirm`, `cli.add`) only
    AFTER the user accepted the expansion. Calling it before user
    confirmation would persist rules the user might have rejected.
    """
    rules = load_rules()
    # Defensive: if the same rule (by id) is somehow already present,
    # don't duplicate it.
    if any(r.get("id") == rule.get("id") for r in rules):
        log.debug("Rule already registered; skipping: %s", rule.get("original_text"))
        return
    rules.append(rule)
    save_rules(rules)
    log.info("Registered recurring rule: %s", rule.get("original_text"))


# ---------------------------------------------------------------------------
# Periodic top-up
# ---------------------------------------------------------------------------

def extend_all(reference_date: date | None = None) -> list[dict]:
    """Top up every saved rule's expansion window to PRE_EXPAND_WEEKS ahead
    of `reference_date`. Returns the new instances that need writing to the
    calendar DB.

    Called once at startup. Idempotent on a given day.
    """
    if reference_date is None:
        reference_date = date.today()

    target_end = reference_date + timedelta(weeks=PRE_EXPAND_WEEKS)
    rules = load_rules()
    if not rules:
        return []

    new_instances: list[dict] = []
    extended_count = 0

    for rule in rules:
        last_str = rule.get("last_expanded_through")
        if last_str:
            try:
                last_d = date.fromisoformat(last_str)
            except ValueError:
                last_d = reference_date - timedelta(days=1)
        else:
            last_d = reference_date - timedelta(days=1)

        if target_end > last_d:
            window_start = last_d + timedelta(days=1)
            new_instances.extend(expand_rule(rule, window_start, target_end))
            rule["last_expanded_through"] = target_end.isoformat()
            extended_count += 1

    if extended_count:
        save_rules(rules)
        log.info(
            "Extended %d of %d rule(s); %d new instances",
            extended_count, len(rules), len(new_instances),
        )

    return new_instances
