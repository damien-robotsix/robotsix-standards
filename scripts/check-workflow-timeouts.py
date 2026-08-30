#!/usr/bin/env python3
"""Check that workflow jobs carrying a `uses:` reusable-workflow caller satisfy
the repo-baseline timeout-minutes rule.

This script is the automated enforcement gate referenced by the
reusable-workflow timeout exception in docs/repo-baseline.md.  It runs in CI
on PRs (see .github/workflows/baseline-check.yml and .github/workflows/ci.yml)
and exits non-zero when a caller job lacks a `timeout-minutes` declaration.

Rules enforced (per docs/repo-baseline.md):
  - A job whose steps call a reusable workflow via `uses:` (a reusable-workflow
    caller) MUST declare `timeout-minutes`, because a reusable workflow does
    not inherit the caller's own step timeout and could otherwise run up to
    GitHub's 6-hour job limit.
  - A job whose `timeout-minutes` exceeds 15 MUST carry a same-line `#`
    comment explaining why, so the deviation from the 15-minute default is
    auditable.

Exit codes:
  0 — all workflow jobs satisfy the rule
  1 — a caller job lacks timeout-minutes, or a >15 timeout has no explanation
  2 — script error (cannot read a workflow file, etc.)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

_TIMEOUT_RE = re.compile(r"^\s*timeout-minutes:\s*(\d+)\s*(#.*)?$")

# Comments that document why the called workflow provides its own timing
# and therefore needs no timeout-minutes on the caller job.
_EXCEPTION_COMMENTS = (
    "called workflow",
    "reusable workflow",
    "reusable-workflow",
    "timeout",
)


def _parse_jobs(text: str) -> list[dict]:
    """Return a lightweight structural parse of each top-level job.

    This is intentionally a grep-based structural scan rather than a full YAML
    parse: jobs have arbitrary names and nested steps, and we only need each
    top-level job's `name`, `runs-on`, `timeout-minutes`, and any job-level
    `uses:` / `with:` attributes.  A line is treated as starting a new job when
    it is a two-space-indented (top-level) key whose previous non-blank line
    was below the `jobs:` mapping (or the top of the file).
    """
    jobs: list[dict] = []
    current: dict | None = None
    prev: str = ""

    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            prev = stripped
            continue

        # Only columns 0-3 indentation can be a job/step/attribute we care
        # about; anything deeper is a nested list or mapping we ignore.
        indent = len(raw) - len(raw.lstrip())
        if indent > 3:
            prev = stripped
            continue

        if indent == 0 and stripped.endswith(":"):
            # A top-level key (workflow `name`, `on`, `jobs`, ...); a job
            # cannot appear directly at column 0, so only reset the "prev"
            # bookkeeping that decides whether a 2-space key starts a job.
            prev = stripped
            continue

        if indent == 2 and not stripped.startswith("-"):
            # '  <key>: <value>' — inside `jobs:` this is a job's attribute
            # (maps: {timeout-minutes, runs-on, ...}); at the top level of a
            # step it would be `- ...` (filtered above) or a nested key we
            # treat as an attribute.  A job attribute is only attributed to
            # the current job.
            key = stripped.split(":", 1)[0]
            value = stripped.split(":", 1)[1].strip() if ":" in stripped else ""

            # A bare top-level key inside `jobs:` is a *new job header* —
            # e.g. `  docs:` with no value (job name), or `  job-id:`.
            if value == "" and prev.endswith(":"):
                jobs.append(
                    {"name": key, "timeout_value": None, "timeout_line": None,
                     "has_runs_on": False, "has_job_uses": False}
                )
                current = jobs[-1]
                prev = stripped
                continue

            if current is None:
                prev = stripped
                continue

            if key == "timeout-minutes":
                m = _TIMEOUT_RE.match(stripped)
                if m:
                    current["timeout_value"] = int(m.group(1))
                    current["timeout_line"] = stripped
            elif key == "runs-on":
                current["has_runs_on"] = True
            elif key == "uses":
                current["has_job_uses"] = True
            prev = stripped
            continue

        # indent 0 non-key (unlikely) or indent 2/3 list item / attribute —
        # step-level `- uses:` lines and `  with:` keys are filtered above.
        prev = stripped

    return jobs


def _analyse_job(job: dict) -> tuple[bool, str]:
    """Return (ok, reason) for one job against the timeout-minutes rule."""
    name = job["name"]

    # Only jobs that call a reusable workflow via job-level `uses:` are
    # required to declare a timeout.  Regular jobs (no `uses:`) are free to
    # rely on the platform default, exactly as the exception documents.
    if not job["has_job_uses"]:
        return True, f"{name}: regular job, no timeout required"

    if job["timeout_value"] is None:
        return (
            False,
            f"{name}: reusable-workflow caller jobs MUST declare "
            "timeout-minutes (docs/repo-baseline.md)",
        )

    if job["timeout_value"] > 15:
        line = job["timeout_line"]
        if not line or "#" not in line.split("timeout-minutes:", 1)[-1]:
            return (
                False,
                f"{name}: timeout-minutes > 15 requires an inline # comment "
                "explaining why (docs/repo-baseline.md)",
            )

    return True, f"{name}: timeout-minutes OK"


def main() -> int:
    workflows_dir = WORKFLOWS_DIR
    if not workflows_dir.is_dir():
        print("No .github/workflows/ directory — nothing to check.")
        return 0

    ok_count = 0
    problems: list[str] = []

    for wf in sorted(workflows_dir.glob("*.yml")):
        try:
            text = wf.read_text()
        except OSError as exc:  # pragma: no cover - defensive
            print(f"ERROR: cannot read {wf.name}: {exc}")
            return 2

        for job in _parse_jobs(text):
            ok, reason = _analyse_job(job)
            if ok:
                ok_count += 1
            else:
                problems.append(f"{wf.name}: {reason}")

    if problems:
        print(
            "ERROR: actionable timeout-minutes violations found:\n  "
            + "\n  ".join(problems)
            + "\n\nAdd a `timeout-minutes` (with an inline # comment when "
            "> 15) to every job\nthat calls a reusable workflow via `uses:` — "
            "see docs/repo-baseline.md.\n"
        )
        return 1

    print(
        f"OK — {ok_count} job(s) checked: every reusable-workflow caller "
        "carries timeout-minutes."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
