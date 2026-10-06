# Contributing to project-init

Thank you for your interest in contributing.

## Ways to Contribute

- **Bug reports** — Open a GitHub Issue with a minimal reproduction.
- **Feature requests** — Describe the use case in a GitHub Issue before opening a PR.
- **Pull requests** — Fork, branch from `main`, make changes, and open a PR.

## Development Setup

```bash
git clone git@github.com:rootkind35-del/project-init.git
cd project-init
python --version   # 3.8+ required
```

No additional dependencies. All scripts use the Python standard library.

## Testing a Change

Run the scanner against any local project:

```bash
python scripts/scan_project.py /path/to/any/project | python scripts/write_memory.py /tmp/test-project
cat /tmp/test-project/PROJECT_MEMORY.md
```

Test the hook in isolation:

```powershell
# Windows
echo '{"workspacePaths": ["C:\\path\\to\\project"], "invocationNum": 1}' | python scripts/inject_memory.py
```

```bash
# Unix
echo '{"workspacePaths": ["/path/to/project"], "invocationNum": 1}' | python scripts/inject_memory.py
```

## Code Style

- Standard library only (no third-party deps).
- Type hints encouraged.
- Keep `scan_project.py` self-contained — it must run with `python scan_project.py <root>` and nothing else.

## Roadmap Items

Check the [open issues](https://github.com/rootkind35-del/project-init/issues) tagged `roadmap` for planned features to pick up.
