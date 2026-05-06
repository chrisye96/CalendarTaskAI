"""Command-line interface for CalendarTaskAI."""
import sys
from datetime import date, datetime, timedelta

import click

from config_manager import load_config, set_config, is_configured, interactive_setup
from constants import APP_NAME, APP_VERSION


@click.group(invoke_without_command=True)
@click.version_option(version=APP_VERSION, prog_name=APP_NAME)
@click.pass_context
def cli(ctx):
    """CalendarTaskAI - AI-powered task scheduling for DesktopCal."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.argument("text", required=False, nargs=-1)
def add(text):
    """Add tasks using AI analysis.
    
    If TEXT is not provided, prompts for multi-line input.
    """
    # Check configuration first
    if not is_configured():
        click.echo(click.style("Error: API key not configured.", fg="red"))
        click.echo("Run 'calendarai config setup' to configure your API key.")
        return
    
    # Get user input
    if text:
        user_input = " ".join(text)
    else:
        click.echo("Enter tasks (empty line to finish):")
        lines = []
        while True:
            try:
                line = input()
                if not line:
                    break
                lines.append(line)
            except EOFError:
                break
        user_input = "\n".join(lines)
    
    if not user_input.strip():
        click.echo("No input provided.")
        return
    
    config = load_config()
    
    # Call AI to analyze tasks
    try:
        from ai_client import analyze_tasks
        click.echo("Analyzing tasks...")
        tasks = analyze_tasks(user_input, config)
    except Exception as e:
        # Save to retry queue on failure
        from retry_queue import save_pending
        save_pending(user_input)
        click.echo(click.style(f"API Error: {e}", fg="red"))
        click.echo("Your input has been saved. Run 'calendarai retry' when online.")
        return
    
    if not tasks:
        click.echo("No tasks were identified from your input.")
        return
    
    # Display allocation plan as table
    click.echo()
    click.echo(click.style("Allocation Plan:", fg="cyan", bold=True))
    click.echo("-" * 50)
    click.echo(f"{'Date':<14}| Task")
    click.echo("-" * 14 + "|" + "-" * 35)
    for task in tasks:
        click.echo(f"{task['date']:<14}| {task['task']}")
    click.echo("-" * 50)
    click.echo()
    
    # Ask for confirmation
    if click.confirm("Confirm this allocation?"):
        # Write tasks to database
        from calendar_db import write_tasks
        from history import log_interaction, should_ask_rating, save_rating
        
        try:
            count = write_tasks(tasks)
            click.echo(click.style(f"Successfully added {count} task(s).", fg="green"))
            log_interaction(user_input, tasks, accepted_tasks=tasks)
        except Exception as e:
            click.echo(click.style(f"Database Error: {e}", fg="red"))
            return
        
        # Check if we should ask for rating
        if should_ask_rating():
            click.echo()
            rating = click.prompt(
                "How satisfied are you with this allocation? (1-5)",
                type=click.IntRange(1, 5),
                default=None,
                show_default=False
            )
            if rating:
                save_rating(rating)
                click.echo("Thank you for your feedback!")
    else:
        # Log rejected interaction
        from history import log_interaction
        log_interaction(user_input, tasks, accepted_tasks=[], rejected_tasks=tasks)
        click.echo("Allocation cancelled.")


@cli.command()
@click.argument("action", type=click.Choice(["view", "edit", "reset"]), default="view")
def profile(action):
    """View, edit, or reset your profile.
    
    ACTION: view (default), edit, or reset
    """
    from profile_manager import load_profile, edit_profile, reset_profile
    
    if action == "view":
        content = load_profile()
        click.echo(content)
    elif action == "edit":
        click.echo("Opening profile in system editor...")
        edit_profile()
    elif action == "reset":
        if click.confirm("Reset profile to default template? This cannot be undone."):
            reset_profile()
            click.echo(click.style("Profile has been reset.", fg="green"))
        else:
            click.echo("Reset cancelled.")


@cli.command()
@click.argument("action", type=click.Choice(["show", "set", "setup"]), default="show")
@click.argument("key", required=False)
@click.argument("value", required=False)
def config(action, key, value):
    """View or modify configuration.
    
    ACTION: show (default), set KEY VALUE, or setup
    """
    if action == "show":
        cfg = load_config()
        click.echo(click.style("Current Configuration:", fg="cyan", bold=True))
        click.echo("-" * 40)
        for k, v in cfg.items():
            # Mask API key
            if k == "gemini_api_key" and v:
                display_value = f"***{v[-4:]}" if len(v) > 4 else "(set but short)"
            else:
                display_value = v
            click.echo(f"  {k}: {display_value}")
    elif action == "set":
        if not key:
            click.echo(click.style("Error: KEY is required for 'set' action.", fg="red"))
            return
        if value is None:
            click.echo(click.style("Error: VALUE is required for 'set' action.", fg="red"))
            return
        
        # Type conversion for known keys
        if key == "auto_start" or key == "retry_on_startup":
            value = value.lower() in ("true", "yes", "1")
        
        set_config(key, value)
        click.echo(click.style(f"Set {key} successfully.", fg="green"))
    elif action == "setup":
        interactive_setup()


@cli.command("list")
@click.argument("date_arg", default="today")
def list_tasks(date_arg):
    """List tasks for a date or date range.
    
    DATE: today, tomorrow, this-week, this-month, or YYYY-MM-DD
    """
    from calendar_db import get_tasks_for_date, get_tasks_in_range
    
    today = date.today()
    
    # Parse date argument
    if date_arg == "today":
        start_date = today
        end_date = today
    elif date_arg == "tomorrow":
        start_date = today + timedelta(days=1)
        end_date = start_date
    elif date_arg == "this-week":
        # Start from today, end on Sunday
        start_date = today
        days_until_sunday = (6 - today.weekday()) % 7
        end_date = today + timedelta(days=days_until_sunday if days_until_sunday else 7)
    elif date_arg == "this-month":
        start_date = today
        # Last day of current month
        if today.month == 12:
            end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
    else:
        # Try to parse as YYYY-MM-DD
        try:
            start_date = datetime.strptime(date_arg, "%Y-%m-%d").date()
            end_date = start_date
        except ValueError:
            click.echo(click.style(f"Invalid date format: {date_arg}", fg="red"))
            click.echo("Use: today, tomorrow, this-week, this-month, or YYYY-MM-DD")
            return
    
    # Get tasks
    try:
        if start_date == end_date:
            tasks = get_tasks_for_date(start_date.isoformat())
            tasks_by_date = {start_date.isoformat(): tasks} if tasks else {}
        else:
            tasks_by_date = get_tasks_in_range(start_date.isoformat(), end_date.isoformat())
    except Exception as e:
        click.echo(click.style(f"Database Error: {e}", fg="red"))
        return
    
    if not tasks_by_date:
        click.echo(f"No tasks found for {date_arg}.")
        return
    
    # Display tasks
    for date_str in sorted(tasks_by_date.keys()):
        tasks = tasks_by_date[date_str]
        click.echo(click.style(f"\n{date_str}", fg="cyan", bold=True))
        click.echo("-" * 30)
        for task in tasks:
            checkbox = "[x]" if task["done"] else "[ ]"
            color = "green" if task["done"] else None
            click.echo(click.style(f"  {checkbox} {task['text']}", fg=color))


@cli.command()
def today():
    """Show today's tasks (shortcut for 'list today')."""
    ctx = click.get_current_context()
    ctx.invoke(list_tasks, date_arg="today")


