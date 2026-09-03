"""Shared fixtures for the CI-gate script unit tests.

The three gating scripts under scripts/ use dashes in their filenames
(check-toc-sync.py, check-workflow-timeouts.py, check-py-typed-guard.py),
which are not valid Python module identifiers, so each is loaded by file
path via importlib instead of a plain ``import``.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


def _load_script(filename: str, module_name: str) -> ModuleType:
    path = SCRIPTS_DIR / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def check_toc_sync() -> ModuleType:
    return _load_script("check-toc-sync.py", "check_toc_sync")


@pytest.fixture
def check_workflow_timeouts() -> ModuleType:
    return _load_script(
        "check-workflow-timeouts.py", "check_workflow_timeouts"
    )


@pytest.fixture
def check_py_typed_guard() -> ModuleType:
    return _load_script("check-py-typed-guard.py", "check_py_typed_guard")
