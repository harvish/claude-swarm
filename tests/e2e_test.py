#!/usr/bin/env python3
"""
End-to-end tests for the claude swarm system.
Run from project root: python3 tests/e2e_test.py
"""
import sys
import os
import time
import subprocess
import threading

from claude_swarm import db
from claude_swarm.wait import wait_for
from claude_swarm.spawn import spawn
from claude_swarm.config import TMUX_SESSION

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"

def check(name, condition, detail=""):
    if condition:
        print(f"  {PASS}  {name}")
    else:
        print(f"  {FAIL}  {name}" + (f": {detail}" if detail else ""))
    return condition

def test_db_connection():
    print("\n[1] DB connection")
    try:
        conn = db.connect()
        conn.close()
        check("connect to postgres", True)
        return True
    except Exception as e:
        check("connect to postgres", False, str(e))
        return False

def test_schema_init():
    print("\n[2] Schema init")
    try:
        db.init_schema()
        check("init_schema runs without error", True)
        # idempotent
        db.init_schema()
        check("init_schema is idempotent", True)
        return True
    except Exception as e:
        check("init_schema", False, str(e))
        return False

def test_task_lifecycle():
    print("\n[3] Task lifecycle (no claude)")
    task_id = db.create_task("test prompt for lifecycle")
    task = db.get_task(task_id)
    check("task created with status=pending", task["status"] == "pending")
    check("prompt stored correctly", task["prompt"] == "test prompt for lifecycle")

    db.set_running(task_id)
    task = db.get_task(task_id)
    check("status=running after set_running", task["status"] == "running")
    check("started_at set", task["started_at"] is not None)

    db.set_done(task_id, "hello output")
    task = db.get_task(task_id)
    check("status=done after set_done", task["status"] == "done")
    check("output stored", task["output"] == "hello output")
    check("completed_at set", task["completed_at"] is not None)
    return True

def test_parent_child():
    print("\n[4] Parent-child relationship")
    parent_id = db.create_task("parent task")
    child_id = db.create_task("child task", parent_id=parent_id)
    child = db.get_task(child_id)
    check("child has correct parent_id", str(child["parent_id"]) == parent_id)
    return True

def test_notify_listen():
    print("\n[5] LISTEN/NOTIFY")
    task_id = db.create_task("notify test task")
    db.set_running(task_id)

    received = []

    def listener():
        results = wait_for([task_id], timeout=10)
        if task_id in results:
            received.append(results[task_id])

    t = threading.Thread(target=listener, daemon=True)
    t.start()
    time.sleep(0.3)

    db.set_done(task_id, "notify output")
    t.join(timeout=10)

    check("listener received notification", len(received) == 1)
    if received:
        check("output matches", received[0]["output"] == "notify output")
    return len(received) == 1

def test_tmux_session():
    print("\n[6] Tmux session")
    result = subprocess.run(["tmux", "has-session", "-t", TMUX_SESSION], capture_output=True)
    existed = result.returncode == 0

    # ensure_session is called by spawn, test it via subprocess
    subprocess.run(["tmux", "new-session", "-d", "-s", TMUX_SESSION], capture_output=True)
    result = subprocess.run(["tmux", "has-session", "-t", TMUX_SESSION], capture_output=True)
    check("tmux session can be created", result.returncode == 0)

    if not existed:
        subprocess.run(["tmux", "kill-session", "-t", TMUX_SESSION], capture_output=True)
    return True

def test_worker_direct():
    print("\n[7] Worker with real claude (echo task)")
    task_id = db.create_task("Reply with exactly: SWARM_OK")

    result = subprocess.run(
        [sys.executable, "-m", "claude_swarm.worker", task_id],
        capture_output=True, text=True, timeout=60
    )
    task = db.get_task(task_id)
    check("worker exited cleanly", result.returncode == 0, result.stderr)
    check("status=done", task["status"] == "done", task.get("error"))
    check("output contains SWARM_OK", "SWARM_OK" in (task["output"] or ""), repr(task["output"]))
    return task["status"] == "done"

def test_spawn_and_wait():
    print("\n[8] Spawn via tmux + wait")
    task_id = spawn("Reply with exactly: SPAWN_OK")
    check("spawn returned a task_id", len(task_id) == 36)

    results = wait_for([task_id], timeout=120)
    check("wait_for returned result", task_id in results)
    if task_id in results:
        task = results[task_id]
        check("status=done", task["status"] == "done", task.get("error"))
        check("output contains SPAWN_OK", "SPAWN_OK" in (task["output"] or ""), repr(task["output"]))
    return task_id in results

def test_parallel_spawn():
    print("\n[9] Parallel spawn (3 children)")
    prompts = [
        "Reply with exactly: PARALLEL_A",
        "Reply with exactly: PARALLEL_B",
        "Reply with exactly: PARALLEL_C",
    ]
    task_ids = [spawn(p) for p in prompts]
    check("spawned 3 tasks", len(task_ids) == 3)

    results = wait_for(task_ids, timeout=180)
    check("all 3 completed", len(results) == 3)
    for i, (tid, expected) in enumerate(zip(task_ids, ["PARALLEL_A", "PARALLEL_B", "PARALLEL_C"])):
        if tid in results:
            task = results[tid]
            check(f"task {i+1} status=done", task["status"] == "done")
            check(f"task {i+1} output correct", expected in (task["output"] or ""), repr(task["output"]))
    return len(results) == 3

def test_list_tasks():
    print("\n[10] list_tasks")
    tasks = db.list_tasks(50)
    check("returns a list", isinstance(tasks, list))
    check("has tasks", len(tasks) > 0)
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("Claude Swarm — End-to-End Tests")
    print("=" * 50)

    tests = [
        test_db_connection,
        test_schema_init,
        test_task_lifecycle,
        test_parent_child,
        test_notify_listen,
        test_tmux_session,
        test_worker_direct,
        test_spawn_and_wait,
        test_parallel_spawn,
        test_list_tasks,
    ]

    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  {FAIL}  unhandled exception: {e}")

    total = len(tests)
    print(f"\n{'=' * 50}")
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 50)
    sys.exit(0 if passed == total else 1)
