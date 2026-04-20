#!/usr/bin/env python3
"""Blocks until one or more task IDs complete, then prints their outputs."""
import sys
import select
import time

import psycopg2

from . import db
from .config import PG_DSN
from .errors import handle_connection_error

def wait_for(task_ids: list[str], timeout: int = 300) -> dict:
    pending = set(task_ids)
    results = {}

    for tid in list(pending):
        task = db.get_task(tid)
        if task["status"] in ("done", "failed"):
            results[tid] = task
            pending.discard(tid)

    if not pending:
        return results

    conn = psycopg2.connect(PG_DSN)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("LISTEN task_complete")

    is_tty = sys.stderr.isatty()
    start = time.monotonic()
    deadline = start + timeout

    while pending:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break

        wait = min(1.0, remaining)
        ready = select.select([conn], [], [], wait)[0]

        if ready:
            conn.poll()
            for notify in conn.notifies:
                tid = notify.payload
                if tid in pending:
                    results[tid] = db.get_task(tid)
                    pending.discard(tid)
            conn.notifies.clear()

        # re-check DB for any tasks that may have completed without notify
        for tid in list(pending):
            task = db.get_task(tid)
            if task["status"] in ("done", "failed"):
                results[tid] = task
                pending.discard(tid)

        if is_tty and pending:
            elapsed = int(time.monotonic() - start)
            statuses = {}
            for tid in pending:
                t = db.get_task(tid)
                statuses[t["status"]] = statuses.get(t["status"], 0) + 1
            parts = "  ".join(f"{v} {k}" for k, v in statuses.items())
            sys.stderr.write(f"\r[swarm] waiting: {parts}  ({elapsed}s){'':<10}")
            sys.stderr.flush()

    if is_tty:
        sys.stderr.write("\r" + " " * 60 + "\r")
        sys.stderr.flush()

    cur.close()
    conn.close()

    for tid in pending:
        results[tid] = {"status": "timeout", "output": None, "error": "timed out"}

    return results

@handle_connection_error
def main():
    task_ids = sys.argv[1:]
    if not task_ids:
        print("usage: swarm-wait <task_id> [...]", file=sys.stderr)
        sys.exit(1)

    results = wait_for(task_ids)
    sep = "=" * 60
    for tid in task_ids:
        task = results.get(tid)
        if not task:
            continue
        status = task["status"]
        print(sep)
        print(f"  {tid[:8]}  [{status}]")
        print(sep)
        body = task.get("output") or task.get("error") or ""
        if body:
            print(body)
        print()

if __name__ == "__main__":
    main()