@cli.command(name="next")
@click.argument("days", type=click.IntRange(1, 365), default=7)
def next_(days):
    """Show tasks for the next N days (default 7).

    Includes today and the next N-1 days. Like `list this-week` but with a
    user-supplied window.
    """
    from calendar_db import get_tasks_in_range

    today_d = date.today()
    end_d = today_d + timedelta(days=days - 1)

    try:
        tasks_by_date = get_tasks_in_range(today_d.isoformat(), end_d.isoformat())
    except Exception as e:
        click.echo(click.style(f"Database Error: {e}", fg="red"))
        return

    if not tasks_by_date:
        click.echo(f"No tasks in the next {days} day(s).")
        return

    click.echo(click.style(
        f"Tasks for the next {days} day(s) ({today_d} to {end_d}):", fg="cyan"
    ))

    for date_str in sorted(tasks_by_date.keys()):
        click.echo(click.style(f"\n{date_str}", fg="cyan", bold=True))
        for task in tasks_by_date[date_str]:
            checkbox = "[x]" if task["done"] else "[ ]"
            color = "green" if task["done"] else None
            click.echo(click.style(f"  {checkbox} {task['text']}", fg=color))


@cli.command()
@click.argument("keyword")
def done(keyword):
    """Mark matching tasks as done."""
    from calendar_db import mark_done
    from history import log_modification
    
    try:
        matched = mark_done(keyword)
    except Exception as e:
        click.echo(click.style(f"Database Error: {e}", fg="red"))
        return
    
    if not matched:
        click.echo(f"No pending tasks found matching '{keyword}'.")
        return
    
    click.echo(click.style(f"Marked {len(matched)} task(s) as done:", fg="green"))
    for task in matched:
        click.echo(f"  [x] {task}")
        log_modification("done", task)


