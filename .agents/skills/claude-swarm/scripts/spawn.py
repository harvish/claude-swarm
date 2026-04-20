#!/usr/bin/env python3
"""Spawns a child Claude Code instance in a tmux window."""
import os
import sys
import argparse
import subprocess

from . import db
from .config import TMUX_SESSION
from .errors import handle_connection_error

WORKER = os.path.join(os.path.dirname(__file__), "worker.py")

def ensure_session():
    result = subprocess.run(
        ["tmux", "has-session", "-t", TMUX_SESSION],
        capture_output=True
    )
    if result.returncode != 0:
        subprocess.run(["tmux", "new-session", "-d", "-s", TMUX_SESSION], check=True)

def spawn(prompt: str, parent_id: str = None, workdir: str = None,
          tools: list[str] = None, task_type: str = "generic") -> str:
    db.init_schema()
    task_id = db.create_task(prompt, parent_id)
    short = task_id[:8]

    ensure_session()

    cmd = f"python3 -m claude_swarm.worker {task_id}"
    if tools:
        cmd += f" --tools {','.join(tools)}"
    if workdir:
        cmd = f"cd {workdir} && {cmd}"
    cmd += f"; echo '[task {short} finished]'; read"

    subprocess.run([
        "tmux", "new-window", "-t", TMUX_SESSION,
        "-n", short,
        cmd
    ], check=True)

    print(task_id)
    print(
        f"[swarm] spawned {task_type} task {short}  "
        f"(tmux attach -t {TMUX_SESSION} to watch live)",
        file=sys.stderr,
    )
    return task_id

@handle_connection_error
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt")
    parser.add_argument("--parent-id", default=None)
    parser.add_argument("--workdir", default=None)
    parser.add_argument("--tools", default=None)
    parser.add_argument("--task-type", default="generic")
    args = parser.parse_args()
    tools = args.tools.split(",") if args.tools else None
    spawn(args.prompt, args.parent_id, args.workdir, tools, args.task_type)

if __name__ == "__main__":
    main()
