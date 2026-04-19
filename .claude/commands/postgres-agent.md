# Configure PostgreSQL for claude-swarm

Sets up and verifies the PostgreSQL connection for the swarm system. Run this once before using any other swarm commands.

## Usage
```
/postgres-agent
/postgres-agent <connection-string>
```

## What to do

Walk the user through these steps in order. Stop and report clearly if any step fails.

### 1. Check for existing configuration

Run this to see if env vars are already set:
```bash
python3 -c "
import os
dsn = os.environ.get('SWARM_PG_DSN')
host = os.environ.get('SWARM_PG_HOST')
if dsn:
    print('SWARM_PG_DSN is set')
elif host:
    print(f'Individual vars set: SWARM_PG_HOST={host}')
else:
    print('No SWARM_PG_* variables found — configuration needed')
"
```

### 2. Set env vars if not already configured

If the user has not set env vars yet, ask them for their PostgreSQL connection details (host, port, database name, user, password) or a full DSN string.

Guide them to export one of these options in their current shell and add it to their shell profile (`~/.bashrc`, `~/.zshrc`, or a `.env` file that is sourced at startup):

**Option A — full DSN (recommended):**
```bash
export SWARM_PG_DSN="host=<host> port=5432 dbname=swarm user=swarm password=<password>"
```

**Option B — individual vars:**
```bash
export SWARM_PG_HOST=<host>
export SWARM_PG_PORT=5432
export SWARM_PG_DB=swarm
export SWARM_PG_USER=swarm
export SWARM_PG_PASSWORD=<password>
```

Optionally, to use a custom tmux session name instead of "swarm":
```bash
export SWARM_TMUX_SESSION=my-swarm
```

After they confirm the vars are exported in the current shell, proceed to step 3.

### 3. Verify the connection

```bash
python3 -c "
from claude_swarm import db
try:
    conn = db.connect()
    conn.close()
    print('OK: connected to PostgreSQL')
except Exception as e:
    print(f'FAILED: {e}')
"
```

If this fails:
- Check that the PostgreSQL server is running and reachable from this machine
- Verify the env vars are exported in the current shell (not just written to the profile)
- Check firewall rules if the server is remote
- Confirm the database and user exist and the user has CONNECT privilege

### 4. Initialize the schema

```bash
python3 -c "
from claude_swarm import db
db.init_schema()
print('OK: tasks table ready')
"
```

This is idempotent — safe to run multiple times.

### 5. Confirm everything is working

```bash
python3 -c "
from claude_swarm import db
task_id = db.create_task('setup verification')
db.set_done(task_id, 'verified')
task = db.get_task(task_id)
print(f'OK: round-trip verified — task {task_id[:8]} status={task[\"status\"]}')
"
```

### 6. Report success to the user

Tell the user:
- Their Postgres connection is working
- The schema is initialized
- They can now use `/spawn`, `/researcher`, and `/swarm-status`
- Task windows are visible in `tmux attach -t swarm` (or their custom `SWARM_TMUX_SESSION`)

## When to auto-invoke

Invoke this skill automatically when:
- The user runs any swarm command and gets a connection error or "password authentication failed"
- The user says they are setting up the swarm for the first time
- Any swarm command fails with a psycopg2 `OperationalError`
