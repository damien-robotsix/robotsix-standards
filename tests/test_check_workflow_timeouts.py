"""Unit tests for the workflow timeout-minutes gate (scripts/check-workflow-timeouts.py).

Covers the core rule (_analyse_job), the structural parse (_parse_jobs), and
the main() happy path / failure edges: a reusable-workflow caller missing
timeout-minutes, and a caller whose timeout exceeds 15 without an inline
justification comment.
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


def test_regular_job_no_timeout_required(check_workflow_timeouts):
    ok, _reason = check_workflow_timeouts._analyse_job(_job(has_job_uses=False))
    assert ok


def test_caller_within_limit_ok(check_workflow_timeouts):
    ok, _reason = check_workflow_timeouts._analyse_job(
        _job(timeout_value=10, timeout_line="timeout-minutes: 10")
    )
    assert ok


def test_caller_at_limit_ok(check_workflow_timeouts):
    ok, _reason = check_workflow_timeouts._analyse_job(
        _job(timeout_value=15, timeout_line="timeout-minutes: 15")
    )
    assert ok


def test_caller_above_limit_with_comment_ok(check_workflow_timeouts):
    line = "timeout-minutes: 30  # called workflow provides its own timing"
    ok, _reason = check_workflow_timeouts._analyse_job(
        _job(timeout_value=30, timeout_line=line)
    )
    assert ok


def test_caller_missing_timeout_fails(check_workflow_timeouts):
    ok, reason = check_workflow_timeouts._analyse_job(_job(timeout_value=None))
    assert not ok
    assert "timeout-minutes" in reason


def test_caller_above_limit_without_comment_fails(check_workflow_timeouts):
    ok, reason = check_workflow_timeouts._analyse_job(
        _job(timeout_value=30, timeout_line="timeout-minutes: 30")
    )
    assert not ok
    assert "comment" in reason


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
    _write_workflow(tmp_path, CALLER_NO_TIMEOUT)
    monkeypatch.setattr(
        check_workflow_timeouts, "WORKFLOWS_DIR", tmp_path / ".github" / "workflows"
    )
    assert check_workflow_timeouts.main() == 1
    assert "timeout-minutes" in capsys.readouterr().out


def test_main_no_workflows_dir(tmp_path, check_workflow_timeouts, monkeypatch):
    monkeypatch.setattr(
        check_workflow_timeouts, "WORKFLOWS_DIR", tmp_path / ".github" / "workflows"
    )
    assert check_workflow_timeouts.main() == 0
