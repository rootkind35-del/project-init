# Manual Scan Procedure (Python Fallback)

Use this only when `scan_project.py` cannot run (e.g., Python not installed).

## Step 1 — Build directory tree

Run one of these commands from the workspace root:

**Windows (PowerShell):**
```powershell
Get-ChildItem -Recurse -Depth 3 | Where-Object { $_.FullName -notmatch "node_modules|\.git|__pycache__|dist|build" } | Select-Object FullName
```

**Unix/macOS:**
```bash
find . -maxdepth 3 -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/__pycache__/*'
```

## Step 2 — Detect tech stack manually

Check for these manifest files in the root:
- `package.json` → Node.js
- `pyproject.toml` / `requirements.txt` → Python
- `go.mod` → Go
- `Cargo.toml` → Rust
- `pom.xml` / `build.gradle` → Java/Kotlin
- `Gemfile` → Ruby
- `composer.json` → PHP
- `Dockerfile` → containerized

## Step 3 — Read key files

Read and summarize:
1. `README.md` (or `README.rst`) — project overview
2. The main manifest (e.g., `package.json`, `pyproject.toml`)
3. Entry point files (e.g., `main.py`, `index.ts`, `main.go`)
4. Any `Makefile` or `justfile` for dev commands

## Step 4 — Write PROJECT_MEMORY.md manually

Use the sections from the main SKILL.md (Project Identity, Directory Map,
Key Files, Tech Stack, Conventions, Dev Commands, Last Updated).
