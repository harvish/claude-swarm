# Researcher expert

Spawns one or more child Claude instances that use WebSearch and WebFetch to research topics in parallel, then synthesizes their findings.

## Usage
```
/researcher <topic or question>
/researcher <topic1> | <topic2> | <topic3>   (parallel)
```

## What to do

**Single topic:**
1. Run: `swarm-expert researcher "<topic>"`
2. Capture the printed task UUID
3. Run: `swarm-wait <task_id>`
4. Present the researcher's findings to the user

**Multiple topics (parallel):**
1. For each topic, run `swarm-expert researcher "<topic>"` — capture all task UUIDs
2. Run: `swarm-wait <id1> <id2> <id3>` (waits for all via LISTEN/NOTIFY)
3. Synthesize all findings into a combined answer

## When to auto-invoke

Spawn a researcher automatically (without the user asking) when:
- Answering requires current information beyond your training data
- The user asks about a specific product, library version, price, or recent event
- Multiple independent sub-questions could be researched in parallel
- You need to verify a fact before acting on it

Always prefer spawning parallel researchers over sequential ones when topics are independent.
