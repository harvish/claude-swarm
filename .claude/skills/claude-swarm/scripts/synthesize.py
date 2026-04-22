#!/usr/bin/env python3
"""Spawn a synthesizer over the outputs of one or more completed tasks."""
import sys

from . import db
from .expert import spawn_expert
from .errors import handle_connection_error
from .utils import task_label


def synthesize(task_ids: list[str], question: str = "", parent_id: str = None) -> str:
    sections = []
    labels   = []
    errors   = []

    for tid in task_ids:
        task   = db.get_task(tid)
        status = task.get("status", "unknown")
        label  = task_label(task.get("prompt") or "")
        labels.append(label or tid[:8])

        if status != "done":
            errors.append(f"  task {tid[:8]} is '{status}' (expected 'done')")
            continue

        output = (task.get("output") or "").strip()
        if not output:
            errors.append(f"  task {tid[:8]} has no output")
            continue

        header = f"=== {label or tid[:8]} ==="
        sections.append(f"{header}\n\n{output}")

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        if not sections:
            print("[swarm] no usable outputs — aborting synthesis", file=sys.stderr)
            sys.exit(1)

    body = "\n\n---\n\n".join(sections)
    if question:
        task_str = f"{question}\n\nResearch results to synthesize:\n\n{body}"
    else:
        topic = " + ".join(labels[:3])
        if len(labels) > 3:
            topic += f" + {len(labels)-3} more"
        task_str = f"Synthesize the following research results on: {topic}\n\n{body}"

    print(f"[swarm] synthesizing {len(sections)} result(s)", file=sys.stderr)
    return spawn_expert("synthesizer", task_str, parent_id=parent_id)


@handle_connection_error
def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Spawn a synthesizer over completed task outputs"
    )
    parser.add_argument("task_ids", nargs="+", metavar="task_id",
                        help="IDs of completed tasks to synthesize")
    parser.add_argument("--question", "-q", default="",
                        help="Optional guiding question for the synthesizer")
    parser.add_argument("--parent-id", default=None,
                        help="Link to a parent task for lineage tracking")
    args = parser.parse_args()
    synthesize(args.task_ids, question=args.question, parent_id=args.parent_id)


if __name__ == "__main__":
    main()