@cli.command()
@click.argument("keyword")
def undone(keyword):
    """Mark matching tasks as undone."""
    from calendar_db import mark_undone
    from history import log_modification
    
    try:
        matched = mark_undone(keyword)
    except Exception as e:
        click.echo(click.style(f"Database Error: {e}", fg="red"))
        return
    
    if not matched:
        click.echo(f"No completed tasks found matching '{keyword}'.")
        return
    
    click.echo(click.style(f"Marked {len(matched)} task(s) as undone:", fg="yellow"))
    for task in matched:
        click.echo(f"  [ ] {task}")
        log_modification("undone", task)


@cli.command()
@click.argument("keyword")
def delete(keyword):
    """Delete matching tasks."""
    from calendar_db import search_tasks, delete_task
    from history import log_modification
    
    # First show matching tasks
    try:
        matches = search_tasks(keyword)
    except Exception as e:
        click.echo(click.style(f"Database Error: {e}", fg="red"))
        return
    
    if not matches:
        click.echo(f"No tasks found matching '{keyword}'.")
        return
    
    click.echo(click.style("Matching tasks:", fg="yellow"))
    for match in matches:
        status = "[x]" if match["done"] else "[ ]"
        click.echo(f"  {match['date']} {status} {match['text']}")
    
    click.echo()
    if click.confirm(f"Delete {len(matches)} task(s)?"):
        try:
            deleted = delete_task(keyword)
            click.echo(click.style(f"Deleted {len(deleted)} task(s).", fg="green"))
            for task in deleted:
                log_modification("delete", task)
        except Exception as e:
            click.echo(click.style(f"Database Error: {e}", fg="red"))
    else:
        click.echo("Deletion cancelled.")


@cli.command()
@click.argument("keyword")
@click.argument("target_date")
def move(keyword, target_date):
    """Move matching tasks to a new date.
    
    TARGET_DATE format: YYYY-MM-DD
    """
    from calendar_db import move_task
    from history import log_modification
    
    # Validate date format
    try:
        datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        click.echo(click.style(f"Invalid date format: {target_date}", fg="red"))
        click.echo("Use YYYY-MM-DD format.")
        return
    
    try:
        moved = move_task(keyword, target_date)
    except Exception as e:
        click.echo(click.style(f"Database Error: {e}", fg="red"))
        return
    
    if not moved:
        click.echo(f"No tasks found matching '{keyword}'.")
        return
    
    click.echo(click.style(f"Moved {len(moved)} task(s) to {target_date}:", fg="green"))
    for task in moved:
        click.echo(f"  -> {task}")
        log_modification("move", task, details=f"moved to {target_date}")


@cli.command()
@click.argument("keyword")
def search(keyword):
    """Search tasks by keyword."""
    from calendar_db import search_tasks
    
    try:
        results = search_tasks(keyword)
    except Exception as e:
        click.echo(click.style(f"Database Error: {e}", fg="red"))
        return
    
    if not results:
        click.echo(f"No tasks found matching '{keyword}'.")
        return
    
    click.echo(click.style(f"Found {len(results)} task(s):", fg="cyan"))
    
    # Group by date
    by_date = {}
    for r in results:
        d = r["date"]
        if d not in by_date:
            by_date[d] = []
        by_date[d].append(r)
    
    for date_str in sorted(by_date.keys()):
        click.echo(click.style(f"\n{date_str}", fg="cyan", bold=True))
        for task in by_date[date_str]:
            checkbox = "[x]" if task["done"] else "[ ]"
            color = "green" if task["done"] else None
            click.echo(click.style(f"  {checkbox} {task['text']}", fg=color))


