#!/usr/bin/env python3
"""Blocks until one or more task IDs complete, then prints their outputs."""
import sys
import select

import psycopg2

from . import db
from .config import PG_DSN

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

    while pending:
        if select.select([conn], [], [], timeout)[0]:
            conn.poll()
            for notify in conn.notifies:
                tid = notify.payload
                if tid in pending:
                    results[tid] = db.get_task(tid)
                    pending.discard(tid)
            conn.notifies.clear()
        else:
            break  # timeout

    cur.close()
    conn.close()
    return results

def main():
    task_ids = sys.argv[1:]
    if not task_ids:
        print("usage: swarm-wait <task_id> [...]", file=sys.stderr)
        sys.exit(1)

    results = wait_for(task_ids)
    for tid, task in results.items():
        print(f"--- {tid[:8]} [{task['status']}] ---")
        print(task.get("output") or task.get("error") or "")

if __name__ == "__main__":
    main()
