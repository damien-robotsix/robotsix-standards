#!/usr/bin/env python3
"""Check that workflow jobs honour the repo-baseline timeout-minutes rule.

This script is the automated enforcement gate referenced by the
timeout-minutes rule in docs/repo-baseline.md.  It runs in CI on PRs
(see .github/workflows/baseline-check.yml and .github/workflows/ci.yml)
and exits non-zero when a step-running job lacks a `timeout-minutes`
declaration or carries an unexplained ceiling above 15.

Rules enforced (per docs/repo-baseline.md):
  - Every job that runs steps directly MUST declare an explicit
    `timeout-minutes` ceiling, so a hung or runaway job is killed quickly
    instead of consuming the 6-hour GitHub default.
  - A job whose `timeout-minutes` exceeds 15 MUST carry a same-line `#`
    comment explaining why, so the deviation from the 15-minute default is
    auditable.
  - Reusable-workflow caller jobs (job-level `uses:`) are exempt: GitHub
    Actions does not support `timeout-minutes` on a caller job, and the
    ceiling belongs inside the called workflow, where each of its own jobs
    declares `timeout-minutes`.

Exit codes:
  0 — all workflow jobs satisfy the rule
  1 — a step-running job lacks timeout-minutes, or a >15 timeout has no
      explanation
  2 — script error (cannot read a workflow file, etc.)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

_TIMEOUT_RE = re.compile(r"^\s*timeout-minutes:\s*(\d+)\s*(#.*)?$")


def _new_job(name: str) -> dict:
    return {
        "name": name,
        "timeout_value": None,
        "timeout_line": None,
        "has_runs_on": False,
        "has_job_uses": False,
    }


def _apply_attribute(job: dict, line: str) -> None:
    """Record one job-level attribute ``line`` (already stripped) on ``job``."""
    key = line.split(":", 1)[0]
    if key == "timeout-minutes":
        m = _TIMEOUT_RE.match(line)
        if m:
            job["timeout_value"] = int(m.group(1))
            job["timeout_line"] = line
    elif key == "runs-on":
        job["has_runs_on"] = True
    elif key == "uses":
        job["has_job_uses"] = True


def _parse_jobs(text: str) -> list[dict]:
    """Return a lightweight structural parse of each top-level job.

    This is intentionally a grep-based structural scan rather than a full YAML
    parse: jobs have arbitrary names and nested steps, and we only need each
    top-level job's `name`, `runs-on`, `timeout-minutes`, and any job-level
    `uses:` / `with:` attributes.  Only lines inside the top-level `jobs:`
    mapping are considered.  A job header is a bare two-space-indented
    `<job-id>:` key under `jobs:`; its attributes are the following
    four-space-indented keys (standard GitHub Actions layout) or, in the
    legacy flat layout, two-space `key: value` lines written directly under
    the header.  Deeper nesting (steps, `with:`, `env:`, matrices, `on:`
    triggers) is ignored.
    """
    jobs: list[dict] = []
    current: dict | None = None
    in_jobs = False  # the most recent top-level key was `jobs:`

    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Only columns 0-4 can be a top-level key, job header or job
        # attribute; anything deeper is a nested list or mapping we ignore.
        indent = len(raw) - len(raw.lstrip())
        if indent > 4:
            continue

        if indent == 0:
            # A top-level mapping key (workflow `name`, `on`, `jobs`, ...).
            # Job headers only exist directly under `jobs:`, so track that
            # and forget the in-flight job on every top-level key.
            in_jobs = stripped.startswith("jobs:")
            current = None
            continue

        if indent == 2 and in_jobs:
            # Under `jobs:`, a 2-space line is either a job header (a bare
            # `<job-id>:` key) or, in the legacy flat layout, a job attribute
            # (`uses: ...`) written at the same indent as the header.
            key, sep, value = stripped.partition(":")
            if sep and value.strip():
                # `  key: value` — flat-layout job attribute.
                if current is not None:
                    _apply_attribute(current, stripped)
                continue
            # Bare `  <job-id>:` — starts a new job.
            jobs.append(_new_job(key))
            current = jobs[-1]
            continue

        if indent == 4 and in_jobs and current is not None:
            # Standard GitHub Actions layout: job attributes sit at 4-space
            # indent under the header.  Nested blocks (`steps:`, `with:`,
            # `env:`, `if:`, `permissions:`, ...) are deeper and filtered
            # above; only the attributes we track are matched.
            _apply_attribute(current, stripped)
            continue

        # indent 2/4 keys outside `jobs:` (`on:` triggers, `env:`,
        # `permissions:`, `concurrency:`) and indents 1-3/5 are not job
        # structure we track.

    return jobs


def _analyse_job(job: dict) -> tuple[bool, str]:
    """Return (ok, reason) for one job against the timeout-minutes rule."""
    name = job["name"]

    # Reusable-workflow caller jobs are exempt from declaring their own
    # timeout-minutes: GitHub Actions does not support the setting on a caller
    # job, and the ceiling belongs inside the called workflow
    # (docs/repo-baseline.md, "Exception — reusable-workflow caller jobs").
    if job["has_job_uses"]:
        return True, f"{name}: reusable-workflow caller; timeout-minutes exempt"

    # Every job that runs steps directly MUST declare a timeout ceiling.
    if job["timeout_value"] is None:
        return (
            False,
            (
                f"{name}: jobs that run steps MUST declare timeout-minutes "
                "(docs/repo-baseline.md)"
            ),
        )

    if job["timeout_value"] > 15:
        line = job["timeout_line"]
        if not line or "#" not in line.split("timeout-minutes:", 1)[-1]:
            return (
                False,
                (
                    f"{name}: timeout-minutes > 15 requires an inline # comment "
                    "explaining why (docs/repo-baseline.md)"
                ),
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
            "> 15) to every job that runs steps directly — see "
            "docs/repo-baseline.md.\n"
        )
        return 1

    print(
        f"OK — {ok_count} job(s) checked: every step-running job carries an "
        "auditable timeout-minutes."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
