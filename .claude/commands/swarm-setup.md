# Set up claude-swarm

Onboarding skill. Run once to connect the swarm to your PostgreSQL instance and initialize the task schema. After this, all other swarm skills (/spawn, /researcher, /swarm-status, /swarm-result) will work.

## Usage
```
/swarm-setup <postgres-dsn>
```

Where `<postgres-dsn>` is a libpq connection string, e.g.:
```
/swarm-setup host=db.example.com port=5432 dbname=swarm user=swarm password=secret
```

## $ARGUMENTS

The PostgreSQL DSN to use. If not provided, ask the user for:
- Host (default: localhost)
- Port (default: 5432)
- Database name (default: swarm)
- Username
- Password

Then assemble it as `host=<host> port=<port> dbname=<db> user=<user> password=<pass>`.

## What to do

### 1. Save the connection to project settings

```python
import json, pathlib

dsn = "$ARGUMENTS"
settings_path = pathlib.Path(".claude/settings.json")
settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
settings.setdefault("env", {})["SWARM_PG_DSN"] = dsn
settings_path.parent.mkdir(exist_ok=True)
settings_path.write_text(json.dumps(settings, indent=2))
print(f"Saved SWARM_PG_DSN to .claude/settings.json")
```

### 2. Verify and initialize schema

```bash
SWARM_PG_DSN="$ARGUMENTS" python3 -c "
from claude_swarm import db
db.connect().close()
db.init_schema()
print('OK: connected and tasks table ready')
"
```

### 3. Confirm

Tell the user setup is complete. They can now use:
- `/spawn <prompt>` — run a task in a child Claude instance
- `/researcher <topic>` — research a topic in parallel
- `/swarm-status` — view recent tasks
- `/swarm-result <id>` — fetch task output
