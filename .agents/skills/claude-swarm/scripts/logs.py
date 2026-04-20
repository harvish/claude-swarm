#!/usr/bin/env python3
"""Stream live output from a running swarm task."""
import sys
import time

from . import db
from .config import log_path
from .errors import handle_connection_error


def tail_task(task_id: str):
    lf_path = log_path(task_id)

    # Wait up to 5s for the log file to appear (task may not have started yet)
    waited = 0.0
    while not lf_path.exists() and waited < 5.0:
        time.sleep(0.2)
        waited += 0.2

    if not lf_path.exists():
        # Task may already be done — just print stored output
        task = db.get_task(task_id)
        if task and task.get("output"):
            print(task["output"])
        else:
            print(f"[swarm] no log file for {task_id[:8]} and task not yet started",
                  file=sys.stderr)
        return

    with lf_path.open("r") as f:
        while True:
            line = f.readline()
            if line:
                sys.stdout.write(line)
                sys.stdout.flush()
            else:
                # No new data — check if task is done or log file gone
                if not lf_path.exists():
                    break
                task = db.get_task(task_id)
                if task and task["status"] in ("done", "failed"):
                    # Drain any remaining lines
                    for line in f:
                        sys.stdout.write(line)
                    sys.stdout.flush()
                    break
                time.sleep(0.1)


@handle_connection_error
def main():
    if len(sys.argv) < 2:
        print("usage: swarm-logs <task_id>", file=sys.stderr)
        sys.exit(1)
    tail_task(sys.argv[1])


if __name__ == "__main__":
    main()
