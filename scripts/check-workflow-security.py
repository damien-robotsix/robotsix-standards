#!/usr/bin/env python3
"""Check that workflow files meet the security-posture 4a/4c rules.

This script is the automated enforcement gate referenced by the
workflow-permissions audit in docs/security-posture.md (gates 4a — actions
pinned to commit SHAs — and 4c — least-privilege `permissions:` blocks).  It
runs in CI on PRs (see .github/workflows/baseline-check.yml and
.github/workflows/ci.yml) and exits non-zero when a workflow file violates
either rule.  It is the self-enforcing gate for **content-only repos**, which
are exempt from the zizmor workflow audit (gate 4b) but must still meet 4a
and 4c — for code repos zizmor mechanically enforces both, so content-only
repos need this script to keep those gates self-enforcing.

Rules enforced (per docs/security-posture.md):

  4a — Actions pinned to commit SHAs
    - Every `uses:` value (step-level and job-level reusable-workflow
      callers) must be pinned to an immutable ref.
    - Local refs starting with `./` are exempt (they resolve to the current
      repo's own workflow directory, not a third-party action).
    - `docker://` refs must pin `@sha256:<digest>`; a mutable tag fails.
    - All other `owner/repo[/path]@<ref>` refs: `<ref>` must be a full
      40-character commit SHA AND the line must carry a trailing `#` version
      comment (the `# vX.Y.Z` / `# main` comment).  This applies to first-party
      robotsix reusable workflows too.

  4c — Least-privilege `permissions:` blocks
    - Every workflow file MUST declare a top-level `permissions:` key.
    - No `permissions: write-all` at workflow or job level.

Exit codes:
  0 — all workflow files satisfy the 4a/4c rules
  1 — a workflow file violates a rule
  2 — script error (cannot read a workflow file, etc.)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

# A pinned ref is exactly 40 hex characters (a full commit SHA).
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

# A `uses:` value, with an optional leading `- ` list dash (step level) and an
# optional trailing `# <version>` comment (job-level callers and steps alike).
_USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*(\S+)(\s*#.*)?$")

# A top-level `permissions:` declaration (indent 0).
_TOP_PERMISSIONS_RE = re.compile(r"^permissions:\s*(.*)$")

# `permissions: write-all` at workflow or job level (any indentation).
_WRITE_ALL_RE = re.compile(r"^\s*permissions:\s*write-all\s*(#.*)?$")


def _check_4a_uses(value: str, has_comment: bool) -> list[str]:
    """Validate one ``uses:`` *value* against rule 4a.

    Returns a list of human-readable violation messages (empty when the value
    is compliant).
    """
    # Local refs resolve to this repo's own workflow directory; exempt.
    if value.startswith("./"):
        return []

    # Container actions must pin a digest; a mutable tag is drift-prone.
    if value.startswith("docker://"):
        if "@sha256:" not in value:
            return [
                "4a: docker:// ref must pin @sha256:<digest> "
                f"(got: {value})"
            ]
        return []

    # Everything else is `owner/repo[/path]@<ref>`: the ref must be a full
    # commit SHA and the line must carry a trailing `#` version comment.
    problems: list[str] = []
    if "@" not in value:
        problems.append(
            f"4a: uses: ref must be pinned to a commit SHA "
            f"(no '@<sha>' present): {value}"
        )
    else:
        ref = value.rsplit("@", 1)[1]
        if not _SHA_RE.match(ref):
            problems.append(
                f"4a: uses: ref '{ref}' is not a full 40-char commit SHA "
                f"(docs/security-posture.md gate 4a)"
            )
    if not has_comment:
        problems.append(
            f"4a: uses: '{value}' must carry a trailing "
            f"'# <version>' comment (docs/security-posture.md gate 4a)"
        )
    return problems


def check_workflow(text: str) -> list[str]:
    """Return a list of 4a/4c violation messages for one workflow *text*.

    An empty list means the workflow satisfies both gates.  Messages are
    prefixed with the 1-based line number (or ``file:`` for file-level rules).
    """
    problems: list[str] = []
    has_top_permissions = False

    for lineno, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())

        # Rule 4c: a top-level (indent 0) `permissions:` declaration.
        if indent == 0 and _TOP_PERMISSIONS_RE.match(raw):
            has_top_permissions = True

        # Rule 4c: `permissions: write-all` at workflow or job level.
        if _WRITE_ALL_RE.match(raw):
            problems.append(
                f"{lineno}:4c permissions: write-all is forbidden "
                "(docs/security-posture.md gate 4c)"
            )

        # Rule 4a: every `uses:` value.
        m = _USES_RE.match(raw)
        if m:
            value = m.group(1)
            has_comment = m.group(2) is not None
            for msg in _check_4a_uses(value, has_comment):
                problems.append(f"{lineno}:{msg}")

    if not has_top_permissions:
        problems.append(
            "file:4c workflow must declare a top-level permissions: block "
            "(docs/security-posture.md gate 4c)"
        )

    return problems


def main() -> int:
    workflows_dir = WORKFLOWS_DIR
    if not workflows_dir.is_dir():
        print("No .github/workflows/ directory — nothing to check.")
        return 0

    ok_count = 0
    problems: list[str] = []

    files = sorted(workflows_dir.glob("*.yml")) + sorted(
        workflows_dir.glob("*.yaml")
    )
    for wf in files:
        try:
            text = wf.read_text()
        except OSError as exc:  # pragma: no cover - defensive
            print(f"ERROR: cannot read {wf.name}: {exc}")
            return 2

        violations = check_workflow(text)
        if violations:
            for v in violations:
                problems.append(f"{wf.name}: {v}")
        else:
            ok_count += 1

    if problems:
        print(
            "ERROR: workflow security (4a/4c) violations found:\n  "
            + "\n  ".join(problems)
            + "\n\nPin every `uses:` to a full commit SHA with a `# <version>` "
            "comment, and declare a least-privilege top-level `permissions:` "
            "block (never `write-all`) — see docs/security-posture.md gates "
            "4a/4c.\n"
        )
        return 1

    print(
        f"OK — {ok_count} workflow file(s) checked: every `uses:` is "
        "SHA-pinned (4a) and every workflow declares a least-privilege "
        "top-level permissions: block (4c)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
