"""Tests for scripts/check-runner-visibility.py."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

import pytest


def _write(tmp_path: Path, body: str, name: str = "ci.yml") -> Path:
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / name).write_text(body)
    return wf_dir


INLINE_SELF_HOSTED = """\
on: push
jobs:
  build:
    runs-on: self-hosted
    steps:
      - run: echo hi
"""

GITHUB_HOSTED = """\
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo hi
"""


@pytest.mark.parametrize(
    "runs_on",
    [
        "self-hosted",
        ["self-hosted", "linux"],
        {"group": "home-runners"},
        {"labels": ["self-hosted"]},
        "${{ github.event_name == 'push' && 'self-hosted' || 'ubuntu-latest' }}",
    ],
)
def test_targets_self_hosted_shapes(
    check_runner_visibility: ModuleType, runs_on: object
) -> None:
    assert check_runner_visibility.targets_self_hosted(runs_on)


@pytest.mark.parametrize("runs_on", ["ubuntu-latest", ["ubuntu-24.04"], None])
def test_github_hosted_shapes(
    check_runner_visibility: ModuleType, runs_on: object
) -> None:
    assert not check_runner_visibility.targets_self_hosted(runs_on)


def test_matrix_reference(check_runner_visibility: ModuleType) -> None:
    strategy = {"matrix": {"os": ["ubuntu-latest", "self-hosted"]}}
    assert check_runner_visibility.targets_self_hosted("${{ matrix.os }}", strategy)
    assert not check_runner_visibility.targets_self_hosted(
        "${{ matrix.os }}", {"matrix": {"os": ["ubuntu-latest"]}}
    )


def test_public_inline_self_hosted_fails(
    check_runner_visibility: ModuleType, tmp_path: Path
) -> None:
    wf_dir = _write(tmp_path, INLINE_SELF_HOSTED)
    assert check_runner_visibility.main(["--private", "false"], wf_dir) == 1


def test_public_reusable_input_self_hosted_fails(
    check_runner_visibility: ModuleType, tmp_path: Path
) -> None:
    wf_dir = _write(
        tmp_path,
        """\
on: push
jobs:
  ci:
    uses: owner/repo/.github/workflows/ci.yml@0123456789abcdef0123456789abcdef01234567 # v1
    with:
      runs-on: self-hosted
""",
    )
    assert check_runner_visibility.main(["--private", "false"], wf_dir) == 1


def test_public_github_hosted_passes(
    check_runner_visibility: ModuleType, tmp_path: Path
) -> None:
    wf_dir = _write(tmp_path, GITHUB_HOSTED)
    assert check_runner_visibility.main(["--private", "false"], wf_dir) == 0


def test_private_self_hosted_passes(
    check_runner_visibility: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    wf_dir = _write(tmp_path, INLINE_SELF_HOSTED)
    assert check_runner_visibility.main(["--private", "true"], wf_dir) == 0
    assert "::warning::" not in capsys.readouterr().out


def test_private_github_hosted_warns_only(
    check_runner_visibility: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    wf_dir = _write(tmp_path, GITHUB_HOSTED)
    assert check_runner_visibility.main(["--private", "true"], wf_dir) == 0
    assert "::warning::" in capsys.readouterr().out


def test_unknown_visibility_fails_closed(
    check_runner_visibility: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("REPO_PRIVATE", raising=False)
    wf_dir = _write(tmp_path, GITHUB_HOSTED)
    assert check_runner_visibility.main([], wf_dir) == 2
    assert check_runner_visibility.main(["--private", ""], wf_dir) == 2


def test_env_visibility(
    check_runner_visibility: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REPO_PRIVATE", "false")
    wf_dir = _write(tmp_path, INLINE_SELF_HOSTED)
    assert check_runner_visibility.main([], wf_dir) == 1


def test_invalid_yaml_exits_2(
    check_runner_visibility: ModuleType, tmp_path: Path
) -> None:
    wf_dir = _write(tmp_path, "jobs: [unclosed\n")
    assert check_runner_visibility.main(["--private", "false"], wf_dir) == 2


def test_missing_workflows_dir_passes(
    check_runner_visibility: ModuleType, tmp_path: Path
) -> None:
    assert (
        check_runner_visibility.main(["--private", "false"], tmp_path / "none") == 0
    )


def test_this_repo_passes_as_public(check_runner_visibility: ModuleType) -> None:
    assert check_runner_visibility.main(["--private", "false"]) == 0
