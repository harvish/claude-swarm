#!/usr/bin/env python3
"""
Runs a single Claude Code task non-interactively, saves output to DB.
Invoked by spawn.py via tmux; not called directly.
"""
import subprocess

from . import db
from .config import log_path
from .utils import TASK_TIMEOUT_S


def run(task_id: str, allowed_tools: list[str] = None):
    db.set_running(task_id)
    task = db.get_task(task_id)

    cmd = ["claude", "-p", task["prompt"]]
    if allowed_tools:
        cmd += ["--allowedTools", ",".join(allowed_tools)]

    lf_path = log_path(task_id)
    lines   = []

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
        proc.wait(timeout=TASK_TIMEOUT_S)

        output = "".join(lines).strip()
        if proc.returncode != 0:
            db.set_failed(task_id, output or f"exit code {proc.returncode}")
        else:
            db.set_done(task_id, output)
    except subprocess.TimeoutExpired:
        proc.kill()
        db.set_failed(task_id, f"timeout after {TASK_TIMEOUT_S}s")
    except Exception as e:
        db.set_failed(task_id, str(e))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("task_id")
    parser.add_argument("--tools", default=None)
    args  = parser.parse_args()
    tools = args.tools.split(",") if args.tools else None
    run(args.task_id, tools)
