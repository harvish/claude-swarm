#!/usr/bin/env python3
"""
Runs a single Claude Code task non-interactively, saves output to DB.
Usage: invoked by spawn.py via tmux; not called directly.
"""
import os
import subprocess

from . import db
from .config import log_path

def run(task_id: str, allowed_tools: list[str] = None):
    task = db.get_task(task_id)
    db.set_running(task_id)

    cmd = ["claude", "-p", task["prompt"]]
    if allowed_tools:
        cmd += ["--allowedTools", ",".join(allowed_tools)]
    max_tokens = os.environ.get("CLAUDE_MAX_TOKENS")
    if max_tokens:
        cmd += ["--max-tokens", max_tokens]

    lf_path = log_path(task_id)
    lines = []

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        with lf_path.open("w", buffering=1) as lf:
            for line in proc.stdout:
                lf.write(line)
                lines.append(line)
        proc.wait(timeout=300)

        output = "".join(lines).strip()
        if proc.returncode != 0:
            db.set_failed(task_id, output or f"exit code {proc.returncode}")
        else:
            db.set_done(task_id, output)
    except subprocess.TimeoutExpired:
        proc.kill()
        db.set_failed(task_id, "timeout after 300s")
    except Exception as e:
        db.set_failed(task_id, str(e))
    finally:
        pass  # log file preserved for post-mortem; use swarm-clean --logs to purge

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("task_id")
    parser.add_argument("--tools", default=None)
    args = parser.parse_args()
    tools = args.tools.split(",") if args.tools else None
    run(args.task_id, tools)
