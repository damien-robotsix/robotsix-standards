#!/usr/bin/env python3
"""Doc-example pinning gate: fenced ``uses:`` examples never use mutable refs.

docs/security-posture.md (rule 4a) and docs/repo-baseline.md mandate that every
GitHub Actions ``uses:`` reference be pinned to a full 40-char commit SHA with a
trailing ``# vX.Y.Z`` version comment, and scripts/check-workflow-security.py
enforces that on real workflows. Copy-paste examples in the standards pages
are not covered by that gate, so they drifted to mutable tag refs
(``actions/checkout@v4``) — and one page even labelled a tag pin "Good".

**Failure mode prevented:** a maintainer copies a tag-pinned example from a
standards page and either gets a red check-workflow-security.py gate, or — in
a repo without the checker — ships a mutable tag pin that an upstream tag
rewrite can hijack (the tj-actions/changed-files compromise, CVE-2025-30066).

This script scans fenced code blocks in ``docs/*.md`` for ``uses:`` lines whose
ref is a version tag (``@v4``, ``@3.1.0``) or a branch (``@main`` /
``@master``). The ``@<sha>`` placeholder and real 40-char SHAs pass; anything
after a ``#`` (the version comment) is ignored. Prose (non-fenced) mentions of
actions by tag are descriptive, not copy-paste examples, and are not checked.

Exits 0 when no fenced example uses a mutable ref, 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

DOCS_DIR = REPO_ROOT / "docs"

# A fence opener/closer: ``` or ~~~ (3+), optionally indented.
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")

# A ``uses:`` line whose ref is a mutable tag or branch. A 40-char hex SHA
# would otherwise match the ``\d[\w.]*`` branch when it starts with a digit,
# so it is excluded explicitly by the negative lookahead.
MUTABLE_REF_RE = re.compile(
    r"uses:\s*[\w./-]+@(?![0-9a-fA-F]{40}\b)(v?\d[\w.]*|main|master)\b"
)


def find_mutable_refs(content: str) -> list[int]:
    """Return 1-indexed line numbers of fenced ``uses:`` lines with mutable refs."""
    offending: list[int] = []
    fence: str | None = None
    for lineno, line in enumerate(content.splitlines(), start=1):
        match = FENCE_RE.match(line)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is None:
            continue
        code = line.split("#", 1)[0]
        if MUTABLE_REF_RE.search(code):
            offending.append(lineno)
    return offending


def main() -> int:
    """Check every ``docs/*.md`` fenced example for mutable ``uses:`` refs.

    Exit codes:
      0 — no fenced example uses a tag or branch ref
      1 — one or more fenced ``uses:`` lines use a mutable ref
    """
    pages = sorted(DOCS_DIR.glob("*.md"))
    failing = [
        f"docs/{path.name}:{lineno}"
        for path in pages
        for lineno in find_mutable_refs(path.read_text())
    ]

    print(f"Checked {len(pages)} page(s) for mutable `uses:` refs in examples ...")

    if failing:
        for location in failing:
            print(f"  MUTABLE ref in fenced example: {location}")
        print(
            f"\n{len(failing)} fenced `uses:` line(s) pin a tag or branch.  Use "
            "the placeholder form `uses: owner/action@<sha>  # vX.Y.Z` "
            "(docs/security-posture.md rule 4a)."
        )
        return 1

    print("All fenced `uses:` examples are SHA-pinned.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
