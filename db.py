import psycopg2
import psycopg2.extras
from config import PG_DSN

def connect():
    conn = psycopg2.connect(PG_DSN)
    conn.autocommit = True
    return conn

def init_schema():
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            parent_id   UUID REFERENCES tasks(id),
            prompt      TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'pending',
            output      TEXT,
            error       TEXT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            started_at  TIMESTAMPTZ,
            completed_at TIMESTAMPTZ
        )
    """)
    cur.close()
    conn.close()

def create_task(prompt: str, parent_id: str = None) -> str:
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tasks (prompt, parent_id) VALUES (%s, %s) RETURNING id",
        (prompt, parent_id)
    )
    task_id = str(cur.fetchone()[0])
    cur.close()
    conn.close()
    return task_id

def set_running(task_id: str):
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "UPDATE tasks SET status='running', started_at=now() WHERE id=%s",
        (task_id,)
    )
    cur.close()
    conn.close()

def set_done(task_id: str, output: str):
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "UPDATE tasks SET status='done', output=%s, completed_at=now() WHERE id=%s",
        (output, task_id)
    )
    cur.execute("SELECT pg_notify('task_complete', %s)", (task_id,))
    cur.close()
    conn.close()

def set_failed(task_id: str, error: str):
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "UPDATE tasks SET status='failed', error=%s, completed_at=now() WHERE id=%s",
        (error, task_id)
    )
    cur.execute("SELECT pg_notify('task_complete', %s)", (task_id,))
    cur.close()
    conn.close()

def get_task(task_id: str) -> dict:
    conn = connect()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM tasks WHERE id=%s", (task_id,))
    row = dict(cur.fetchone())
    cur.close()
    conn.close()
    return row

def list_tasks(limit: int = 20) -> list:
    conn = connect()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT %s", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows
