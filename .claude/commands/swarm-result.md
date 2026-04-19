# Show result of a swarm task

Fetches and displays the full output of a completed task.

## Usage
```
/swarm-result <task_id_or_prefix>
```

## What to do

Run:
```python
from claude_swarm import db
from claude_swarm.config import PG_DSN
import psycopg2
conn = psycopg2.connect(PG_DSN); conn.autocommit = True
cur = conn.cursor()
cur.execute("SELECT * FROM tasks WHERE id::text LIKE %s ORDER BY created_at DESC LIMIT 1", (f"$argument%",))
```

Replace `$argument` with the task ID prefix provided. Display the full `output` or `error` field, along with status, prompt, and timing.
