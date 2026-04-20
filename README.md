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

1. Fork the repo
2. Add your skill under `.agents/skills/<skill-name>/` with a `SKILL.md` and `README.md`
3. List it in this file under **Skills**
4. Open a pull request
