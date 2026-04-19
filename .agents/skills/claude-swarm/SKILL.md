---
name: claude-swarm
description: Orchestrate parallel Claude Code agents for research, coding, and analysis. Use whenever tasks benefit from parallelism — multiple research topics, large codebases requiring simultaneous analysis, or any workflow where spawning specialized child agents (researcher, analyst, coder) would be faster than sequential work. Triggers on phrases like "research X and Y in parallel", "spawn agents for", "swarm", or any multi-track investigation where independent subtasks exist.
---

# Claude Swarm

Orchestrates child Claude Code instances via PostgreSQL + tmux. The parent agent spawns children, waits for their results via LISTEN/NOTIFY, and synthesizes the findings.

## First Run: Onboarding

Before using swarm commands, verify setup by checking for `SWARM_PG_DSN` in the environment. If it's missing, run the onboarding flow in `references/setup.md` — it asks for the user's PostgreSQL connection details, saves the config, installs dependencies, and initializes the schema. Do this automatically without asking the user if any swarm command fails with a connection error.

## Spawning Tasks

**Generic task** — any prompt, unrestricted tools:
```bash
swarm-spawn "<prompt>"
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

`swarm-wait` blocks until all given tasks complete (or 300s timeout), then prints each result.

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

## Tasks visible in tmux

Child Claude instances run in tmux windows. To watch them live:
```bash
tmux attach -t swarm   # or $SWARM_TMUX_SESSION if customized
```
