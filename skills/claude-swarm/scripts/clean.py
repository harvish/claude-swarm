#!/usr/bin/env python3
"""Close tmux windows for completed/failed swarm tasks."""
import sys
import argparse
import subprocess

from . import db
from .config import TMUX_SESSION, log_path
from .errors import handle_connection_error


def clean(purge_logs: bool = False):
    result = subprocess.run(
        ["tmux", "list-windows", "-t", TMUX_SESSION, "-F", "#{window_name}"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"[swarm] no tmux session named '{TMUX_SESSION}'", file=sys.stderr)
        return

    window_names = {name.strip() for name in result.stdout.splitlines() if name.strip()}

    tasks = db.list_tasks(500)
    done_tasks = [t for t in tasks if t["status"] in ("done", "failed")]
    done_shorts = {str(t["id"])[:8] for t in done_tasks}

    to_close = window_names & done_shorts
    for name in sorted(to_close):
        subprocess.run(
            ["tmux", "kill-window", "-t", f"{TMUX_SESSION}:{name}"],
            capture_output=True,
        )
    print(f"[swarm] closed {len(to_close)} completed window(s)")

    if purge_logs:
        removed = 0
        for t in done_tasks:
            lf = log_path(str(t["id"]))
            if lf.exists():
                lf.unlink()
                removed += 1
        print(f"[swarm] removed {removed} log file(s)")


@handle_connection_error
def main():
    parser = argparse.ArgumentParser(description="Clean up completed swarm tasks")
    parser.add_argument("--logs", action="store_true", help="Also delete preserved log files")
    args = parser.parse_args()
    clean(purge_logs=args.logs)


if __name__ == "__main__":
    main()
