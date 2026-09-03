"""Unit tests for the py.typed wheel guard gate (scripts/check-py-typed-guard.py).

Covers type-aware detection (Typing :: Typed classifier and py.typed marker),
guard detection (installed type-check and wheel-content assertion), and the
main() happy path / failure edges: a typed package without any guard in CI.
"""

from __future__ import annotations

from pathlib import Path

WHEEL_ASSERTION = (
    "run: python -c \"import zipfile; "
    "assert 'py.typed' in zipfile.ZipFile('dist/x.whl').namelist()\"\n"
)
INSTALLED_TYPECHECK = "run: uv pip install dist/*.whl\nrun: mypy src\n"


def _write_typed_pyproject(tmp_path: Path) -> Path:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('classifiers = ["Typing :: Typed"]\n')
    return pyproject


def _write_workflow(tmp_path: Path, text: str) -> Path:
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    wf = wf_dir / "ci.yml"
    wf.write_text(text)
    return wf


# ---------------------------------------------------------------------------
# Type-aware detection
# ---------------------------------------------------------------------------


def test_typed_classifier_detected(tmp_path, check_py_typed_guard):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('classifiers = ["Typing :: Typed"]\n')
    assert check_py_typed_guard._has_typed_classifier(pyproject) is True


def test_typed_classifier_missing(tmp_path, check_py_typed_guard):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("classifiers = ['Programming Language :: Python :: 3']\n")
    assert check_py_typed_guard._has_typed_classifier(pyproject) is False


def test_typed_classifier_no_pyproject(tmp_path, check_py_typed_guard):
    assert check_py_typed_guard._has_typed_classifier(tmp_path / "pyproject.toml") is False


def test_py_typed_marker_found(tmp_path, check_py_typed_guard):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "py.typed").write_text("")
    assert check_py_typed_guard._has_py_typed_marker(tmp_path) is True


def test_py_typed_marker_only_in_excluded_dir(tmp_path, check_py_typed_guard):
    (tmp_path / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / ".venv" / "lib" / "py.typed").write_text("")
    assert check_py_typed_guard._has_py_typed_marker(tmp_path) is False


def test_py_typed_marker_absent(tmp_path, check_py_typed_guard):
    assert check_py_typed_guard._has_py_typed_marker(tmp_path) is False


# ---------------------------------------------------------------------------
# Guard detection
# ---------------------------------------------------------------------------


def test_installed_typecheck_detected(check_py_typed_guard):
    assert check_py_typed_guard._workflow_file_has_installed_typecheck(
        INSTALLED_TYPECHECK
    ) is True


def test_source_only_mypy_not_installed_typecheck(check_py_typed_guard):
    assert check_py_typed_guard._workflow_file_has_installed_typecheck(
        "run: mypy src\n"
    ) is False


def test_wheel_content_assertion_detected(check_py_typed_guard):
    assert check_py_typed_guard._workflow_file_has_wheel_content_assertion(
        WHEEL_ASSERTION
    ) is True


def test_wheel_content_assertion_missing(check_py_typed_guard):
    assert check_py_typed_guard._workflow_file_has_wheel_content_assertion(
        "run: mypy src\n"
    ) is False


def test_gather_workflow_texts_sorted(tmp_path, check_py_typed_guard):
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "b.yml").write_text("jobs: {}\n")
    (wf_dir / "a.yml").write_text("jobs: {}\n")
    result = check_py_typed_guard._gather_workflow_texts(tmp_path)
    assert [p.name for p, _ in result] == ["a.yml", "b.yml"]


def test_gather_workflow_texts_missing_dir(tmp_path, check_py_typed_guard):
    assert check_py_typed_guard._gather_workflow_texts(tmp_path) == []


# ---------------------------------------------------------------------------
# main(): end-to-end gate
# ---------------------------------------------------------------------------


def test_main_not_typed(tmp_path, check_py_typed_guard, monkeypatch, capsys):
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    monkeypatch.setattr(check_py_typed_guard, "REPO_ROOT", tmp_path)
    assert check_py_typed_guard.main() == 0
    assert "nothing to check" in capsys.readouterr().out


def test_main_typed_no_workflows_dir(tmp_path, check_py_typed_guard, monkeypatch, capsys):
    _write_typed_pyproject(tmp_path)
    monkeypatch.setattr(check_py_typed_guard, "REPO_ROOT", tmp_path)
    assert check_py_typed_guard.main() == 1
    assert "No .github/workflows" in capsys.readouterr().out


def test_main_typed_without_guard_fails(tmp_path, check_py_typed_guard, monkeypatch, capsys):
    _write_typed_pyproject(tmp_path)
    _write_workflow(tmp_path, "name: CI\non: push\n")
    monkeypatch.setattr(check_py_typed_guard, "REPO_ROOT", tmp_path)
    assert check_py_typed_guard.main() == 1
    assert "neither an installed type-check step" in capsys.readouterr().out


def test_main_typed_with_wheel_guard_ok(tmp_path, check_py_typed_guard, monkeypatch, capsys):
    _write_typed_pyproject(tmp_path)
    _write_workflow(tmp_path, WHEEL_ASSERTION)
    monkeypatch.setattr(check_py_typed_guard, "REPO_ROOT", tmp_path)
    assert check_py_typed_guard.main() == 0
    assert "Guard satisfied" in capsys.readouterr().out


def test_main_typed_with_installed_typecheck_ok(
    tmp_path, check_py_typed_guard, monkeypatch, capsys
):
    _write_typed_pyproject(tmp_path)
    _write_workflow(tmp_path, INSTALLED_TYPECHECK)
    monkeypatch.setattr(check_py_typed_guard, "REPO_ROOT", tmp_path)
    assert check_py_typed_guard.main() == 0
    assert "Guard satisfied" in capsys.readouterr().out
