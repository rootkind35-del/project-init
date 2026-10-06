#!/usr/bin/env python3
"""
inject_memory.py — PreInvocation hook for Antigravity project-init skill.

Reads PROJECT_MEMORY.md from the workspace root and injects it as an
ephemeral system message before every AI invocation.

Contract:
  stdin  -> JSON with workspacePaths, conversationId, invocationNum, etc.
  stdout -> JSON { "injectSteps": [ { "ephemeralMessage": "..." } ] }

If PROJECT_MEMORY.md is missing or empty, outputs {} (no injection).
"""

import sys
import json
from pathlib import Path


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        sys.stdout.write("{}")
        return

    workspace_paths = payload.get("workspacePaths", [])
    if not workspace_paths:
        sys.stdout.write("{}")
        return

    workspace_root = Path(workspace_paths[0])
    memory_file = workspace_root / "PROJECT_MEMORY.md"

    if not memory_file.exists():
        sys.stdout.write("{}")
        return

    try:
        content = memory_file.read_text(encoding="utf-8").strip()
    except OSError:
        sys.stdout.write("{}")
        return

    if not content:
        sys.stdout.write("{}")
        return

    # Only inject once per session (invocationNum == 1) or always?
    # We inject on every invocation so the AI never loses project context.
    invocation_num = payload.get("invocationNum", 0)

    # Build a concise preamble so the AI knows what this is
    message = (
        "=== PROJECT MEMORY (auto-injected by project-init) ===\n"
        "Read and internalize the following project context before responding.\n\n"
        + content
        + "\n\n=== END PROJECT MEMORY ==="
    )

    result = {
        "injectSteps": [
            {"ephemeralMessage": message}
        ]
    }

    sys.stdout.write(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
