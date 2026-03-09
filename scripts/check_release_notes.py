#!/usr/bin/env python3
"""Enforce release notes presence for tagged releases."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _tag_variants(tag: str) -> set[str]:
    clean = tag.strip()
    variants = {clean}
    bare = clean[1:] if clean.lower().startswith("v") else clean
    variants.add(bare)
    variants.add(f"v{bare}")
    return {item for item in variants if item}


def _has_tag_heading(path: Path, tag: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    for variant in _tag_variants(tag):
        pattern = re.compile(
            rf"^(##|###)\s*(\[\s*)?{re.escape(variant)}(\s*\])?(\s+-|\s+\(|\s*:?|$)",
            re.MULTILINE,
        )
        if pattern.search(text):
            return True
    return False


def _notes_file_candidates(tag: str) -> list[Path]:
    variants = _tag_variants(tag)
    candidates = []
    for variant in variants:
        candidates.append(REPO_ROOT / "docs" / "releases" / f"{variant}.md")
        candidates.append(REPO_ROOT / "releases" / f"{variant}.md")
    return candidates


def _find_release_note_source(tag: str) -> str | None:
    for path in _notes_file_candidates(tag):
        if path.exists():
            return str(path.relative_to(REPO_ROOT))

    changelog_paths = [
        REPO_ROOT / "CHANGELOG.md",
        REPO_ROOT / "docs" / "CHANGELOG.md",
    ]
    for path in changelog_paths:
        if _has_tag_heading(path, tag):
            return str(path.relative_to(REPO_ROOT))

    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check release notes for a tag.")
    parser.add_argument(
        "--tag",
        default=os.getenv("GITHUB_REF_NAME", ""),
        help="Tag name to validate (defaults to GITHUB_REF_NAME).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tag = args.tag.strip()
    if not tag:
        raise SystemExit("Missing tag. Pass --tag or set GITHUB_REF_NAME.")

    source = _find_release_note_source(tag)
    if source:
        print(f"release notes check: OK ({tag} documented in {source})")
        return 0

    print("release notes check: FAIL")
    print(f"- No release notes found for tag '{tag}'.")
    print("- Add one of:")
    print(f"  - docs/releases/{tag}.md")
    print(f"  - releases/{tag}.md")
    print(f"  - CHANGELOG.md heading like '## [{tag}]' (or '## {tag}')")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
