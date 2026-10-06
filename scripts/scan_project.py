#!/usr/bin/env python3
"""
scan_project.py — Project memory scanner for Antigravity project-init skill.

Usage:
    python scan_project.py <workspace_root>

Outputs a JSON object to stdout with full project intelligence.
"""

import sys
import os
import json
import re
import subprocess
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Directories to skip entirely
SKIP_DIRS = {
    ".git", ".svn", ".hg",
    "node_modules", "__pycache__", ".venv", "venv", "env", ".env",
    "dist", "build", "out", ".next", ".nuxt", ".output",
    "target", "bin", "obj",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".idea", ".vscode", ".vs",
    "coverage", ".coverage", "htmlcov",
    "vendor", "third_party", "extern",
    ".agents", ".gemini",
}

# Files to skip
SKIP_FILES = {
    ".DS_Store", "Thumbs.db", "desktop.ini",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "Pipfile.lock", "poetry.lock", "composer.lock",
    "Cargo.lock",
}

# Max file size to read for content analysis (128 KB)
MAX_READ_BYTES = 131_072

# Extensions considered "code"
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs",
    ".go", ".rs", ".java", ".kt", ".kts", ".scala",
    ".c", ".cc", ".cpp", ".h", ".hpp",
    ".cs", ".fs", ".vb",
    ".rb", ".php", ".lua", ".pl", ".r", ".R",
    ".swift", ".m", ".mm",
    ".ex", ".exs", ".erl", ".hrl",
    ".clj", ".cljs",
    ".hs", ".lhs",
    ".sh", ".bash", ".zsh", ".fish", ".ps1", ".psm1",
    ".html", ".htm", ".css", ".scss", ".sass", ".less",
    ".vue", ".svelte",
    ".sql", ".graphql", ".gql",
    ".tf", ".tfvars", ".hcl",
    ".yaml", ".yml", ".toml", ".json", ".jsonc", ".ini", ".cfg", ".conf",
    ".proto",
    ".md", ".rst", ".txt",
    ".Dockerfile", ".dockerfile",
}

# Config/manifest files that indicate tech stack
MANIFEST_FILES = {
    "package.json": "Node.js",
    "package-lock.json": "Node.js",
    "yarn.lock": "Yarn",
    "pnpm-lock.yaml": "pnpm",
    "pyproject.toml": "Python",
    "setup.py": "Python",
    "setup.cfg": "Python",
    "requirements.txt": "Python",
    "Pipfile": "Python/Pipenv",
    "poetry.lock": "Python/Poetry",
    "go.mod": "Go",
    "go.sum": "Go",
    "Cargo.toml": "Rust",
    "pom.xml": "Java/Maven",
    "build.gradle": "Java/Gradle",
    "build.gradle.kts": "Kotlin/Gradle",
    "composer.json": "PHP",
    "Gemfile": "Ruby",
    "Rakefile": "Ruby",
    "mix.exs": "Elixir",
    "rebar.config": "Erlang",
    "cabal.project": "Haskell",
    "stack.yaml": "Haskell/Stack",
    "CMakeLists.txt": "C/C++/CMake",
    "Makefile": "Make",
    "Dockerfile": "Docker",
    "docker-compose.yml": "Docker Compose",
    "docker-compose.yaml": "Docker Compose",
    ".terraform": "Terraform",
    "pubspec.yaml": "Dart/Flutter",
    "build.sbt": "Scala/SBT",
    "project.clj": "Clojure/Leiningen",
    "deps.edn": "Clojure/deps",
    ".swift-version": "Swift",
}

# Framework detection patterns (file content based)
FRAMEWORK_PATTERNS = {
    "FastAPI": [r"from fastapi import", r"import fastapi"],
    "Django": [r"from django", r"import django", r"DJANGO_SETTINGS_MODULE"],
    "Flask": [r"from flask import", r"import flask"],
    "SQLAlchemy": [r"from sqlalchemy", r"import sqlalchemy"],
    "React": [r"from 'react'", r'from "react"', r"import React"],
    "Vue": [r"from 'vue'", r'from "vue"', r"createApp\("],
    "Angular": [r"@angular/core", r"NgModule\("],
    "Next.js": [r"from 'next/", r'from "next/', r"next/app"],
    "NestJS": [r"@nestjs/common", r"@Module\("],
    "Express": [r"require\('express'\)", r'require\("express"\)', r"from 'express'"],
    "Spring": [r"@SpringBootApplication", r"@RestController"],
    "Gin": [r'"github.com/gin-gonic/gin"'],
    "Echo": [r'"github.com/labstack/echo"'],
    "Axum": [r"use axum", r"axum::Router"],
    "Actix": [r"use actix_web"],
    "Pytest": [r"import pytest", r"from pytest"],
    "Jest": [r"from '@jest/", r"describe\(", r"test\("],
    "Vitest": [r"from 'vitest'", r"import { describe }"],
    "Tailwind CSS": [r"tailwind", r"@tailwind base"],
    "PostgreSQL": [r"postgresql://", r"psycopg2", r"asyncpg"],
    "MySQL": [r"mysql://", r"pymysql", r"mysql-connector"],
    "MongoDB": [r"mongodb://", r"pymongo", r"mongoose"],
    "Redis": [r"redis://", r"aioredis", r"ioredis"],
    "Prisma": [r"@prisma/client", r"prisma.schema"],
    "Alembic": [r"from alembic", r"import alembic"],
    "Docker": [r"FROM ", r"WORKDIR ", r"EXPOSE "],
    "GitHub Actions": [r"on:\n\s+push", r"jobs:\n"],
}

