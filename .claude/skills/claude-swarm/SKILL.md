---
name: claude-swarm
description: Orchestrate parallel Claude Code agents for research, coding, and analysis. Use whenever tasks benefit from parallelism — multiple research topics, large codebases requiring simultaneous analysis, or any workflow where spawning specialized child agents (researcher, analyst, coder) would be faster than sequential work. Triggers on phrases like "research X and Y in parallel", "spawn agents for", "swarm", or any multi-track investigation where independent subtasks exist.
---

# Claude Swarm

Orchestrates child Claude Code instances via PostgreSQL + tmux. The parent agent spawns children, waits for their results via LISTEN/NOTIFY, and synthesizes the findings.

## First Run: Onboarding

Before using any swarm command, verify setup is complete:

```bash
swarm-doctor
```

If `swarm-doctor` is not found or any check fails, run the onboarding flow in `references/setup.md` — it walks through installing dependencies, creating the bash wrappers, persisting the DSN, and initializing the schema. Do this automatically without asking the user.

## Spawning Tasks

**Generic task** — any prompt, unrestricted tools:
```bash
swarm-spawn "<prompt>"
```

**Expert task** — wraps prompt in a role-specific system prompt with restricted tools:
```bash
swarm-expert researcher   "<topic>"    # WebSearch + WebFetch
swarm-expert analyst      "<subject>"  # WebSearch + WebFetch
swarm-expert coder        "<task>"     # WebFetch + Read + Write + Bash
swarm-expert synthesizer  "<task>"     # no tools — synthesizes provided context
```

Each spawn prints a UUID. Pass one or more to `swarm-wait`:
```bash
swarm-wait <id1> [<id2> <id3> ...]
swarm-wait <id1> <id2> --timeout 900   # override timeout (default: 600s)
swarm-wait <id1> <id2> --json          # structured JSON output for scripting
```

`swarm-wait` shows a **live Rich table** — per-task rows with spinner, status, elapsed time, and last log line — then prints a summary line (`N/M done  ~X,XXX words`) followed by color-coded result panels (green=done, red=failed). For expert tasks the table and panels show the **task topic** (e.g. "AAPL 2025 analyst outlook") rather than the system prompt.

### Passing context
- `swarm-spawn "<prompt>" --workdir <path>` — child works in that directory
- `swarm-spawn "<prompt>" --parent-id <uuid>` — links child to parent for lineage tracking

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

**Snapshot** (one-shot, TTY-safe, pipe-friendly):
```bash
swarm-status              # rich table if TTY, plain text otherwise
swarm-status --json       # JSON output for piping/scripting
swarm-status -n 50        # show last 50 tasks
```

**Live dashboard** (auto-refreshes until Ctrl-C):
```bash
swarm-status --live
```

## Watching Task Output Live

Stream a running task's output in real time:
```bash
swarm-logs <task_id>
```

Waits up to 5s for the task to start, then tails line-by-line (inotify on Linux, poll fallback). Or watch all windows at once:
```bash
tmux attach -t swarm
```

## Pre-flight Check

```bash
swarm-doctor
```

Checks: SWARM_PG_DSN set, postgres reachable, tasks table exists, tmux available, swarm session running, claude CLI in PATH, API key set, rich installed.

## Synthesizing Results

After parallel researchers complete, `swarm-wait` prints a ready-to-run hint:
```
Synthesize:  swarm-synthesize <id1> <id2> <id3>
```

Run it to auto-fetch all stored outputs and spawn a synthesizer:
```bash
swarm-synthesize <id1> <id2> <id3>                   # auto-topic from task labels
swarm-synthesize <id1> <id2> -q "Which is riskier?"  # guiding question
```

Prints a new task ID; pipe to `swarm-wait` to see the result:
```bash
swarm-wait $(swarm-synthesize <id1> <id2> <id3>)
```

## Retrying Failed Tasks

Re-spawn a failed or timed-out task with the same prompt (no copy-paste needed):
```bash
swarm-retry <task_id>
```

Prints the new task ID. Detects the original expert type from the prompt so
`swarm-retry` preserves researcher/analyst/coder/synthesizer semantics. Only
works on tasks with status `failed` or `timeout`.

## Cancelling and Cleaning Up

```bash
swarm-cancel <task_id>     # kill tmux window + mark failed in DB
swarm-clean                # close tmux windows for finished tasks
swarm-clean --logs         # also purge preserved log files
```
