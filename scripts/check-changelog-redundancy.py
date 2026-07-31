#!/usr/bin/env python3
"""Reject PRs that hand-edit CHANGELOG.md while also adding a changelog.d fragment.

Per docs/changelog-driven-releases.md §3, CHANGELOG.md is never edited by hand
— the release workflow (towncrier build) is its sole writer.  The only exempt
path is a programmatic tool fixing a bug in CHANGELOG.md itself (no fragment).

This gate fails when a changeset adds both:
- A prose line under ``## 0.0.0 (unreleased)`` in CHANGELOG.md
- A changelog.d/*.md fragment file

The changelog.d fragment is the single source of truth; the hand-edit is
redundant, drift-prone, and clobbered at the next ``towncrier build``.
"""

from __future__ import annotations

import subprocess
import sys


def run_git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"git {' '.join(args)} failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


def main() -> None:
    base_ref = sys.argv[1] if len(sys.argv) > 1 else "origin/main"

    changed = run_git("diff", "--name-only", f"{base_ref}...HEAD").splitlines()

    fragment_files = [
        f for f in changed if f.startswith("changelog.d/") and f.endswith(".md")
    ]

    if not fragment_files:
        print(
            "No changelog.d fragments in this changeset — "
            "skipping redundancy check."
        )
        sys.exit(0)

    if "CHANGELOG.md" not in changed:
        print("CHANGELOG.md not modified in this changeset — no redundancy.")
        sys.exit(0)

    diff = run_git("diff", f"{base_ref}...HEAD", "--", "CHANGELOG.md")

    in_unreleased = False
    prose_lines: list[str] = []

    for line in diff.splitlines():
        if line.startswith("@@"):
            continue

        # Determine the real content (strip diff prefix).
        content = line[1:] if line[:1] in "+-" else line
        stripped = content.strip()

        # Track section boundaries via version headers.
        if stripped.startswith("## "):
            in_unreleased = "0.0.0 (unreleased)" in stripped
            continue

        # Only care about added lines within the unreleased section.
        if not in_unreleased or not line.startswith("+"):
            continue

        # Skip structural lines: empty, comments, the header itself.
        if not stripped or stripped.startswith("<!--"):
            continue

        prose_lines.append(stripped)

    if not prose_lines:
        print(
            "CHANGELOG.md changes are structural (no prose under "
            "'## 0.0.0 (unreleased)') — ok."
        )
        sys.exit(0)

    print(
        "ERROR: CHANGELOG.md has hand-edited prose under"
        " '## 0.0.0 (unreleased)' while changelog.d/ fragments also exist"
        " in this changeset.\n"
        "\n"
        "Per docs/changelog-driven-releases.md §3, CHANGELOG.md is never"
        " edited by hand — changelog.d/ fragments are the single source"
        " of truth.\n"
        "\n"
        f"Fragments in this changeset: {', '.join(fragment_files)}\n"
        "\n"
        "Offending lines in CHANGELOG.md:\n"
    )
    for line in prose_lines:
        print(f"  {line}")
    print(
        "\nAction: remove the hand-edited lines from CHANGELOG.md — the"
        " changelog.d fragment alone is sufficient.  The release workflow"
        " (towncrier build) will compile CHANGELOG.md from fragments."
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
