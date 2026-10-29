#!/usr/bin/env python3
"""Check that workflow runner choice matches the repository's visibility.

This script is the enforcement gate for the "Runner choice follows
repository visibility" rule in docs/repo-baseline.md and for gate 4d
(*Runner isolation*) in docs/security-posture.md.  It runs in CI on every
push and PR (the ``runner-visibility-check`` job in
.github/workflows/baseline-check.yml).

Rules enforced:
  - A **public** repository never uses a self-hosted runner.  The gate
    fails (exit 1) when any job's ``runs-on`` — a string, a list of labels,
    a ``{group:, labels:}`` mapping or an expression — names
    ``self-hosted`` or a runner group, or when a reusable-workflow caller
    passes ``self-hosted`` through a ``runs-on`` / ``runner`` input.  On a
    public repo a self-hosted runner executes code from any fork pull
    request on the host, so this is fail-closed from day one (no
    warning-first period).
  - A **private** repository should run every job on ``self-hosted``
    (free-tier rule).  A private repo job on a GitHub-hosted runner is
    reported as a ``::warning::`` annotation only; it never fails the gate.

Visibility is read from ``--private true|false`` (CI passes
``${{ github.event.repository.private }}``) or, failing that, the
``REPO_PRIVATE`` environment variable.  An unknown visibility fails closed
(exit 2): the gate cannot prove a public repo is safe without it.

Exit codes:
  0 — runner choice matches visibility
  1 — a public repository targets a self-hosted runner
  2 — visibility unknown, or a workflow file could not be read or parsed
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from _workflow_utils import WORKFLOWS_DIR, iter_workflow_files, read_workflow

SELF_HOSTED = "self-hosted"
# Reusable-workflow inputs that select the runner of the called workflow.
RUNNER_INPUTS = ("runs-on", "runs_on", "runner", "runner-label", "runner-labels")
RULE_REF = "docs/repo-baseline.md#runner-choice-follows-repository-visibility"


def parse_visibility(value: str | None) -> bool | None:
    """Return True for private, False for public, None when unknown."""
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in ("true", "1", "yes", "private"):
        return True
    if normalized in ("false", "0", "no", "public"):
        return False
    return None


def _flatten(value: Any) -> str:
    """Serialize *value* (string, list, mapping) to one searchable string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(f"{k} {_flatten(v)}" for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return " ".join(_flatten(v) for v in value)
    return str(value)


def targets_self_hosted(runs_on: Any, strategy: Any = None) -> bool:
    """Return True when a ``runs-on`` value can select a self-hosted runner.

    Matches the ``self-hosted`` label anywhere in a string, label list or
    expression; any ``group:`` key (runner groups exist only for
    self-hosted runners); and a ``matrix.*`` reference whose matrix lists
    ``self-hosted``.
    """
    if runs_on is None:
        return False
    if isinstance(runs_on, dict) and "group" in runs_on:
        return True
    flat = _flatten(runs_on)
    if SELF_HOSTED in flat.lower():
        return True
    if "matrix." in flat and strategy is not None:
        return SELF_HOSTED in _flatten(strategy).lower()
    return False


def job_runner_findings(job_id: str, job: Any) -> tuple[bool, bool]:
    """Return ``(self_hosted, github_hosted)`` for one job.

    ``self_hosted`` is True when the job (inline ``runs-on`` or a
    reusable-workflow runner input) can target a self-hosted runner.
    ``github_hosted`` is True when the job explicitly or implicitly runs on a
    GitHub-hosted runner (an inline job without ``self-hosted``, or a
    reusable-workflow caller that passes no self-hosted runner input).
    """
    if not isinstance(job, dict):
        return False, False
    if "uses" in job:
        with_block = job.get("with") or {}
        if not isinstance(with_block, dict):
            return False, True
        self_hosted = any(
            targets_self_hosted(with_block.get(key)) for key in RUNNER_INPUTS
        )
        return self_hosted, not self_hosted
    runs_on = job.get("runs-on")
    self_hosted = targets_self_hosted(runs_on, job.get("strategy"))
    return self_hosted, runs_on is not None and not self_hosted


def scan_workflow(text: str) -> list[tuple[str, bool, bool]]:
    """Return ``(job_id, self_hosted, github_hosted)`` for every job in *text*.

    Raises ``yaml.YAMLError`` when *text* is not valid YAML.
    """
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        return []
    jobs = data.get("jobs")
    if not isinstance(jobs, dict):
        return []
    return [
        (str(job_id), *job_runner_findings(str(job_id), job))
        for job_id, job in jobs.items()
    ]


def main(
    argv: list[str] | None = None,
    workflows_dir: Path = WORKFLOWS_DIR,
) -> int:
    """Check every workflow job's runner against the repository visibility."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--private",
        default=None,
        help="repository visibility: true (private) or false (public); "
        "defaults to $REPO_PRIVATE",
    )
    args = parser.parse_args(argv)
    raw = args.private if args.private is not None else os.environ.get("REPO_PRIVATE")
    private = parse_visibility(raw)
    if private is None:
        print(
            f"::error::repository visibility is unknown ({raw!r}); pass "
            "--private true|false (CI: ${{ github.event.repository.private }}). "
            "Failing closed."
        )
        return 2

    violations: list[str] = []
    hosted_warnings: list[str] = []
    for wf in iter_workflow_files(workflows_dir):
        text = read_workflow(wf)
        if text is None:
            return 2
        try:
            jobs = scan_workflow(text)
        except yaml.YAMLError as exc:
            print(f"::error::{wf.name}: cannot parse workflow YAML: {exc}")
            return 2
        for job_id, self_hosted, github_hosted in jobs:
            if not private and self_hosted:
                violations.append(f"{wf.name}: {job_id}")
            elif private and github_hosted:
                hosted_warnings.append(f"{wf.name}: {job_id}")

    for finding in hosted_warnings:
        print(
            f"::warning::{finding}: private repository job runs on a "
            f"GitHub-hosted runner; use runs-on: self-hosted ({RULE_REF})"
        )

    if violations:
        for finding in violations:
            print(
                f"::error::{finding}: public repository job targets a "
                "self-hosted runner — fork pull requests would execute on the "
                f"host ({RULE_REF})"
            )
        print(
            f"ERROR: {len(violations)} job(s) on a public repository target a "
            "self-hosted runner. Move them to a GitHub-hosted runner."
        )
        return 1

    visibility = "private" if private else "public"
    print(f"Runner choice matches repository visibility ({visibility}): OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
