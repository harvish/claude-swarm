# Show swarm task status

Displays recent tasks from the swarm PostgreSQL database.

## What to do

Run the following Python snippet and display the results in a readable table:

```python
import sys; sys.path.insert(0, '/root/docs/swarm')
import db
tasks = db.list_tasks(20)
for t in tasks:
    short = str(t['id'])[:8]
    parent = str(t['parent_id'])[:8] if t['parent_id'] else '-'
    elapsed = ''
    if t['completed_at'] and t['started_at']:
        elapsed = f"{(t['completed_at'] - t['started_at']).seconds}s"
    print(f"{short}  parent={parent}  status={t['status']:<8}  {elapsed:>5}  {t['prompt'][:60]}")
```

Show statuses with color context: pending=waiting, running=in-progress, done=success, failed=error.
