# Claude Swarm — Onboarding

Run once before using any swarm commands. All steps are idempotent — safe to re-run.

---

## Step 1 — Get PostgreSQL connection details

Ask the user for their PostgreSQL DSN. Accept either format:

- libpq: `host=db.example.com port=5432 dbname=swarm user=swarm password=secret`
- URL: `postgresql://user:password@host:5432/dbname`

**No Postgres yet?** Suggest the default for a local instance:
```
host=localhost port=5432 dbname=swarm user=swarm password=swarm
```

Store it as `DSN` for the steps below.

---

## Step 2 — Install Python dependencies

```bash
pip install psycopg2-binary rich inotify_simple -q
```

No package install needed — swarm commands run directly from the skill scripts.

---

## Step 3 — Symlink bin/ wrappers into PATH

The `bin/` directory in the skill is version-controlled and contains
self-locating wrappers (they resolve their own path via `readlink -f`,
so symlinks work correctly from any location).

Run from the project root (where `.agents/` lives):

```bash
SWARM_ROOT="$(pwd)"
BIN_DIR="$SWARM_ROOT/.claude/skills/claude-swarm/bin"

mkdir -p ~/.local/bin

for f in "$BIN_DIR"/swarm-*; do
  ln -sf "$f" ~/.local/bin/"$(basename "$f")"
done

echo "Linked: $(ls ~/.local/bin/swarm-* | xargs -n1 basename | tr '\n' ' ')"
```

---

## Step 4 — Persist DSN and PATH in shell profile

```bash
grep -q 'SWARM_PG_DSN' ~/.bashrc || cat >> ~/.bashrc << EOF

# Claude Swarm
export SWARM_PG_DSN="$DSN"
EOF

grep -q '\.local/bin' ~/.bashrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

# Apply to current session
export PATH="$HOME/.local/bin:$PATH"
export SWARM_PG_DSN="$DSN"
```

---

## Step 5 — Initialize the database schema

```bash
python3 -c "
import sys; sys.path.insert(0, '$SCRIPTS_PARENT')
from scripts import db
db.init_schema()
print('OK: schema ready')
"
```

---

## Step 6 — Save DSN to project settings

Persists `SWARM_PG_DSN` so Claude Code sessions load it automatically on startup:

```bash
python3 - << 'EOF'
import json, pathlib, os
p = pathlib.Path(".claude/settings.json")
s = json.loads(p.read_text()) if p.exists() else {}
s.setdefault("env", {})["SWARM_PG_DSN"] = os.environ["SWARM_PG_DSN"]
p.parent.mkdir(exist_ok=True)
p.write_text(json.dumps(s, indent=2))
print("Saved to .claude/settings.json")
EOF
```

---

## Step 7 — Verify with doctor

```bash
swarm-doctor
```

All 8 checks should pass. Common fixes:

| Failing check | Fix |
|---|---|
| `SWARM_PG_DSN not set` | Re-run Step 4, then open a new shell |
| `PostgreSQL unreachable` | Check host/port/firewall; verify DB server is running |
| `tasks table missing` | Re-run Step 5 |
| `tmux not found` | `apt install tmux` or `brew install tmux` |
| `claude CLI not found` | Install Claude Code: https://claude.ai/code |
| `API key missing` | Set `ANTHROPIC_API_KEY` in your shell |
| `rich not installed` | `pip install rich` |

---

## Done — Available commands

| Command | What it does |
|---------|-------------|
| `swarm-spawn "<prompt>"` | Run any task in a child Claude instance |
| `swarm-expert researcher "<topic>"` | Researcher agent (WebSearch + WebFetch) |
| `swarm-expert analyst "<subject>"` | Analyst agent (WebSearch + WebFetch) |
| `swarm-expert coder "<task>"` | Coder agent (Read + Write + Bash) |
| `swarm-wait <id> [<id2> ...]` | Wait for tasks — live table + color-coded results |
| `swarm-status` | Snapshot of recent tasks |
| `swarm-status --live` | Auto-refreshing live dashboard |
| `swarm-logs <id>` | Stream live output from a running task |
| `swarm-cancel <id>` | Cancel a running task |
| `swarm-synthesize <id> [<id2> ...]` | Spawn synthesizer over stored outputs of completed tasks |
| `swarm-retry <id>` | Re-spawn a failed/timed-out task with the same prompt |
| `swarm-clean` | Close tmux windows for finished tasks |
| `swarm-clean --logs` | Also purge preserved log files |
| `swarm-doctor` | Pre-flight check for all dependencies |
