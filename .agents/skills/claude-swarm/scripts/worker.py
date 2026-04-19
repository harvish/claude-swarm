#!/usr/bin/env python3
"""
Runs a single Claude Code task non-interactively, saves output to DB.
Usage: invoked by spawn.py via tmux; not called directly.
"""
import sys
import os
import subprocess

from . import db

def run(task_id: str, allowed_tools: list[str] = None):
    task = db.get_task(task_id)
    db.set_running(task_id)

    cmd = ["claude", "-p", task["prompt"]]
    if allowed_tools:
        cmd += ["--allowedTools", ",".join(allowed_tools)]
    model = os.environ.get("CLAUDE_MODEL")
    if model:
        cmd += ["--model", model]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        output = result.stdout.strip()
        if result.returncode != 0:
            db.set_failed(task_id, result.stderr.strip() or f"exit code {result.returncode}")
        else:
            db.set_done(task_id, output)
    except subprocess.TimeoutExpired:
        db.set_failed(task_id, "timeout after 300s")
    except Exception as e:
        db.set_failed(task_id, str(e))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("task_id")
    parser.add_argument("--tools", default=None)
    args = parser.parse_args()
    tools = args.tools.split(",") if args.tools else None
    run(args.task_id, tools)
