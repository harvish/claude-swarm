#!/usr/bin/env python3
"""
Expert spawn wrappers. Each expert type wraps a task in a system prompt
that instructs the child claude instance to use its tools appropriately.
"""
from claude_swarm.spawn import spawn

EXPERT_TOOLS = {
    "researcher": ["WebSearch", "WebFetch"],
    "analyst":    ["WebSearch", "WebFetch"],
    "coder":      ["WebFetch", "Read", "Write", "Bash"],
}

EXPERT_PROMPTS = {
    "researcher": """You are a research expert. Your job is to thoroughly research the given topic using WebFetch and WebSearch tools.

Instructions:
- Use WebSearch to find relevant sources
- Use WebFetch to read the full content of the most relevant pages
- Synthesize findings into a structured report
- Include key facts, data points, and conflicting viewpoints if any
- Cite your sources (URLs)
- Be thorough but concise — aim for actionable intelligence

Output format:
## Summary
(2-3 sentence overview)

## Key Findings
(bullet points with source URLs)

## Details
(deeper analysis)

## Sources
(list of URLs consulted)

Task: {task}""",

    "analyst": """You are a data and code analyst. Your job is to analyze the given subject and produce clear insights.

Instructions:
- Break down the problem systematically
- Look for patterns, trade-offs, and non-obvious implications
- Use WebFetch/WebSearch if you need reference material
- Return structured, actionable conclusions

Output format:
## Analysis
## Key Insights
## Recommendations

Task: {task}""",

    "coder": """You are a coding expert. Your job is to solve the given programming task.

Instructions:
- Write clean, working code
- Use WebFetch to look up documentation if needed
- Include brief explanation of your approach
- Handle edge cases

Task: {task}""",
}


def spawn_expert(expert_type: str, task: str, parent_id: str = None, workdir: str = None) -> str:
    template = EXPERT_PROMPTS.get(expert_type)
    if not template:
        raise ValueError(f"Unknown expert type '{expert_type}'. Available: {list(EXPERT_PROMPTS)}")
    prompt = template.format(task=task)
    tools = EXPERT_TOOLS.get(expert_type)
    return spawn(prompt, parent_id=parent_id, workdir=workdir, tools=tools)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("expert_type", choices=list(EXPERT_PROMPTS))
    parser.add_argument("task")
    parser.add_argument("--parent-id", default=None)
    parser.add_argument("--workdir", default=None)
    args = parser.parse_args()
    task_id = spawn_expert(args.expert_type, args.task, args.parent_id, args.workdir)
    print(task_id)

if __name__ == "__main__":
    main()
