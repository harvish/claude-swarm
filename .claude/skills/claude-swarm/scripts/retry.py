#!/usr/bin/env python3
"""Re-spawn a failed or timed-out task using the same prompt."""
import sys

from . import db
from .spawn import spawn
from .errors import handle_connection_error


def retry(task_id: str) -> str:
    task = db.get_task(task_id)
    status = task["status"]
    if status not in ("failed", "timeout"):
        print(
            f"[swarm] task {task_id[:8]} has status '{status}' — "
            "only failed or timed-out tasks can be retried.",
            file=sys.stderr,
        )
        sys.exit(1)

    prompt    = task["prompt"]
    parent_id = str(task["parent_id"]) if task.get("parent_id") else None

    # Detect original task_type from prompt prefix (best-effort)
    if prompt.startswith("You are a research expert"):
        task_type = "researcher"
    elif prompt.startswith("You are a data and code analyst"):
        task_type = "analyst"
    elif prompt.startswith("You are a coding expert"):
        task_type = "coder"
    elif prompt.startswith("You are a synthesis expert"):
        task_type = "synthesizer"
    else:
        task_type = "generic"

    print(f"[swarm] retrying {task_id[:8]} ({task_type}, was {status})", file=sys.stderr)
    return spawn(prompt, parent_id=parent_id, tools=None, task_type=task_type)


@handle_connection_error
def main():
    if len(sys.argv) < 2:
        print("usage: swarm-retry <task_id>", file=sys.stderr)
        sys.exit(1)
    retry(sys.argv[1])


if __name__ == "__main__":
    main()
