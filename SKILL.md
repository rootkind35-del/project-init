---
name: project-init
description: >-
  Scans the entire project workspace and generates a PROJECT_MEMORY.md file
  containing structure, key files, tech stack, conventions, and entry points.
  Use this skill when the user runs /init, asks to "init project", "index
  project", "scan project", "memorize project", or wants the AI to understand
  the codebase before starting work. After init completes, every subsequent AI
  action in the session reads PROJECT_MEMORY.md first as persistent context.
---

# Project Init — Workspace Memory Builder

This skill replicates the `init` workflow from Codex/Claude Code: scan the
full project once, write a structured memory file, then automatically inject
that memory into every future AI invocation in the session.

---

## When to Activate

Activate when the user says any of:
- `/init`
- "init project", "khởi tạo project", "scan project", "index project"
- "đọc toàn bộ project", "ghi nhớ project", "analyze codebase"
- "tạo bộ nhớ project", "memorize codebase"

---

## Step-by-Step Workflow

### Step 1 — Determine the workspace root

Check `workspacePaths` from context or ask the user if no workspace is active.
The root is the directory that contains `.git`, `package.json`, `pyproject.toml`,
`go.mod`, `Cargo.toml`, or similar project markers.

### Step 2 — Run the scanner script

Execute the Python scanner to collect project intelligence:

```powershell
python "C:\Users\dhp01\.gemini\config\skills\project-init\scripts\scan_project.py" <workspace_root>
```

The script outputs a JSON summary to stdout. Capture it.

If Python is not available, fall back to the manual scan procedure in
[references/manual_scan.md](./references/manual_scan.md).

### Step 3 — Generate PROJECT_MEMORY.md

Write `<workspace_root>/PROJECT_MEMORY.md` using the JSON output from Step 2.
Use the template in [references/memory_template.md](./references/memory_template.md).

The file must contain these sections:
1. **Project Identity** — name, type, language/stack
2. **Directory Map** — tree of top-level dirs with one-line purpose each
3. **Key Files** — entry points, config files, main modules (with paths)
4. **Tech Stack** — frameworks, libraries, tools detected
5. **Conventions** — code style, naming patterns, test framework, lint rules
6. **Important Patterns** — repeated patterns, custom utilities, shared types
7. **Dev Commands** — build, test, run, lint commands
8. **Last Updated** — ISO 8601 timestamp

### Step 4 — Install the PreInvocation hook (session-local)

After writing `PROJECT_MEMORY.md`, check if `.agents/hooks.json` exists in the
workspace root. If not, create it with the memory-injector hook:

```json
{
  "project-memory-injector": {
    "PreInvocation": [
      {
        "type": "command",
        "command": "python \"C:\\Users\\dhp01\\.gemini\\config\\skills\\project-init\\scripts\\inject_memory.py\"",
        "timeout": 5
      }
    ]
  }
}
```

If `.agents/hooks.json` already exists, merge the `project-memory-injector`
key into it without overwriting existing hooks.

Create `.agents/` directory if it does not exist.

### Step 5 — Confirm completion

Report to the user:
- Total files scanned
- Lines of code
- Tech stack detected
- Path of `PROJECT_MEMORY.md`
- Confirm that the hook is active

Example output:
```
Project init complete.
  Files scanned : 142
  Lines of code : 18,430
  Stack detected: Python 3.11, FastAPI, PostgreSQL, Alembic
  Memory file   : /path/to/project/PROJECT_MEMORY.md
  Hook status   : PreInvocation hook active — memory will be injected automatically.
```

---

## Updating Memory

Re-run `/init` at any time to refresh `PROJECT_MEMORY.md`. The hook always
reads the latest version of the file, so no restart is needed.

---

## Notes

- `PROJECT_MEMORY.md` is safe to commit to version control — it helps teammates
  onboard faster and serves as a living project summary.
- The hook only injects when `PROJECT_MEMORY.md` exists in the workspace root.
  If the file is missing, the hook silently skips injection.
- The hook uses `ephemeralMessage` so the memory is injected as a transient
  system message and does not pollute the conversation history.
