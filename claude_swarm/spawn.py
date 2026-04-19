#!/usr/bin/env python3
"""
Spawns a child Claude Code instance in a tmux window.
Usage: swarm-spawn <prompt> [--parent-id <uuid>] [--workdir <path>]
"""
import os
import argparse
import subprocess

from claude_swarm import db
from claude_swarm.config import TMUX_SESSION

WORKER = os.path.join(os.path.dirname(__file__), "worker.py")

def ensure_session():
    result = subprocess.run(
        ["tmux", "has-session", "-t", TMUX_SESSION],
        capture_output=True
    )
    if result.returncode != 0:
        subprocess.run(["tmux", "new-session", "-d", "-s", TMUX_SESSION], check=True)

def spawn(prompt: str, parent_id: str = None, workdir: str = None, tools: list[str] = None) -> str:
    db.init_schema()
    task_id = db.create_task(prompt, parent_id)
    short = task_id[:8]

    ensure_session()

    cmd = f"python3 {WORKER} {task_id}"
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
    return task_id

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt")
    parser.add_argument("--parent-id", default=None)
    parser.add_argument("--workdir", default=None)
    parser.add_argument("--tools", default=None, help="comma-separated allowed tools")
    args = parser.parse_args()
    tools = args.tools.split(",") if args.tools else None
    spawn(args.prompt, args.parent_id, args.workdir, tools)

if __name__ == "__main__":
    main()
