---
name: claude-swarm
description: Orchestrate parallel Claude Code agents for research, coding, and analysis. Use whenever tasks benefit from parallelism — multiple research topics, large codebases requiring simultaneous analysis, or any workflow where spawning specialized child agents (researcher, analyst, coder) would be faster than sequential work. Triggers on phrases like "research X and Y in parallel", "spawn agents for", "swarm", or any multi-track investigation where independent subtasks exist.
---

# Claude Swarm

Orchestrates child Claude Code instances via PostgreSQL + tmux. The parent agent spawns children, waits for their results via LISTEN/NOTIFY, and synthesizes the findings.

## Checking Configuration

Before running any swarm command, verify `SWARM_PG_DSN` is set in the environment:

```bash
python3 -c "from claude_swarm.config import PG_DSN; print('DSN:', PG_DSN[:30], '...')"
```

If the variable is missing or the connection fails, run the onboarding flow in `references/setup.md` automatically — ask the user for their PostgreSQL DSN, save it, install the package, and initialize the schema. Do not ask the user to do this manually.

## Spawning Tasks

**Generic task** — any prompt, unrestricted tools:
```bash
task_id=$(swarm-spawn "<prompt>")
# stderr: [swarm] spawned generic task a1b2c3d4  (tmux attach -t swarm to watch live)
```

**Expert task** — wraps the prompt in a role-specific system prompt with restricted tools:
```bash
swarm-expert researcher "<topic>"   # WebSearch + WebFetch
swarm-expert analyst "<subject>"    # WebSearch + WebFetch
swarm-expert coder "<task>"         # WebFetch + Read + Write + Bash
```

Capture the printed UUID from each spawn, then wait for completion:
```bash
swarm-wait <task_id> [<task_id2> <task_id3> ...]
```

`swarm-wait` shows a live status line while waiting, then prints a formatted result block for each task. Tasks that time out (300s default) are reported explicitly.

### Passing context
- `--workdir <path>` — child works in that directory
- `--parent-id <uuid>` — links child to parent task in the DB for lineage tracking

### When to auto-spawn (without being asked)

| Situation | Action |
|-----------|--------|
| Need current or live information | `swarm-expert researcher` |
| User asks about library versions, prices, recent events | `swarm-expert researcher` |
| Multiple independent sub-questions | Parallel researchers (one spawn per topic) |
| Large analysis task | `swarm-expert analyst` |
| Need working code for a sub-problem | `swarm-expert coder` |

When you would normally do a WebSearch or WebFetch inline, spawn a researcher instead and wait for its output — this keeps the parent session focused on synthesis.

## Watching Task Output Live

While a task is running, stream its output in real time:

```bash
swarm-logs <task_id>
```

`swarm-logs` waits up to 5s for the task to start, then tails the log line-by-line until the task completes. Combine with spawn for a "fire and watch" workflow:

```bash
task_id=$(swarm-spawn "research FAANG stocks")
swarm-logs "$task_id"
# ... streams output live, exits when done ...
swarm-wait "$task_id"   # grab the stored result
```

You can also attach to the tmux session to see all windows at once:
```bash
tmux attach -t swarm   # or $SWARM_TMUX_SESSION if customized
```

## Checking Status

Show recent tasks from the database:

```python
from claude_swarm import db
tasks = db.list_tasks(20)
for t in tasks:
    short = str(t['id'])[:8]
    parent = str(t['parent_id'])[:8] if t['parent_id'] else '-'
    elapsed = f"{(t['completed_at'] - t['started_at']).seconds}s" if t['completed_at'] and t['started_at'] else ''
    print(f"{short}  parent={parent}  status={t['status']:<8}  {elapsed:>5}  {t['prompt'][:60]}")
```

Color context: pending=waiting, running=in-progress, done=success, failed=error.

## Fetching Results

Fetch the full output of a completed task by ID prefix:

```python
from claude_swarm.config import PG_DSN
import psycopg2
conn = psycopg2.connect(PG_DSN); conn.autocommit = True
cur = conn.cursor()
cur.execute(
    "SELECT * FROM tasks WHERE id::text LIKE %s ORDER BY created_at DESC LIMIT 1",
    ("<task_id_prefix>%",)
)
row = cur.fetchone()
```

Display the full `output` or `error` field along with status, prompt, and timing.

## Cancelling and Cleaning Up

Cancel a running task (kills its tmux window and marks it failed in the DB):
```bash
swarm-cancel <task_id>
```

Close all tmux windows for tasks that have already completed or failed:
```bash
swarm-clean
```

`swarm-clean` cross-references the DB with open tmux windows and kills only the matching ones, leaving any still-running windows untouched.
