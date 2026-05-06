"""Gemini API client for task analysis and allocation.

Phase 0 keeps the original procedural shape of this module. Phase 1 will
introduce an `LLMProvider` abstraction that this file is rewritten on top of.
For now we just fix the immediate bugs:

  * No request timeout (UI could hang indefinitely on a bad network).
  * `print()` for diagnostics was lost under pythonw.

Note: there is intentionally NO fallback to a different Gemini model on 404.
If the configured `gemini_model` doesn't exist, the user gets a clear error
so they can fix their config; silently retrying on a different model would
hide the misconfiguration.
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


def call_gemini(system_prompt: str, user_message: str, config: dict) -> list[dict]:
    """Call Gemini API and return parsed task allocation.

    Uses exactly the configured `gemini_model`. If the model is unavailable
    (404), the error propagates so the user can correct their config — we do
    NOT silently retry on a different model.

    Raises on any failure.
    """
    from google import genai

    model = config.get("gemini_model", "gemini-3.1-flash-lite-preview")
    timeout = int(config.get("request_timeout_sec", 30))

    client = genai.Client(api_key=config["gemini_api_key"])

    # google-genai's HttpOptions.timeout is in milliseconds.
    try:
        gen_config = genai.types.GenerateContentConfig(
            system_instruction=system_prompt,
            http_options=genai.types.HttpOptions(timeout=timeout * 1000),
        )
    except (TypeError, AttributeError):
        # Older builds without HttpOptions; degrade gracefully.
        log.debug("HttpOptions not supported by installed google-genai; no timeout")
        gen_config = genai.types.GenerateContentConfig(system_instruction=system_prompt)

    log.info("Calling Gemini model=%s timeout=%ss", model, timeout)
    response = client.models.generate_content(
        model=model,
        contents=user_message,
        config=gen_config,
    )
    return parse_response(response.text)


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


def analyze_tasks(user_input: str, config: dict) -> list[dict]:
    """High-level entry point: split input, resolve dates deterministically,
    only call the LLM for the leftovers.
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

    ai_results = call_gemini(system_prompt, unresolved_text, config)
    log.info("LLM returned %d allocations", len(ai_results))

    return resolved + ai_results
