# claude-skills

A collection of agent skills for Claude Code, installable via [skills.sh](https://skills.sh).

## Skills

### claude-swarm

Orchestrate parallel Claude Code agents for research, coding, and analysis. Spawns specialized workers (researcher, analyst, coder) that run concurrently and report back to the parent session.

```bash
npx skills add harvish/claude-swarm
```

[Details](.agents/skills/claude-swarm/README.md)

---

## Usage

Skills are picked up automatically by Claude Code after installation. Each skill can also be invoked explicitly via its slash command (e.g. `/claude-swarm`).

## Contributing

There are a few ways to contribute:

- **Add a new skill** — create `.agents/skills/<skill-name>/` with a `SKILL.md` and `README.md`, then list it above
- **Add expert configurations** — extend an existing skill with new expert roles under its `scripts/` directory
- **Customize a skill** — fork and adapt any skill's `SKILL.md` or supporting scripts to fit your workflow

Open a pull request with your changes.
