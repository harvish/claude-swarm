# Spawn a child Claude Code task

Spawns a new non-interactive Claude Code instance in a tmux window. Output is saved to PostgreSQL and retrieved via LISTEN/NOTIFY.

## Usage
```
/spawn <prompt>
/spawn expert:<type> <task>    (researcher | analyst | coder)
```

## What to do

**Plain spawn:**
```bash
swarm-spawn "<prompt>"
```

**Expert spawn:**
```bash
swarm-expert <type> "<task>"
```

Capture the printed UUID, then wait:
```bash
swarm-wait <task_id> [<task_id2> ...]
```

Tell the user the task ID(s) and that windows are visible in `tmux attach -t swarm`.

## When to auto-spawn (do this without being asked)

| Situation | Action |
|-----------|--------|
| Need current/live information | Spawn `researcher` |
| User asks about docs, versions, prices, recent news | Spawn `researcher` |
| Multiple independent sub-questions | Spawn parallel researchers |
| Large analysis task | Spawn `analyst` |
| Need working code for a sub-problem | Spawn `coder` |

**Default behavior:** when you would normally do a WebSearch or WebFetch inline, spawn a researcher instead and wait for its output. This keeps the parent session focused on synthesis while children handle data gathering.

## Passing context
- `--workdir <path>` — child works in that directory
- `--parent-id <uuid>` — links child to a parent task in the DB
