# claude-swarm

An agent swarm skill for Claude Code, built entirely on the default skills spec supported by Claude — no external infrastructure, no platform-specific tools.

> **Scope**: Currently targets Claude Code. Future plan is to expand to all clients that support the skills spec.

## What it does

The `claude-swarm` skill lets Claude orchestrate parallel child agents from within a single session. Instead of working sequentially, Claude spawns specialized workers (researcher, analyst, coder) to run concurrently, then synthesizes their results.

## Install

```bash
npx skills add harvish/claude-swarm
```

## Usage

Once installed, Claude picks up the skill automatically. You can also invoke it explicitly:

```
/claude-swarm
```

Trigger phrases that cause Claude to auto-activate swarm mode:

- "research X and Y in parallel"
- "spawn agents for …"
- any multi-track task with independent subtasks

## Skill structure

```
.claude/skills/claude-swarm/
├── SKILL.md              # skill definition (loaded by Claude Code)
├── scripts/              # CLI helpers: swarm-spawn, swarm-wait, swarm-expert
└── references/setup.md   # first-run onboarding guide
```
