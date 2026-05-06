"""LLM-backed task analysis (provider-agnostic orchestration).

Pipeline:
  1. `analyze_tasks(user_input, config)` is the public entry point.
  2. `task_parser.preprocess_input` resolves anything with an explicit date
     hint deterministically, no LLM call.
  3. Whatever is left goes to whichever provider `config["llm_provider"]`
     selects (Gemini today, DeepSeek next; future providers plug in by
     subclassing `providers.LLMProvider`).

This module owns the prompt builder and the JSON-parsing helper because both
are provider-agnostic; the provider-specific HTTP / SDK details live in
`providers/`.
"""
import json
import re
from datetime import datetime, date, timedelta

from logger import get_logger

log = get_logger(__name__)


def build_prompt(user_input: str, profile_text: str, existing_tasks: dict,
                 history_context: str = "", behavioral_patterns: str = "") -> tuple[str, str]:
    """Build the complete prompt for Gemini.

    Returns (system_prompt, user_message).
    """
    today = date.today().isoformat()

    system_prompt = f"""You are an intelligent task scheduling assistant. Your job is to analyze the user's task input and assign each task to the most appropriate date.

## Today's Date
{today}

## User Profile
{profile_text if profile_text else "No profile provided."}

## Current Task Load (Existing tasks by date)
{_format_existing_tasks(existing_tasks)}

{f"## Recent Interaction History{chr(10)}{history_context}" if history_context else ""}

{f"## Observed User Patterns{chr(10)}{behavioral_patterns}" if behavioral_patterns else ""}

## Input Format
Users may input tasks in various formats. You must intelligently parse and split them:

**Task separators to recognize:**
- Newlines (one task per line)
- Commas: Chinese (，) or English (,)
- Semicolons: Chinese (；) or English (;)
- Chinese enumeration comma (、)
- Spaces between short task descriptions (e.g., "买菜 洗衣服 打扫卫生")
- Mixed formats: some tasks on the same line, some on different lines

**Date hints that may appear within task text:**
- Chinese relative: 今天, 明天, 后天, 大后天, 今晚, 下周, 下周一~日, 这周五, 月底, 月初, 下个月, 这个月
- Relative expressions: 3天后, 一周内, 两周后, 几天后
- Short dates: 3月25, 3.25, 0325, 3/25, 3-25
- Full dates: 2026年3月25日, 2026-03-25, 2026/03/25
- Day of week: 周一~周日, 星期一~星期天, 礼拜一~礼拜天
- English: today, tonight, tomorrow, next week, next Monday~Sunday, in 3 days, end of month, etc.

## Instructions
1. **Parse and split tasks intelligently:**
   - Split input by recognized separators (newlines, commas, semicolons, enumeration commas)
   - If a single line contains what appears to be multiple short tasks separated by spaces (e.g., "买菜 洗衣服 打扫卫生"), split them into individual tasks
   - If a phrase is ambiguous or appears to be one coherent task (e.g., "完成项目报告初稿", "prepare quarterly financial report"), treat it as a single task
   - When in doubt, prefer treating text as one task rather than incorrectly splitting

2. **Respect explicit date hints in task text:**
   - If a task contains a date hint (any format listed above), you MUST assign it to that specific date
   - Extract the date hint and REMOVE it from the task text (return only the action portion)
   - Examples: "明天买菜" -> date=tomorrow, task="买菜"; "下周一开会" -> date=next Monday, task="开会"

3. **For tasks WITHOUT date hints, assign intelligently based on:**
   - The user's profile, habits, and scheduling rules
   - Current task load on each date (avoid overloading busy days)
   - Task urgency and estimated effort
   - The user's observed behavioral patterns and preferences

4. You may assign tasks to ANY future date - there is no hard limit. Use your judgment based on task nature.

5. PRESERVE the user's original language - do NOT translate task descriptions.

6. Handle each task independently - different tasks can have different dates.

## Output Format
Respond with ONLY a JSON array, no other text:
[
  {{"date": "YYYY-MM-DD", "task": "task text without date hint"}}
]
"""
    return system_prompt, user_input


def _format_existing_tasks(tasks: dict) -> str:
    if not tasks:
        return "No existing tasks in the upcoming period."

    lines = []
    for date_str in sorted(tasks.keys()):
        task_list = tasks[date_str]
        total = len(task_list)
        done = sum(1 for t in task_list if t["done"])
        pending = total - done
        lines.append(f"- {date_str}: {pending} pending, {done} completed")
        for t in task_list:
            status = "[done]" if t["done"] else "[pending]"
            lines.append(f"  {status} {t['text']}")
    return "\n".join(lines)


def parse_response(response_text: str) -> list[dict]:
    """Parse Gemini response to extract a JSON task list.

    Tolerates the response being wrapped in ```json ... ``` fences.
    """
    text = response_text.strip()

    code_block_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if code_block_match:
        text = code_block_match.group(1).strip()

    result = json.loads(text)

    if not isinstance(result, list):
        raise ValueError("Expected JSON array from AI response")

    validated = []
    for item in result:
        if "date" in item and "task" in item:
            datetime.strptime(item["date"], "%Y-%m-%d")  # validates format
            validated.append({"date": item["date"], "task": item["task"]})

    if not validated:
        raise ValueError("No valid task allocations in AI response")

    return validated


def analyze_tasks(user_input: str, config: dict, *, force_high_quality: bool = False) -> list[dict]:
    """High-level entry point: split input, resolve dates deterministically,
    only call the LLM for the leftovers.

    Args:
        user_input: raw text from the user.
        config: app config dict (`load_config()`).
        force_high_quality: when True and the active provider supports a tier
            split (e.g. DeepSeek pro vs flash), force the higher-quality
            variant. Wired up to the "Re-run with Pro" button in the UI.
    """
    from task_parser import preprocess_input
    from profile_manager import load_profile
    from calendar_db import get_tasks_in_range
    from history import get_recent_interactions, get_behavioral_patterns, get_feedback_summary

    # Step 1: regex-based preprocessing
    resolved, unresolved = preprocess_input(user_input)
    log.info("preprocess: %d resolved, %d unresolved", len(resolved), len(unresolved))

    # Step 2: short-circuit if everything was resolvable by rules
    if not unresolved:
        return resolved

    # Step 3: only the leftovers go to the LLM
    profile_text = load_profile()
    today = date.today()
    end = today + timedelta(days=30)
    existing_tasks = get_tasks_in_range(today.isoformat(), end.isoformat())

    history_context = get_recent_interactions(n=15)
    behavioral = get_behavioral_patterns()
    feedback = get_feedback_summary()

    patterns_text = ""
    if behavioral:
        patterns_text += behavioral
    if feedback:
        patterns_text += f"\n\n## User Satisfaction Feedback\n{feedback}"

    unresolved_text = "\n".join(unresolved)
    system_prompt, _ = build_prompt(
        unresolved_text, profile_text, existing_tasks,
        history_context=history_context,
        behavioral_patterns=patterns_text,
    )

    from providers import get_provider
    provider = get_provider(config)
    if force_high_quality and provider.supports_quality_override():
        log.info("Using %s high-quality variant (manual override)", provider.name)
        ai_results = provider.analyze_high_quality(system_prompt, unresolved_text)
    else:
        ai_results = provider.analyze(system_prompt, unresolved_text)
    log.info("Provider %s returned %d allocations", provider.name, len(ai_results))

    return resolved + ai_results
