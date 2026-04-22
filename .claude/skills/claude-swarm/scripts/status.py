#!/usr/bin/env python3
"""Show swarm task status. Live dashboard or one-shot snapshot."""
import sys
import time
import argparse

from . import db
from .errors import handle_connection_error

import datetime

_STATUS_STYLE = {
    "pending": ("yellow", "⏳"),
    "running": ("cyan",   "⚙ "),
    "done":    ("green",  "✓ "),
    "failed":  ("red",    "✗ "),
    "zombie":  ("red",    "💀"),
}

_ZOMBIE_THRESHOLD_S = 600  # 10 min with no completion = likely hung


def _task_label(prompt: str, max_len: int = 65) -> str:
    """Short display label. Expert prompts end with 'Task: <topic>'; extract just the topic."""
    lines = [l.strip() for l in (prompt or "").splitlines() if l.strip()]
    if not lines:
        return ""
    last = lines[-1]
    if last.startswith("Task: "):
        return last[6:][:max_len]  # explicit task label — always use, just truncate
    candidate = last if len(last) <= max_len else lines[0]
    return candidate[:max_len]

def _style(status):
    return _STATUS_STYLE.get(status, ("white", "? "))


def _effective_status(t):
    """Return 'zombie' for running tasks stuck beyond threshold."""
    if t.get("status") != "running":
        return t.get("status", "pending")
    if t.get("started_at"):
        age = (datetime.datetime.now(datetime.timezone.utc) - t["started_at"]).total_seconds()
        if age > _ZOMBIE_THRESHOLD_S:
            return "zombie"
    return "running"


def _make_table(tasks, title="Recent Tasks", live=False):
    from rich.table import Table
    from rich.text import Text
    from rich import box as rbox
    import datetime

    effective = [_effective_status(t) for t in tasks]
    done   = effective.count("done")
    fail   = effective.count("failed")
    run    = effective.count("running")
    zombie = effective.count("zombie")
    total  = len(tasks)

    parts = [f"{done}/{total} done"]
    if run:    parts.append(f"{run} running")
    if fail:   parts.append(f"{fail} failed")
    if zombie: parts.append(f"[red]{zombie} zombie[/red]")
    full_title = f"{title}  —  {', '.join(parts)}"

    table = Table(
        title=full_title, title_justify="left", title_style="bold",
        box=rbox.SIMPLE_HEAD, show_header=True, padding=(0, 1),
    )
    table.add_column("",       width=2)
    table.add_column("ID",     style="dim", width=9)
    table.add_column("Status", width=9)
    table.add_column("Elapsed", width=8, justify="right")
    table.add_column("Parent", style="dim", width=9)
    table.add_column("Prompt")

    zombies = 0
    for t in tasks:
        status = _effective_status(t)
        if status == "zombie":
            zombies += 1
        color, icon = _style(status)
        elapsed = ""
        if t.get("started_at"):
            end = t.get("completed_at") or datetime.datetime.now(datetime.timezone.utc)
            secs = int((end - t["started_at"]).total_seconds())
            elapsed = f"{secs}s"
        if live and status == "running":
            spinner_frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
            icon = spinner_frames[int(time.time() * 8) % len(spinner_frames)]
        parent = str(t["parent_id"])[:8] if t.get("parent_id") else "-"
        prompt = _task_label(t.get("prompt") or "")
        table.add_row(
            Text(icon,              style=color),
            Text(str(t["id"])[:8],  style="dim"),
            Text(status,            style=color),
            Text(elapsed,           style="dim"),
            parent,
            Text(prompt,            style="dim"),
        )
    if zombies:
        table.caption = f"[red]{zombies} zombie task(s) detected — run swarm-cancel <id> to clean up[/red]"
    return table


def _plain_snapshot(tasks):
    """TTY-safe plain-text output for CI/pipes."""
    header = f"{'':2} {'ID':8}  {'STATUS':9}  {'ELAPSED':>7}  PROMPT"
    print(header)
    print("-" * 70)
    import datetime
    for t in tasks:
        status = t.get("status", "pending")
        _, icon = _style(status)
        elapsed = ""
        if t.get("started_at"):
            end = t.get("completed_at") or datetime.datetime.now(datetime.timezone.utc)
            secs = int((end - t["started_at"]).total_seconds())
            elapsed = f"{secs}s"
        prompt = (t.get("prompt") or "")[:55].split("\n")[0]
        print(f"{icon} {str(t['id'])[:8]}  {status:<9}  {elapsed:>7}  {prompt}")


def snapshot(limit=20, json_out=False):
    tasks = db.list_tasks(limit)
    if json_out:
        import json
        import datetime
        def _serial(o):
            if isinstance(o, datetime.datetime):
                return o.isoformat()
            return str(o)
        print(json.dumps(tasks, default=_serial, indent=2))
        return

    is_tty = sys.stdout.isatty()
    if is_tty:
        try:
            from rich.console import Console
            Console().print(_make_table(tasks))
            return
        except ImportError:
            pass
    _plain_snapshot(tasks)


def live_dashboard(limit=20, refresh=2):
    try:
        from rich.live import Live
        from rich.console import Console
        from rich.text import Text
    except ImportError:
        print("[swarm] rich not installed — showing snapshot instead", file=sys.stderr)
        snapshot(limit)
        return

    console = Console()
    console.print("[dim]Watching swarm tasks — Ctrl-C to exit[/dim]")
    try:
        with Live(console=console, refresh_per_second=refresh) as live:
            while True:
                tasks = db.list_tasks(limit)
                live.update(_make_table(tasks, title="Swarm Tasks", live=True))
                time.sleep(1.0 / refresh)
    except KeyboardInterrupt:
        pass


@handle_connection_error
def main():
    parser = argparse.ArgumentParser(description="Show swarm task status")
    parser.add_argument("--live", "-l", action="store_true", help="Live dashboard (auto-refresh)")
    parser.add_argument("--limit", "-n", type=int, default=20, help="Number of tasks to show")
    parser.add_argument("--json", action="store_true", help="JSON output (CI-safe)")
    args = parser.parse_args()

    if args.live:
        live_dashboard(args.limit)
    else:
        snapshot(args.limit, args.json)


if __name__ == "__main__":
    main()
