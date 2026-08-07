#!/usr/bin/env python3
"""Gate: reject PRs that add multiple changelog fragments with the same timestamp.

A changelog fragment filename carries the ticket timestamp as its prefix
(e.g. ``20260802T153209Z``).  Two fragments sharing the same timestamp
double-record the same event — a single event must have exactly one fragment.

This script diffs the PR against its merge-base (default ``origin/main``) and
flags any timestamp that appears in two or more **newly added** fragment files.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Timestamp pattern: ``YYYYMMDDTHHMMSSZ`` at start of filename.
_TIMESTAMP_RE = re.compile(r"^(\d{8}T\d{6}Z)")


def _run_git_diff(base_ref: str) -> list[str]:
    """Run ``git diff --name-only --diff-filter=A`` and return matching files."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=A", f"{base_ref}...HEAD"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return [
        f
        for f in result.stdout.strip().splitlines()
        if f.startswith("changelog.d/") and f.endswith(".md")
    ]


def get_new_fragments(base_ref: str) -> list[str]:
    """Return ``changelog.d/*.md`` files newly added in the current branch."""
    # Try the requested base ref first.
    try:
        return _run_git_diff(base_ref)
    except RuntimeError:
        pass  # fall through to auto-detection

    # If the base ref doesn't exist (e.g. shallow PR clone), try HEAD^1
    # (on a PR merge commit, HEAD^1 is the base branch tip).
    try:
        return _run_git_diff("HEAD^1")
    except RuntimeError:
        pass

    print(
        f"git diff failed: '{base_ref}' (and fallback 'HEAD^1') not available.\n"
        "Fetch the base branch (e.g. 'git fetch origin main') and try again."
    )
    sys.exit(1)


def main() -> int:
    base_ref = sys.argv[1] if len(sys.argv) > 1 else "origin/main"

    try:
        fragments = get_new_fragments(base_ref)
    except SystemExit:
        return 1

    if not fragments:
        print("No new changelog fragments in this changeset.")
        return 0

    by_timestamp: dict[str, list[str]] = defaultdict(list)
    for path in fragments:
        basename = Path(path).name
        m = _TIMESTAMP_RE.match(basename)
        if m is None:
            print(f"WARNING: fragment filename has no timestamp prefix: {path}")
            continue
        by_timestamp[m.group(1)].append(path)

    duplicates = {ts: files for ts, files in by_timestamp.items() if len(files) > 1}

    if duplicates:
        print("ERROR: Multiple new changelog fragments share the same timestamp —")
        print("       each event must have exactly one fragment.\n")
        for ts, files in sorted(duplicates.items()):
            print(f"  {ts}:")
            for f in sorted(files):
                print(f"    {f}")
        print("\nMerge or remove the extra fragments and push again.")
        return 1

    print(f"OK — {len(fragments)} new fragment(s), no duplicate timestamps.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