# Entry point patterns
ENTRY_POINT_NAMES = {
    "main.py", "app.py", "server.py", "index.py", "run.py", "manage.py",
    "main.go", "main.ts", "main.js", "index.ts", "index.js",
    "src/main.ts", "src/main.js", "src/index.ts", "src/index.js",
    "src/app.ts", "src/app.js", "src/main.py", "src/app.py",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "main.rs", "lib.rs",
    "Program.cs", "Startup.cs",
    "Application.java", "Main.java",
    "app.rb", "config.ru",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_binary(path: Path) -> bool:
    """Quick binary detection by reading first 8 KB."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(8192)
        return b"\x00" in chunk
    except OSError:
        return True


def count_lines(path: Path) -> int:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def read_head(path: Path, max_bytes: int = MAX_READ_BYTES) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(max_bytes)
    except OSError:
        return ""


def detect_license(root: Path) -> str:
    for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "COPYING"):
        p = root / name
        if p.exists():
            head = read_head(p, 512)
            if "MIT" in head:
                return "MIT"
            if "Apache" in head:
                return "Apache-2.0"
            if "GPL" in head:
                return "GPL"
            if "BSD" in head:
                return "BSD"
            return "Custom"
    return "Unknown"


def get_git_info(root: Path) -> dict:
    info = {}
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=root, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            info["remote"] = result.stdout.strip()
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%H|%an|%ae|%s"],
            cwd=root, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split("|", 3)
            if len(parts) == 4:
                info["last_commit"] = {
                    "hash": parts[0][:8],
                    "author": parts[1],
                    "email": parts[2],
                    "message": parts[3],
                }
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=root, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            info["branch"] = result.stdout.strip()
    except Exception:
        pass
    return info


# ---------------------------------------------------------------------------
# Core scanner
# ---------------------------------------------------------------------------

def scan(root: Path) -> dict:
    root = root.resolve()

    files_by_ext: dict[str, list[str]] = defaultdict(list)
    key_files: list[dict] = []
    all_contents: dict[str, str] = {}  # rel_path -> text content
    total_files = 0
    total_lines = 0
    total_bytes = 0
    dir_purposes: dict[str, list[str]] = defaultdict(list)  # top-level dir -> file names

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skip dirs in-place
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS and not d.startswith(".")
        ]

        rel_dir = Path(dirpath).relative_to(root)
        top_level = rel_dir.parts[0] if rel_dir.parts else "."

        for fname in filenames:
            if fname in SKIP_FILES:
                continue
            fpath = Path(dirpath) / fname
            ext = fpath.suffix.lower() or fpath.name
            rel = str(fpath.relative_to(root)).replace("\\", "/")

            # Track top-level directory contents
            if top_level != ".":
                dir_purposes[top_level].append(fname)

            # Stat
            try:
                size = fpath.stat().st_size
            except OSError:
                continue
            total_bytes += size
            total_files += 1

            if ext in CODE_EXTENSIONS or fpath.name in MANIFEST_FILES:
                files_by_ext[ext].append(rel)
                lines = count_lines(fpath)
                total_lines += lines

                # Read content for important files
                if fpath.name in MANIFEST_FILES or rel in ENTRY_POINT_NAMES or size <= MAX_READ_BYTES:
                    if not is_binary(fpath):
                        all_contents[rel] = read_head(fpath)

            # Key files
            if fname in MANIFEST_FILES or rel in ENTRY_POINT_NAMES:
                key_files.append({"path": rel, "purpose": MANIFEST_FILES.get(fname, "entry point")})

    # -- Stack detection from manifests --
    stack: set[str] = set()
    for rel, text in all_contents.items():
        fname = Path(rel).name
        if fname in MANIFEST_FILES:
            stack.add(MANIFEST_FILES[fname])

    # -- Framework detection --
    frameworks: set[str] = set()
    combined_text = "\n".join(all_contents.values())
    for framework, patterns in FRAMEWORK_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, combined_text, re.MULTILINE):
                frameworks.add(framework)
                break

    # -- Conventions detection --
    conventions: list[str] = []

    # Linter configs
    for linter_file in (".eslintrc", ".eslintrc.json", ".eslintrc.js", ".eslintrc.yaml",
                         "pyproject.toml", ".flake8", ".pylintrc", ".ruff.toml",
                         "biome.json", ".prettierrc"):
        if any(rel.endswith(linter_file) for rel in all_contents):
            conventions.append(f"Linter config: {linter_file}")

    # Type checking
    if "tsconfig.json" in [Path(r).name for r in all_contents]:
        conventions.append("TypeScript strict mode detected")
    if any("mypy" in t or "pyright" in t for t in all_contents.values()):
        conventions.append("Python type checking active (mypy/pyright)")

    # Test patterns
    test_files = [r for r in all_contents if "test" in r.lower() or "spec" in r.lower()]
    if test_files:
        conventions.append(f"Tests found: {len(test_files)} test/spec files")

    # -- Dev commands from manifests --
    dev_commands: dict[str, str] = {}
    if "package.json" in all_contents.get("package.json", ""):
        pass  # parsed below
    for rel, text in all_contents.items():
        if Path(rel).name == "package.json":
            try:
                pkg = json.loads(text)
                scripts = pkg.get("scripts", {})
                for cmd in ("dev", "start", "build", "test", "lint"):
                    if cmd in scripts:
                        dev_commands[cmd] = f"npm run {cmd}"
            except Exception:
                pass
        if Path(rel).name == "Makefile":
            targets = re.findall(r"^([a-zA-Z][a-zA-Z0-9_-]+)\s*:", text, re.MULTILINE)
            for t in targets[:10]:
                dev_commands[t] = f"make {t}"
        if Path(rel).name == "pyproject.toml":
            for match in re.finditer(r'\[tool\.(?:poetry\.)?scripts\]\n(.*?)(?:\n\[|\Z)', text, re.DOTALL):
                for line in match.group(1).splitlines():
                    if "=" in line:
                        name, _, cmd = line.partition("=")
                        dev_commands[name.strip()] = cmd.strip().strip('"')

    # -- Top-level directory map --
    dir_map: dict[str, str] = {}
    for d in sorted(dir_purposes.keys()):
        files = dir_purposes[d]
        # Guess purpose from contents
        if any(f.endswith((".test.ts", ".spec.ts", ".test.js", ".spec.js")) for f in files):
            purpose = "tests"
        elif d in ("src", "lib", "app", "core", "pkg"):
            purpose = "main source code"
        elif d in ("docs", "documentation"):
            purpose = "documentation"
        elif d in ("scripts", "tools", "bin"):
            purpose = "build/utility scripts"
        elif d in ("config", "configs", "settings"):
            purpose = "configuration"
        elif d in ("public", "static", "assets", "media"):
            purpose = "static assets"
        elif d in ("migrations", "alembic"):
            purpose = "database migrations"
        elif d in ("api", "routes", "endpoints", "controllers"):
            purpose = "API layer"
        elif d in ("models", "entities", "schemas"):
            purpose = "data models"
        elif d in ("services", "usecases", "domain"):
            purpose = "business logic"
        elif d in ("infra", "infrastructure", "repositories"):
            purpose = "infrastructure / data access"
        elif d in ("components", "ui", "views", "pages", "templates"):
            purpose = "UI components / views"
        elif d in ("hooks", "composables", "stores"):
            purpose = "frontend logic"
        elif d in ("types", "interfaces", "dto"):
            purpose = "type definitions"
        elif d in ("utils", "helpers", "common", "shared"):
            purpose = "shared utilities"
        else:
            purpose = f"{len(files)} files"
        dir_map[d] = purpose

    # -- Language breakdown --
    lang_lines: dict[str, int] = defaultdict(int)
    for ext, paths in files_by_ext.items():
        for rel in paths:
            fpath = root / rel
            lang_lines[ext] += count_lines(fpath)

    top_langs = sorted(lang_lines.items(), key=lambda x: -x[1])[:8]

    return {
        "workspace_root": str(root),
        "project_name": root.name,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "total_files": total_files,
        "total_lines": total_lines,
        "total_bytes": total_bytes,
        "language_breakdown": [{"ext": ext, "lines": lines} for ext, lines in top_langs],
        "stack": sorted(stack),
        "frameworks": sorted(frameworks),
        "key_files": key_files[:30],
        "dir_map": dir_map,
        "conventions": conventions,
        "dev_commands": dev_commands,
        "license": detect_license(root),
        "git": get_git_info(root),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: scan_project.py <workspace_root>"}))
        sys.exit(1)

    root = Path(sys.argv[1])
    if not root.exists():
        print(json.dumps({"error": f"Path does not exist: {root}"}))
        sys.exit(1)

    result = scan(root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
