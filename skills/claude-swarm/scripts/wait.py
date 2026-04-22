#!/usr/bin/env python3
"""Blocks until one or more task IDs complete, then prints their outputs."""
import sys
import select
import time
import datetime

import psycopg2

from . import db
from .config import PG_DSN
from .errors import handle_connection_error
from .utils import task_label, style, TASK_TIMEOUT_S


def _elapsed(task):
    if not task.get("started_at"):
        return ""
    end = task.get("completed_at") or datetime.datetime.now(datetime.timezone.utc)
    secs = int((end - task["started_at"]).total_seconds())
    return f"{secs}s"


def _last_log_line(task_id: str) -> str:
    """Return last non-empty line from the task's live log file, if it exists."""
    try:
        from .config import log_path
        lf = log_path(task_id)
        if not lf.exists():
            return ""
        with lf.open("rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 2048))
            tail = f.read().decode("utf-8", errors="replace")
        lines = [l.strip() for l in tail.splitlines() if l.strip()]
        return lines[-1][:80] if lines else ""
    except Exception:
        return ""


def _make_table(task_ids, task_cache, pending, start_mono, title="Tasks"):
    from rich.table import Table
    from rich.text import Text
    from rich import box as rbox

    done_count = sum(1 for tid in task_ids if task_cache.get(tid, {}).get("status") == "done")
    fail_count = sum(1 for tid in task_ids if task_cache.get(tid, {}).get("status") == "failed")
    total      = len(task_ids)
    wall       = int(time.monotonic() - start_mono)

    header = f"{title}  {done_count}/{total} done"
    if fail_count:
        header += f"  {fail_count} failed"
    if pending:
        header += f"  —  {wall}s"

    show_preview = bool(pending)

    table = Table(
        title=header, title_justify="left", title_style="bold",
        box=rbox.SIMPLE_HEAD, show_header=True, padding=(0, 1),
    )
    table.add_column("",        width=2)
    table.add_column("ID",      style="dim", width=9)
    table.add_column("Status",  width=9)
    table.add_column("Elapsed", width=8, justify="right")
    table.add_column("Prompt / Last output", no_wrap=True)

    for tid in task_ids:
        t      = task_cache.get(tid) or {}
        status = t.get("status", "pending")
        color, icon = style(status)

        if status == "running" and pending:
            spinner_frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
            icon = spinner_frames[int(time.monotonic() * 8) % len(spinner_frames)]

        if status == "running" and show_preview:
            preview = _last_log_line(tid)
            label   = Text(preview or "…", style="italic dim")
        else:
            label   = Text(task_label(t.get("prompt", "")), style="dim")

        table.add_row(
            Text(icon,              style=color),
            Text(tid[:8],           style="dim"),
            Text(status,            style=color),
            Text(_elapsed(t) or "", style="dim"),
            label,
        )
    return table


def wait_for(task_ids: list[str], timeout: int = TASK_TIMEOUT_S) -> dict:
    task_cache = {}
    pending    = set(task_ids)

    for tid in task_ids:
        t = db.get_task(tid)
        task_cache[tid] = t
        if t["status"] in ("done", "failed"):
            pending.discard(tid)

    if not pending:
        return task_cache

    conn = psycopg2.connect(PG_DSN)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("LISTEN task_complete")

    start    = time.monotonic()
    deadline = start + timeout

    def _poll():
        wait = min(0.5, max(0.0, deadline - time.monotonic()))
        ready = select.select([conn], [], [], wait)[0]
        if ready:
            conn.poll()
            for notify in conn.notifies:
                tid = notify.payload
                if tid in pending:
                    task_cache[tid] = db.get_task(tid)
                    pending.discard(tid)
            conn.notifies.clear()
        for tid in list(pending):
            t = db.get_task(tid)
            task_cache[tid] = t
            if t["status"] in ("done", "failed"):
                pending.discard(tid)

    is_tty = sys.stderr.isatty()

    if is_tty:
        try:
            from rich.live    import Live
            from rich.console import Console
            console = Console(stderr=True)
            with Live(console=console, refresh_per_second=4, transient=False) as live:
                while pending and time.monotonic() < deadline:
                    _poll()
                    live.update(_make_table(task_ids, task_cache, pending, start))
                live.update(_make_table(task_ids, task_cache, pending, start))
        except ImportError:
            while pending and time.monotonic() < deadline:
                _poll()
                elapsed = int(time.monotonic() - start)
                sys.stderr.write(
                    f"\r[swarm] {len(task_ids)-len(pending)}/{len(task_ids)} done  ({elapsed}s)      "
                )
                sys.stderr.flush()
            sys.stderr.write("\n")
    else:
        while pending and time.monotonic() < deadline:
            _poll()

    cur.close()
    conn.close()

    for tid in pending:
        task_cache[tid] = {
            "status": "timeout", "output": None, "error": "timed out",
            "prompt": task_cache.get(tid, {}).get("prompt", ""),
            "started_at": None, "completed_at": None,
        }

    return task_cache


def _wall_time(results) -> str:
    started   = [t["started_at"]   for t in results.values() if t.get("started_at")]
    completed = [t["completed_at"] for t in results.values() if t.get("completed_at")]
    if not started or not completed:
        return ""
    secs = int((max(completed) - min(started)).total_seconds())
    return f"{secs}s"


def _synthesis_hint(task_ids, results) -> str:
    research_ids = [
        tid for tid in task_ids
        if results.get(tid, {}).get("status") == "done"
        and "Task: " in (results[tid].get("prompt") or "")
    ]
    if len(research_ids) < 2:
        return ""
    return "swarm-synthesize " + " ".join(tid[:8] for tid in research_ids)


def _print_results(task_ids, results):
    try:
        from rich.console  import Console
        from rich.panel    import Panel
        from rich.markdown import Markdown
        from rich.text     import Text
        console = Console()
        console.print()

        done    = sum(1 for t in results.values() if t.get("status") == "done")
        failed  = sum(1 for t in results.values() if t.get("status") == "failed")
        timeout = sum(1 for t in results.values() if t.get("status") == "timeout")
        total   = len(task_ids)
        words   = sum(len((t.get("output") or "").split()) for t in results.values())
        wall    = _wall_time(results)
        parts   = [f"[green]{done}/{total} done[/green]"]
        if failed:  parts.append(f"[red]{failed} failed[/red]")
        if timeout: parts.append(f"[red]{timeout} timed out[/red]")
        parts.append(f"~{words:,} words")
        if wall:    parts.append(f"{wall} total")
        console.print("  " + "  ·  ".join(parts))
        console.print()

        for tid in task_ids:
            task = results.get(tid)
            if not task:
                continue
            status = task["status"]
            color, icon = style(status)
            topic      = task_label(task.get("prompt", ""), max_len=50)
            label_part = f"  —  {topic}" if topic else ""
            title      = Text(
                f"{icon} {tid[:8]}  [{status}]  {_elapsed(task)}{label_part}",
                style=f"bold {color}",
            )
            body   = task.get("output") or task.get("error") or ""
            footer = (
                f"[dim]Retry: swarm-retry {tid[:8]}[/dim]"
                if status in ("failed", "timeout") else None
            )
            console.print(Panel(
                Markdown(body) if body else Text("(no output)", style="dim"),
                title=title,
                border_style=color,
                subtitle=footer,
            ))

        hint = _synthesis_hint(task_ids, results)
        if hint:
            console.print(f"  [dim]Synthesize:[/dim]  {hint}")
            console.print()

    except ImportError:
        sep = "=" * 60
        for tid in task_ids:
            task = results.get(tid)
            if not task:
                continue
            print(sep)
            print(f"  {tid[:8]}  [{task['status']}]  {_elapsed(task)}")
            print(sep)
            body = task.get("output") or task.get("error") or ""
            if body:
                print(body)
            if task.get("status") in ("failed", "timeout"):
                print(f"  Retry: swarm-retry {tid[:8]}")
            print()


def _print_results_json(task_ids, results):
    import json
    import datetime

    def _serial(o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        return str(o)

    out = []
    for tid in task_ids:
        task   = results.get(tid) or {}
        output = task.get("output") or ""
        out.append({
            "id":         tid,
            "label":      task_label(task.get("prompt", "")),
            "status":     task.get("status", "unknown"),
            "elapsed":    _elapsed(task),
            "word_count": len(output.split()) if output else 0,
            "output":     output,
            "error":      task.get("error") or "",
        })
    print(json.dumps(out, default=_serial, indent=2))


@handle_connection_error
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Wait for swarm tasks to complete")
    parser.add_argument("task_ids", nargs="+", metavar="task_id")
    parser.add_argument("--timeout", "-t", type=int, default=TASK_TIMEOUT_S,
                        help=f"Seconds before marking tasks timed out (default: {TASK_TIMEOUT_S})")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON (useful for scripting / orchestrator)")
    args = parser.parse_args()
    results = wait_for(args.task_ids, timeout=args.timeout)
    if args.json:
        _print_results_json(args.task_ids, results)
    else:
        _print_results(args.task_ids, results)


if __name__ == "__main__":
    main()
