#!/usr/bin/env python3
"""Pre-flight check: validates swarm dependencies and configuration."""
import sys
import subprocess
import shutil


def _check(label, ok, detail=""):
    mark = "✓" if ok else "✗"
    color = "\033[32m" if ok else "\033[31m"
    reset = "\033[0m"
    suffix = f"  {detail}" if detail else ""
    print(f"  {color}{mark}{reset}  {label}{suffix}")
    return ok


def run():
    print("[swarm] doctor — pre-flight check\n")
    passed = 0
    failed = 0

    # 1. SWARM_PG_DSN
    import os
    dsn = os.environ.get("SWARM_PG_DSN", "")
    ok = bool(dsn)
    _check("SWARM_PG_DSN set", ok, dsn[:40] + "…" if len(dsn) > 40 else dsn)
    passed += ok; failed += not ok

    # 2. PostgreSQL connectivity
    try:
        import psycopg2
        from .config import PG_DSN
        conn = psycopg2.connect(PG_DSN)
        ver = conn.server_version
        conn.close()
        ok = True
        detail = f"server version {ver}"
    except Exception as e:
        ok = False
        detail = str(e)[:80]
    _check("PostgreSQL reachable", ok, detail)
    passed += ok; failed += not ok

    # 3. tasks table exists
    if ok:
        try:
            conn = psycopg2.connect(PG_DSN)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM tasks")
            count = cur.fetchone()[0]
            conn.close()
            _check("tasks table exists", True, f"{count} rows")
            passed += 1
        except Exception as e:
            _check("tasks table exists", False, str(e)[:80])
            failed += 1

    # 4. tmux available
    ok = shutil.which("tmux") is not None
    _check("tmux in PATH", ok)
    passed += ok; failed += not ok

    # 5. tmux swarm session
    from .config import TMUX_SESSION
    result = subprocess.run(["tmux", "has-session", "-t", TMUX_SESSION], capture_output=True)
    ok = result.returncode == 0
    _check(f"tmux session '{TMUX_SESSION}' running", ok,
           "" if ok else "run 'tmux new-session -d -s swarm' or spawn a task first")
    passed += ok; failed += not ok

    # 6. claude CLI
    ok = shutil.which("claude") is not None
    _check("claude CLI in PATH", ok, "" if ok else "install Claude Code: https://claude.ai/code")
    passed += ok; failed += not ok

    # 7. ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN / OPENROUTER_API_KEY
    has_key = bool(
        os.environ.get("ANTHROPIC_API_KEY") or
        os.environ.get("ANTHROPIC_AUTH_TOKEN") or
        os.environ.get("OPENROUTER_API_KEY")
    )
    _check("API key set (ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN / OPENROUTER_API_KEY)", has_key,
           "" if has_key else "child agents won't authenticate")
    passed += has_key; failed += not has_key

    # 8. rich installed
    try:
        import rich
        ver = getattr(rich, "__version__", None) or getattr(rich, "version", {}).get("VERSION", "?")
        _check("rich installed (enhanced UX)", True, f"v{ver}")
        passed += 1
    except ImportError:
        _check("rich installed (enhanced UX)", False, "pip install rich")
        failed += 1

    print(f"\n  {passed} passed  {failed} failed")
    if failed:
        sys.exit(1)


def main():
    run()


if __name__ == "__main__":
    main()
