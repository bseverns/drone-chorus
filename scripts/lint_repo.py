#!/usr/bin/env python3
"""Lightweight repository lint checks used in CI."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def lint_yaml() -> list[str]:
    errors: list[str] = []
    for pattern in ("config/**/*.yaml", "presets/**/*.yaml"):
        for path in sorted(REPO_ROOT.glob(pattern)):
            try:
                with path.open("r", encoding="utf-8") as fh:
                    yaml.safe_load(fh)
            except Exception as exc:
                errors.append(f"{path.relative_to(REPO_ROOT)}: invalid YAML ({exc})")
    return errors


def lint_markdown_links() -> list[str]:
    errors: list[str] = []
    md_paths = sorted(REPO_ROOT.glob("*.md"))
    md_paths.extend(sorted(REPO_ROOT.glob("docs/**/*.md")))
    md_paths.extend(sorted(REPO_ROOT.glob("software/**/*.md")))
    md_paths.extend(sorted(REPO_ROOT.glob("data/**/*.md")))
    md_paths.extend(sorted(REPO_ROOT.glob("logs/**/*.md")))
    md_paths.extend(sorted(REPO_ROOT.glob("obs/**/*.md")))
    md_paths.extend(sorted(REPO_ROOT.glob("vcv/**/*.md")))

    seen = set()
    for path in md_paths:
        if path in seen:
            continue
        seen.add(path)
        text = path.read_text(encoding="utf-8")
        for target in LINK_RE.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            clean = target.split("#", 1)[0].split("?", 1)[0].strip()
            if not clean:
                continue
            resolved = (path.parent / clean).resolve()
            if not resolved.exists():
                rel_path = path.relative_to(REPO_ROOT)
                errors.append(f"{rel_path}: broken link target '{target}'")
    return errors


def lint_scope_statements() -> list[str]:
    errors: list[str] = []
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    if "CLI stack is the canonical control surface" not in root_readme:
        errors.append("README.md: missing CLI-canonical scope statement")

    gui_doc = (REPO_ROOT / "docs" / "GUI_CONTROL_ROOM.md").read_text(encoding="utf-8")
    if "GUI scope: single-drone bridge operation" not in gui_doc:
        errors.append("docs/GUI_CONTROL_ROOM.md: missing explicit GUI scope statement")
    return errors


def lint_release_policy() -> list[str]:
    errors: list[str] = []
    release_doc = REPO_ROOT / "docs" / "releases" / "README.md"
    if not release_doc.exists():
        errors.append("docs/releases/README.md: missing release notes policy doc")
    return errors


def main() -> int:
    errors: list[str] = []
    errors.extend(lint_yaml())
    errors.extend(lint_markdown_links())
    errors.extend(lint_scope_statements())
    errors.extend(lint_release_policy())

    if not errors:
        print("repo lint: OK")
        return 0

    print("repo lint: FAIL")
    for error in errors:
        print(f"- {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
