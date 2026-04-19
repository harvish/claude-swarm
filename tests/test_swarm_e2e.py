#!/usr/bin/env python3
"""
Skill e2e tests — require Claude Code CLI, Postgres, and ANTHROPIC_API_KEY.
Run: python3 tests/test_swarm_e2e.py
"""
import os
import sys
import subprocess

from claude_swarm import db

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"


def check(name, condition, detail=""):
    if condition:
        print(f"  {PASS}  {name}")
    else:
        print(f"  {FAIL}  {name}" + (f": {detail}" if detail else ""))
    return condition


def run_claude(prompt: str, timeout: int = 180) -> str:
    model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
    result = subprocess.run(
        ["claude", "-p", prompt, "--allowedTools", "Bash", "--model", model, "--no-color"],
        capture_output=True, text=True, timeout=timeout,
    )
    return result.stdout + result.stderr


# ──────────────────────────────────────────────────────────────────────────────

def test_smoke():
    """Ask Claude to spawn a single task and verify it completes via the swarm."""
    print("\n[1] Smoke — spawn and wait via swarm skill")

    before = len(db.list_tasks(100))
    output = run_claude(
        "Use the swarm to spawn a task that replies with exactly: SMOKE_OK. "
        "Wait for the result and report the output."
    )
    after = len(db.list_tasks(100))

    ok = True
    ok &= check("swarm tasks created in DB", after > before, f"before={before} after={after}")
    ok &= check("output contains SMOKE_OK", "SMOKE_OK" in output, repr(output[:300]))
    return ok


def test_faang_research():
    """
    Ask Claude to research FAANG stock price projections using parallel researcher
    agents. Verifies that tasks are dispatched through the swarm and that the
    synthesised output covers the expected companies.
    """
    print("\n[2] FAANG research — parallel researcher swarm")

    before = len(db.list_tasks(200))

    output = run_claude(
        "Use the claude-swarm researcher skill to fetch 2025 stock price projections "
        "for each FAANG company (Apple / AAPL, Google / Alphabet / GOOGL, "
        "Meta / META, Amazon / AMZN, Netflix / NFLX). "
        "Spawn one researcher agent per company in parallel, wait for all results, "
        "then give me a concise summary with each company's analyst outlook.",
        timeout=360,
    )

    after_tasks = db.list_tasks(200)
    spawned = len(after_tasks) - before

    ok = True
    ok &= check("swarm tasks were spawned", spawned >= 1, f"spawned={spawned}")

    # At least researcher tasks should have run
    recent = after_tasks[:spawned] if spawned > 0 else []
    done   = [t for t in recent if t["status"] == "done"]
    failed = [t for t in recent if t["status"] == "failed"]
    ok &= check(f"tasks completed ({len(done)}/{spawned})", len(done) >= 1)
    ok &= check("no tasks failed", len(failed) == 0,
                f"failed={[str(t['id'])[:8] for t in failed]}")

    # Output should mention at least 3 of the 5 companies
    tickers = ["apple", "aapl", "google", "alphabet", "googl",
               "meta", "amazon", "amzn", "netflix", "nflx"]
    hits = [t for t in tickers if t in output.lower()]
    ok &= check("FAANG companies in output", len(hits) >= 3,
                f"matched={hits}")

    return ok


# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("Claude Swarm — Skill E2E Tests")
    print("=" * 55)

    db.init_schema()

    tests = [test_smoke, test_faang_research]
    passed = 0
    for t in tests:
        try:
            if t():
                passed += 1
        except Exception as e:
            print(f"  {FAIL}  unhandled exception: {e}")

    total = len(tests)
    print(f"\n{'=' * 55}")
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 55)
    sys.exit(0 if passed == total else 1)
