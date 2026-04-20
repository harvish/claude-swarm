import os
import pathlib
import tempfile

_dsn = os.environ.get("SWARM_PG_DSN")
if not _dsn:
    _host = os.environ.get("SWARM_PG_HOST", "localhost")
    _port = os.environ.get("SWARM_PG_PORT", "5432")
    _db   = os.environ.get("SWARM_PG_DB",   "swarm")
    _user = os.environ.get("SWARM_PG_USER",  "swarm")
    _pass = os.environ.get("SWARM_PG_PASSWORD", "")
    _dsn  = f"host={_host} port={_port} dbname={_db} user={_user} password={_pass}"

PG_DSN = _dsn
TMUX_SESSION = os.environ.get("SWARM_TMUX_SESSION", "swarm")

_LOG_DIR = pathlib.Path(tempfile.gettempdir())

def log_path(task_id: str) -> pathlib.Path:
    return _LOG_DIR / f"swarm-{task_id}.log"
