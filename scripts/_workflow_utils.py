#!/usr/bin/env python3
"""Shared scaffolding for the workflow CI gate scripts.

``check-workflow-security.py`` and ``check-workflow-timeouts.py`` (the CI
gates for ``.github/workflows/``) used to each define the repo-root /
workflows-dir constants and walk the workflows directory themselves.  The two
copies drifted: the security gate globbed ``*.yml`` *and* ``*.yaml`` while
the timeout gate globbed only ``*.yml``, so a ``.yaml`` workflow would be
security-audited but never timeout-checked.  This module is the single source
of truth for that walk — the glob pattern and the read-with-error-handling
routine live here once and are imported by both gates, so they cannot drift.

The leading underscore marks this as an internal helper shared by sibling
scripts, not a public API.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


def iter_workflow_files(workflows_dir: Path = WORKFLOWS_DIR) -> Iterator[Path]:
    """Yield every workflow file under *workflows_dir*, in sorted order.

    Both ``.yml`` and ``.yaml`` files are included — a workflow may use either
    extension — with all ``.yml`` files yielded before the ``.yaml`` files.
    Yields nothing when *workflows_dir* does not exist; callers treat an empty
    walk as "nothing to check".
    """
    if not workflows_dir.is_dir():
        return
    for pattern in ("*.yml", "*.yaml"):
        yield from sorted(workflows_dir.glob(pattern))


def read_workflow(wf: Path) -> str | None:
    """Return *wf*'s text, or None after printing an ERROR on OSError."""
    try:
        return wf.read_text()
    except OSError as exc:  # pragma: no cover - defensive
        print(f"ERROR: cannot read {wf.name}: {exc}")
        return None
