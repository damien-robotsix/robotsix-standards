#!/usr/bin/env python3
"""Verify that mkdocs.yml nav pages appear in README.md and docs/index.md.

Parses mkdocs.yml, extracts page references under the configured nav sections,
and checks that each page filename appears in both README.md and docs/index.md.
Exits 0 on success, 1 if any entries are missing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml  # type: ignore[import-untyped]

REPO_ROOT = Path(__file__).resolve().parent.parent

MKDOCS_YML = REPO_ROOT / "mkdocs.yml"
README_MD = REPO_ROOT / "README.md"
INDEX_MD = REPO_ROOT / "docs" / "index.md"

# Top-level nav keys whose sub-pages must appear in README.md and docs/index.md.
SECTIONS_TO_CHECK = ["Every repo", "Deployable components"]


def extract_pages(nav: list[object], section_name: str) -> list[str]:
    """Return page filenames (e.g. 'docstrings.md') listed under *section_name*."""
    for item in nav:
        if not isinstance(item, dict):
            continue
        for key, value in item.items():
            if key != section_name:
                continue
            if isinstance(value, list):
                return [list(sub.values())[0] for sub in value]
            if isinstance(value, str):
                return [value]
            break
    return []


def missing_pages(pages: list[str], filepath: Path) -> list[str]:
    """Return pages whose bare filename does NOT appear in *filepath*."""
    content = filepath.read_text()
    return [p for p in pages if p not in content]


def main() -> int:
    with MKDOCS_YML.open() as fh:
        config = yaml.safe_load(fh)

    nav: list[object] = config.get("nav", [])

    all_missing: list[tuple[str, str, str]] = []

    for section in SECTIONS_TO_CHECK:
        pages = extract_pages(nav, section)
        if not pages:
            print(
                f"WARNING: section '{section}' not found or has no pages "
                f"in mkdocs.yml nav"
            )
            continue

        print(f"Checking section '{section}' ({len(pages)} pages) ...")

        for page in missing_pages(pages, README_MD):
            print(f"  MISSING from README.md: {page}")
            all_missing.append((section, "README.md", page))

        for page in missing_pages(pages, INDEX_MD):
            print(f"  MISSING from docs/index.md: {page}")
            all_missing.append((section, "docs/index.md", page))

    if all_missing:
        print(
            f"\n{len(all_missing)} missing entry(s) found.  "
            "Update README.md and/or docs/index.md to match mkdocs.yml nav."
        )
        return 1

    print("All TOC entries are synchronized.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
