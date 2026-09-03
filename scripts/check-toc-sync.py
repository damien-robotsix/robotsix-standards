#!/usr/bin/env python3
"""Bidirectional TOC-sync gate for mkdocs.yml ↔ README.md + docs/index.md.

Parses mkdocs.yml, extracts page references under the configured nav sections,
and checks that:
- each nav page appears in both README.md and docs/index.md (forward); and
- each page linked from README.md / docs/index.md appears in the nav (reverse).

Exits 0 on success, 1 if any entries are missing or orphaned.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml  # type: ignore[import-untyped]

REPO_ROOT = Path(__file__).resolve().parent.parent

MKDOCS_YML = REPO_ROOT / "mkdocs.yml"
README_MD = REPO_ROOT / "README.md"
INDEX_MD = REPO_ROOT / "docs" / "index.md"

# Top-level nav keys whose sub-pages must appear in README.md and docs/index.md.
SECTIONS_TO_CHECK = ["Every repo", "Deployable components", "Deployment system", "Meta"]

# Map nav section names to the marker strings that introduce the corresponding
# sections in README.md and docs/index.md.  Used to scope reverse-direction
# extraction to the right section.
_SECTION_MARKERS: dict[str, dict[str, str]] = {
    "Every repo": {
        "readme": "**Every repository**",
        "index": "### Every repository",
    },
    "Deployable components": {
        "readme": "**Deployable components**",
        "index": "### Deployable components",
    },
    "Deployment system": {
        "readme": "**The deployment system**",
        "index": "### The deployment system",
    },
    "Meta": {
        "readme": "**Meta**",
        "index": "### Meta",
    },
}

# Ordered lists of section-introducing markers in each file, so we can bound
# extraction between a section header and the next one.
_README_MARKERS = [
    "**Every repository**",
    "**Deployable components**",
    "**The deployment system**",
    "**Meta**",
]
_INDEX_MARKERS = [
    "### Every repository",
    "### Deployable components",
    "### The deployment system",
    "### Meta",
]


def extract_pages(nav: list[object], section_name: str) -> list[str]:
    """Return page filenames (e.g. 'docstrings.md') listed under *section_name*."""
    for item in nav:
        if not isinstance(item, dict):
            continue
        for key, value in item.items():
            if key != section_name:
                continue
            if isinstance(value, list):
                return [next(iter(sub.values())) for sub in value]
            if isinstance(value, str):
                return [value]
            break
    return []


def missing_pages(pages: list[str], filepath: Path) -> list[str]:
    """Return pages whose bare filename does NOT appear in *filepath*."""
    content = filepath.read_text()
    return [p for p in pages if p not in content]


def _extract_section_text(content: str, marker: str, all_markers: list[str]) -> str:
    """Return the substring of *content* from *marker* to the next marker."""
    start = content.find(marker)
    if start == -1:
        return ""
    marker_idx = all_markers.index(marker)
    end = len(content)
    for nm in all_markers[marker_idx + 1 :]:
        nidx = content.find(nm, start + len(marker))
        if nidx != -1:
            end = nidx
            break
    return content[start:end]


def _extract_readme_pages(
    content: str, marker: str, all_markers: list[str]
) -> list[str]:
    """Extract page filenames from links like ``[text](docs/<page>.md)`` in a README section."""
    section = _extract_section_text(content, marker, all_markers)
    return re.findall(r"\]\(docs/([^)]+\.md)\)", section)


def _extract_index_pages(
    content: str, marker: str, all_markers: list[str]
) -> list[str]:
    """Extract page filenames from links like ``[text](<page>.md)`` in an index section."""
    section = _extract_section_text(content, marker, all_markers)
    return re.findall(r"\]\(([^)]+\.md)\)", section)


def _all_nav_pages(nav: list[object]) -> set[str]:
    """Return the set of all page filenames referenced anywhere in the nav."""
    pages: set[str] = set()
    for item in nav:
        if not isinstance(item, dict):
            continue
        for value in item.values():
            if isinstance(value, list):
                for sub in value:
                    if isinstance(sub, dict):
                        pages.update(sub.values())
            elif isinstance(value, str):
                pages.add(value)
    return pages


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

    # Reverse direction: every page linked from README.md / docs/index.md
    # must appear somewhere in the mkdocs.yml nav (any section).
    readme_content = README_MD.read_text()
    index_content = INDEX_MD.read_text()

    all_nav = _all_nav_pages(nav)

    all_orphaned: list[tuple[str, str, str]] = []

    for section in SECTIONS_TO_CHECK:
        # Only run reverse extraction for sections that actually exist
        # in the nav; skip sections with no pages so we don't report
        # false orphans for pages extracted from stale marker regions.
        markers = _SECTION_MARKERS.get(section)
        if not markers:
            continue

        readme_pages = _extract_readme_pages(
            readme_content, markers["readme"], _README_MARKERS
        )
        for page in readme_pages:
            if page not in all_nav:
                print(f"  ORPHANED in README.md (not in mkdocs.yml nav): {page}")
                all_orphaned.append((section, "README.md → nav", page))

        index_pages = _extract_index_pages(
            index_content, markers["index"], _INDEX_MARKERS
        )
        for page in index_pages:
            if page not in all_nav:
                print(f"  ORPHANED in docs/index.md (not in mkdocs.yml nav): {page}")
                all_orphaned.append((section, "docs/index.md → nav", page))

    if all_missing or all_orphaned:
        if all_missing:
            print(
                f"\n{len(all_missing)} missing entry(s) found.  "
                "Update README.md and/or docs/index.md to match mkdocs.yml nav."
            )
        if all_orphaned:
            print(
                f"\n{len(all_orphaned)} orphaned page(s) found in README.md / "
                "docs/index.md that are not in mkdocs.yml nav.  "
                "Add them to mkdocs.yml nav or remove the references."
            )
        return 1

    print("All TOC entries are synchronized.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
