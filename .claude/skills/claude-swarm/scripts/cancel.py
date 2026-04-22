#!/usr/bin/env python3
"""Cancel a running swarm task."""
import sys
import subprocess

from . import db
from .config import TMUX_SESSION
from .errors import handle_connection_error


def cancel(task_id: str):
    short = task_id[:8]

    result = subprocess.run(
        ["tmux", "kill-window", "-t", f"{TMUX_SESSION}:{short}"],
        capture_output=True,
    )
    if result.returncode != 0:
        print(f"[swarm] warning: tmux window {short} not found (may have already exited)",
              file=sys.stderr)

    db.set_failed(task_id, "cancelled by user")
    print(f"[swarm] task {short} cancelled")


@handle_connection_error
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Cancel a running swarm task")
    parser.add_argument("task_id")
    args = parser.parse_args()
    cancel(args.task_id)


if __name__ == "__main__":
    main()
