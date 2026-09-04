"""Unit tests for the workflow timeout-minutes gate (scripts/check-workflow-timeouts.py).

Covers the core rule (_analyse_job), the structural parse (_parse_jobs), and
the main() happy path / failure edges: a step-running job missing
timeout-minutes, and a job whose timeout exceeds 15 without an inline
justification comment.  Reusable-workflow caller jobs are exempt from
declaring their own timeout-minutes (docs/repo-baseline.md).
"""

from __future__ import annotations

from pathlib import Path

CALLER_WITH_TIMEOUT = """\
name: Test

on: push

jobs:
  caller:
  runs-on: ubuntu-latest
  uses: org/repo/.github/workflows/reusable.yml@main
  timeout-minutes: 15
"""

CALLER_NO_TIMEOUT = """\
name: Test

on: push

jobs:
  caller:
  runs-on: ubuntu-latest
  uses: org/repo/.github/workflows/reusable.yml@main
"""

# Standard GitHub Actions layout: a reusable-workflow caller followed by a
# second job, both with 4-space-indented attributes.  Exercises the parser's
# 4-space attribute handling and consecutive job-header detection.
STANDARD_CALLER_NO_TIMEOUT = """\
name: Test

on:
  push:
    branches: [main]

jobs:
  caller:
    runs-on: ubuntu-latest
    uses: org/repo/.github/workflows/reusable.yml@main
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 5
"""

# A step-running job (no `uses:`) that omits timeout-minutes entirely.
REGULAR_NO_TIMEOUT = """\
name: Test

on: push

jobs:
  build:
    runs-on: ubuntu-latest
"""


def _job(name="caller", timeout_value=None, timeout_line=None, has_job_uses=True):
    return {
        "name": name,
        "timeout_value": timeout_value,
        "timeout_line": timeout_line,
        "has_runs_on": False,
        "has_job_uses": has_job_uses,
    }


def _write_workflow(tmp_path: Path, text: str) -> Path:
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    wf = wf_dir / "test.yml"
    wf.write_text(text)
    return wf


# ---------------------------------------------------------------------------
# _analyse_job: the timeout-minutes rule
# ---------------------------------------------------------------------------


def test_regular_job_missing_timeout_fails(check_workflow_timeouts):
    ok, reason = check_workflow_timeouts._analyse_job(_job(has_job_uses=False))
    assert not ok
    assert "timeout-minutes" in reason


def test_regular_job_within_limit_ok(check_workflow_timeouts):
    ok, _reason = check_workflow_timeouts._analyse_job(
        _job(has_job_uses=False, timeout_value=10, timeout_line="timeout-minutes: 10")
    )
    assert ok


def test_regular_job_at_limit_ok(check_workflow_timeouts):
    ok, _reason = check_workflow_timeouts._analyse_job(
        _job(has_job_uses=False, timeout_value=15, timeout_line="timeout-minutes: 15")
    )
    assert ok


def test_regular_job_above_limit_with_comment_ok(check_workflow_timeouts):
    line = "timeout-minutes: 30  # image build needs extra headroom"
    ok, _reason = check_workflow_timeouts._analyse_job(
        _job(has_job_uses=False, timeout_value=30, timeout_line=line)
    )
    assert ok


def test_regular_job_above_limit_without_comment_fails(check_workflow_timeouts):
    ok, reason = check_workflow_timeouts._analyse_job(
        _job(has_job_uses=False, timeout_value=30, timeout_line="timeout-minutes: 30")
    )
    assert not ok
    assert "comment" in reason


def test_caller_exempt_without_timeout(check_workflow_timeouts):
    ok, _reason = check_workflow_timeouts._analyse_job(_job(timeout_value=None))
    assert ok


def test_caller_exempt_regardless_of_timeout(check_workflow_timeouts):
    # A caller's timeout is ignored by GitHub Actions, so even a caller that
    # happens to carry one is exempt from the >15 justification check.
    ok, _reason = check_workflow_timeouts._analyse_job(
        _job(timeout_value=30, timeout_line="timeout-minutes: 30")
    )
    assert ok


# ---------------------------------------------------------------------------
# _parse_jobs: structural detection of a caller's attributes
# ---------------------------------------------------------------------------


def test_parse_jobs_detects_caller_attrs(check_workflow_timeouts):
    jobs = check_workflow_timeouts._parse_jobs(CALLER_WITH_TIMEOUT)
    assert len(jobs) == 1
    job = jobs[0]
    assert job["name"] == "caller"
    assert job["has_job_uses"] is True
    assert job["has_runs_on"] is True
    assert job["timeout_value"] == 15


def test_parse_jobs_reports_missing_timeout(check_workflow_timeouts):
    jobs = check_workflow_timeouts._parse_jobs(CALLER_NO_TIMEOUT)
    assert len(jobs) == 1
    assert jobs[0]["name"] == "caller"
    assert jobs[0]["has_job_uses"] is True
    assert jobs[0]["timeout_value"] is None


def test_parse_jobs_standard_4space_attributes(check_workflow_timeouts):
    # Job-level attributes at the standard 4-space indent must be attributed
    # to the enclosing job (previously only the flat 2-space form was seen),
    # and consecutive job headers must each be detected as a separate job.
    jobs = check_workflow_timeouts._parse_jobs(STANDARD_CALLER_NO_TIMEOUT)
    assert [j["name"] for j in jobs] == ["caller", "build"]
    caller, build = jobs
    assert caller["has_job_uses"] is True
    assert caller["has_runs_on"] is True
    assert caller["timeout_value"] is None
    assert build["has_job_uses"] is False
    assert build["timeout_value"] == 5


# ---------------------------------------------------------------------------
# main(): end-to-end gate
# ---------------------------------------------------------------------------


def test_main_happy_path(tmp_path, check_workflow_timeouts, monkeypatch):
    _write_workflow(tmp_path, CALLER_WITH_TIMEOUT)
    monkeypatch.setattr(
        check_workflow_timeouts, "WORKFLOWS_DIR", tmp_path / ".github" / "workflows"
    )
    assert check_workflow_timeouts.main() == 0


def test_main_missing_timeout_fails(tmp_path, check_workflow_timeouts, monkeypatch, capsys):
    _write_workflow(tmp_path, REGULAR_NO_TIMEOUT)
    monkeypatch.setattr(
        check_workflow_timeouts, "WORKFLOWS_DIR", tmp_path / ".github" / "workflows"
    )
    assert check_workflow_timeouts.main() == 1
    assert "timeout-minutes" in capsys.readouterr().out


def test_main_caller_exempt(tmp_path, check_workflow_timeouts, monkeypatch):
    # A reusable-workflow caller without timeout-minutes must NOT fail the gate.
    _write_workflow(tmp_path, CALLER_NO_TIMEOUT)
    monkeypatch.setattr(
        check_workflow_timeouts, "WORKFLOWS_DIR", tmp_path / ".github" / "workflows"
    )
    assert check_workflow_timeouts.main() == 0


def test_main_no_workflows_dir(tmp_path, check_workflow_timeouts, monkeypatch):
    monkeypatch.setattr(
        check_workflow_timeouts, "WORKFLOWS_DIR", tmp_path / ".github" / "workflows"
    )
    assert check_workflow_timeouts.main() == 0
