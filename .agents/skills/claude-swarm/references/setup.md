# Claude Swarm Setup

Run these steps once before using any swarm commands. You can re-run safely — all steps are idempotent.

## 1. Get PostgreSQL connection details

Ask the user for their PostgreSQL connection string. They can provide it as:

- A full libpq DSN: `host=db.example.com port=5432 dbname=swarm user=swarm password=secret`
- A URL: `postgresql://swarm:secret@db.example.com:5432/swarm`

If they need a local Postgres for testing, suggest: `host=localhost port=5432 dbname=swarm user=swarm password=swarm`

## 2. Install the Python package

From the project root, install the swarm package and its CLI commands:

```bash
pip install -e .
```

This puts `swarm-spawn`, `swarm-wait`, and `swarm-expert` on `$PATH`.

## 3. Save the connection to project settings

Run this Python snippet (replace `<dsn>` with the user's connection string):

```python
import json, pathlib

dsn = "<dsn>"
settings_path = pathlib.Path(".claude/settings.json")
settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
settings.setdefault("env", {})["SWARM_PG_DSN"] = dsn
settings_path.parent.mkdir(exist_ok=True)
settings_path.write_text(json.dumps(settings, indent=2))
print(f"Saved SWARM_PG_DSN to .claude/settings.json")
```

This persists the DSN across Claude Code sessions via the project's environment config.

Optional — customize the tmux session name (default is `swarm`):
```python
settings["env"]["SWARM_TMUX_SESSION"] = "my-swarm"
settings_path.write_text(json.dumps(settings, indent=2))
```

## 4. Verify connection and initialize schema

```bash
python3 -c "
from claude_swarm import db
db.connect().close()
db.init_schema()
print('OK: connected and tasks table ready')
"
```

If this fails:
- Check that the Postgres server is running and reachable
- Make sure `SWARM_PG_DSN` is set in the current shell (restart Claude Code after saving settings)
- Verify the database and user exist with CONNECT privilege

## 5. Confirm to the user

Setup is complete. They can now use:
- `swarm-spawn "<prompt>"` — run any task in a child Claude instance
- `swarm-expert researcher "<topic>"` — spawn a researcher agent
- `/claude-swarm` — access all swarm commands via the skill