@cli.command()
@click.option("--format", "fmt", type=click.Choice(["md", "txt"]), default="md",
              help="Output format: md (Markdown) or txt (plain text)")
@click.option("--start", "start_date", help="Start date (YYYY-MM-DD)")
@click.option("--end", "end_date", help="End date (YYYY-MM-DD)")
def export(fmt, start_date, end_date):
    """Export tasks to stdout.
    
    Default range: this month. Redirect output to save to file.
    """
    from calendar_db import export_tasks
    
    today = date.today()
    
    # Default to this month
    if not start_date:
        start_date = date(today.year, today.month, 1).isoformat()
    if not end_date:
        if today.month == 12:
            end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
        end_date = end_date.isoformat()
    
    # Validate dates
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError as e:
        click.echo(click.style(f"Invalid date format: {e}", fg="red"))
        return
    
    try:
        output = export_tasks(start_date, end_date, fmt)
        click.echo(output)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"))


@cli.command()
@click.option("--out", "out_file", help="Output path. Defaults to ./calendartaskai-backup-YYYY-MM-DD.json")
def backup(out_file):
    """Export config (API keys redacted), profile, history, templates,
    recurring rules, and ±1 year of tasks to a JSON file.
    """
    import json
    from backup import create_backup

    if not out_file:
        out_file = f"calendartaskai-backup-{date.today().isoformat()}.json"

    try:
        data = create_backup()
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        click.echo(click.style(f"Backup failed: {e}", fg="red"))
        return

    click.echo(click.style(f"Backup written: {out_file}", fg="green"))


@cli.command()
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option("--overwrite-config", is_flag=True,
              help="Also overwrite non-key config fields. API keys are kept as-is.")
def restore(path, overwrite_config):
    """Restore from a backup JSON file.

    Profile, history, templates, and recurring rules are OVERWRITTEN.
    Tasks are APPENDED to the calendar (duplicates may result if the DB
    already had matching entries). Config API keys are never replaced.
    """
    import json
    from backup import restore_backup

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    click.echo(f"Backup created: {data.get('created_at', '?')} (app v{data.get('app_version', '?')})")
    if not click.confirm(
        "This will overwrite local profile/history/templates/recurring and append "
        "stored tasks to the calendar. Continue?",
        default=False,
    ):
        click.echo("Restore cancelled.")
        return

    try:
        counts = restore_backup(data, overwrite_config=overwrite_config)
    except Exception as e:
        click.echo(click.style(f"Restore failed: {e}", fg="red"))
        return

    click.echo(click.style("Restore complete:", fg="green"))
    for k, v in counts.items():
        click.echo(f"  {k}: {v}")


@cli.command()
def undo():
    """Undo the most recent batch of tasks added.

    Reverses exactly the last `add` (whether from CLI or GUI). Tasks are
    matched by date + exact text; tasks marked done since the original add
    are still removed.
    """
    from last_op import undo_last_add

    count, message = undo_last_add()
    fg = "green" if count else "yellow"
    click.echo(click.style(message, fg=fg))


@cli.command()
def refresh():
    """Show instructions to refresh DesktopCal view."""
    click.echo("Please switch pages or restart DesktopCal to refresh the calendar view.")


@cli.command()
def retry():
    """Retry all pending (failed) requests."""
    if not is_configured():
        click.echo(click.style("Error: API key not configured.", fg="red"))
        click.echo("Run 'calendarai config setup' to configure your API key.")
        return
    
    from retry_queue import load_pending, retry_all
    
    pending = load_pending()
    if not pending:
        click.echo("No pending requests to retry.")
        return
    
    click.echo(f"Retrying {len(pending)} pending request(s)...")
    
    config = load_config()
    result = retry_all(config)
    
    click.echo()
    click.echo(click.style(f"Success: {result['success']}", fg="green"))
    click.echo(click.style(f"Failed:  {result['failed']}", fg="red" if result['failed'] else None))
    
    # Show details
    for r in result["results"]:
        if "error" in r:
            click.echo(click.style(f"  [FAIL] {r['input'][:50]}... - {r['error']}", fg="red"))
        else:
            click.echo(click.style(f"  [OK] {r['input'][:50]}... - {r['written']} task(s)", fg="green"))


if __name__ == "__main__":
    cli()
