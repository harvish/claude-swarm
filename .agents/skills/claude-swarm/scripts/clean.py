#!/usr/bin/env python3
"""Close tmux windows for completed/failed swarm tasks."""
import sys
import subprocess

from . import db
from .config import TMUX_SESSION
from .errors import handle_connection_error


def clean():
    result = subprocess.run(
        ["tmux", "list-windows", "-t", TMUX_SESSION, "-F", "#{window_name}"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"[swarm] no tmux session named '{TMUX_SESSION}'", file=sys.stderr)
        return

    window_names = {name.strip() for name in result.stdout.splitlines() if name.strip()}

    tasks = db.list_tasks(500)
    done_shorts = {
        str(t["id"])[:8]
        for t in tasks
        if t["status"] in ("done", "failed")
    }

    to_close = window_names & done_shorts
    for name in sorted(to_close):
        subprocess.run(
            ["tmux", "kill-window", "-t", f"{TMUX_SESSION}:{name}"],
            capture_output=True,
        )

    print(f"[swarm] closed {len(to_close)} completed window(s)")


@handle_connection_error
def main():
    clean()


if __name__ == "__main__":
    main()
