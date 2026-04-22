"""Shared utilities used across swarm scripts."""

TASK_TIMEOUT_S = 600  # seconds before worker kills a stuck task

STATUS_STYLE = {
    "pending": ("yellow", "⏳"),
    "running": ("cyan",   "⚙ "),
    "done":    ("green",  "✓ "),
    "failed":  ("red",    "✗ "),
    "timeout": ("red",    "✗ "),
    "zombie":  ("red",    "💀"),
}


def task_label(prompt: str, max_len: int = 65) -> str:
    """Short display label from a prompt.

    Expert prompts contain 'Task: <topic>' on one line; extract just the topic.
    Scans all lines so synthesizer prompts (Task: near the top) work correctly.
    """
    lines = [l.strip() for l in (prompt or "").splitlines() if l.strip()]
    if not lines:
        return ""
    for line in lines:
        if line.startswith("Task: "):
            return line[6:][:max_len]
    candidate = lines[-1] if len(lines[-1]) <= max_len else lines[0]
    return candidate[:max_len]


def style(status: str) -> tuple[str, str]:
    return STATUS_STYLE.get(status, ("white", "? "))
