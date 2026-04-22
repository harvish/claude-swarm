#!/usr/bin/env python3
"""Spawns a child Claude Code instance in a tmux window."""
import os
import sys
import argparse
import subprocess
import shlex

from . import db
from .config import TMUX_SESSION, PG_DSN
from .errors import handle_connection_error
from .utils import TASK_TIMEOUT_S

WORKER = os.path.join(os.path.dirname(__file__), "worker.py")

_AUTH_VARS = [
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
]


def ensure_session():
    result = subprocess.run(
        ["tmux", "has-session", "-t", TMUX_SESSION],
        capture_output=True,
    )
    if result.returncode != 0:
        subprocess.run(["tmux", "new-session", "-d", "-s", TMUX_SESSION], check=True)


def spawn(prompt: str, parent_id: str = None, workdir: str = None,
          tools: list[str] = None, task_type: str = "generic") -> str:
    db.init_schema()
    task_id = db.create_task(prompt, parent_id)
    short   = task_id[:8]

    ensure_session()

    scripts_parent = os.path.dirname(os.path.dirname(__file__))
    tools_arg      = f", allowed_tools={repr(tools)}" if tools else ""

    env_parts = [f"SWARM_PG_DSN={shlex.quote(PG_DSN)}", f"SWARM_TMUX_SESSION={shlex.quote(TMUX_SESSION)}"]
    for var in _AUTH_VARS:
        val = os.environ.get(var)
        if val:
            env_parts.append(f"{var}={shlex.quote(val)}")

    env_prefix = " ".join(env_parts)
    python_cmd = (
        f"import sys; sys.path.insert(0, {repr(scripts_parent)}); "
        f"from scripts.worker import run; "
        f"run({repr(task_id)}{tools_arg})"
    )
    cmd = f"{env_prefix} python3 -c {shlex.quote(python_cmd)}"
    if workdir:
        cmd = f"cd {shlex.quote(workdir)} && {cmd}"
    cmd += f"; echo '[task {short} finished]'; read"

    subprocess.run([
        "tmux", "new-window", "-t", TMUX_SESSION,
        "-n", short,
        cmd,
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
    parser.add_argument("--workdir",   default=None)
    parser.add_argument("--tools",     default=None)
    parser.add_argument("--task-type", default="generic")
    args  = parser.parse_args()
    tools = args.tools.split(",") if args.tools else None
    spawn(args.prompt, args.parent_id, args.workdir, tools, args.task_type)


if __name__ == "__main__":
    main()
