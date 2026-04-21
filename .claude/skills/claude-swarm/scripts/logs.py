#!/usr/bin/env python3
"""Stream live output from a running swarm task."""
import sys
import time

from . import db
from .config import log_path
from .errors import handle_connection_error


def _tail_with_inotify(lf_path, task_id):
    """Zero-latency tail using Linux inotify."""
    import inotify_simple
    inotify = inotify_simple.INotify()
    inotify.add_watch(str(lf_path), inotify_simple.flags.MODIFY | inotify_simple.flags.DELETE_SELF)

    with lf_path.open("r") as f:
        while True:
            # drain any lines already in the file
            for line in f:
                sys.stdout.write(line)
                sys.stdout.flush()

            # wait for next write event (250ms timeout so we can check status)
            events = inotify.read(timeout=250)

            for event in events:
                if inotify_simple.flags.DELETE_SELF & event.mask:
                    return  # file removed, done

            task = db.get_task(task_id)
            if task and task["status"] in ("done", "failed"):
                for line in f:  # drain remainder
                    sys.stdout.write(line)
                sys.stdout.flush()
                return


def _tail_with_poll(lf_path, task_id):
    """100ms-poll fallback for non-Linux or missing inotify_simple."""
    with lf_path.open("r") as f:
        while True:
            line = f.readline()
            if line:
                sys.stdout.write(line)
                sys.stdout.flush()
            else:
                if not lf_path.exists():
                    return
                task = db.get_task(task_id)
                if task and task["status"] in ("done", "failed"):
                    for line in f:
                        sys.stdout.write(line)
                    sys.stdout.flush()
                    return
                time.sleep(0.1)


def tail_task(task_id: str):
    lf_path = log_path(task_id)

    # Wait up to 5s for the log file to appear
    waited = 0.0
    while not lf_path.exists() and waited < 5.0:
        time.sleep(0.2)
        waited += 0.2

    if not lf_path.exists():
        # Task may already be done — print stored output
        task = db.get_task(task_id)
        if task and task.get("output"):
            print(task["output"])
        else:
            print(f"[swarm] no log for {task_id[:8]} — task not started or already cleaned",
                  file=sys.stderr)
        return

    try:
        import inotify_simple
        _tail_with_inotify(lf_path, task_id)
    except (ImportError, OSError):
        _tail_with_poll(lf_path, task_id)


@handle_connection_error
def main():
    if len(sys.argv) < 2:
        print("usage: swarm-logs <task_id>", file=sys.stderr)
        sys.exit(1)
    tail_task(sys.argv[1])


if __name__ == "__main__":
    main()
