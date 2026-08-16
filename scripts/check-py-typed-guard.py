#!/usr/bin/env python3
"""Check that type-aware Python packages have CI enforcement for the py.typed wheel marker.

This script is the automated enforcement gate referenced by the
py.typed wheel guard standard (docs/py-typed-wheel-guard.md).  It is
intended to run in CI on PRs and exit non-zero when a PEP 561-typed
package lacks both the installed type-check and the wheel-content
assertion in its CI workflows.

Detection of a type-aware package (either is sufficient):
- pyproject.toml declares the "Typing :: Typed" trove classifier
- A py.typed marker file exists anywhere in the repository

Required CI guards (at least one must be found in a workflow YAML):
- **Installed type-check:** the workflow builds a wheel, installs it
  in a clean environment, and runs mypy or pyright against the
  installed package.
- **Wheel-content assertion:** the workflow unzips (or inspects) the
  built wheel and explicitly asserts that a py.typed path exists
  inside it.

Exit codes:
  0 — no typed package, or the typed package has the required guard
  1 — typed package found but no guard is present
  2 — script error (cannot read files, etc.)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Detection: is this repo a type-aware Python package?
# ---------------------------------------------------------------------------

_TYPED_CLASSIFIER_RE = re.compile(r"\bTyping\s*::\s*Typed\b")


def _has_typed_classifier(pyproject: Path) -> bool:
    """Return True if pyproject.toml declares the Typing :: Typed classifier."""
    if not pyproject.exists():
        return False
    text = pyproject.read_text()
    return bool(_TYPED_CLASSIFIER_RE.search(text))


# Directories that should never be scanned for a project's own py.typed marker.
# These contain third-party packages, build artifacts, or tool caches whose
# py.typed files belong to other packages — not the repository itself.
_EXCLUDE_DIRS = {".venv", "venv", ".tox", "__pycache__", "node_modules",
                 ".git", "site-packages", "dist", "build", "site", ".mypy_cache",
                 ".pytest_cache", ".ruff_cache"}


def _has_py_typed_marker(root: Path) -> bool:
    """Return True if any py.typed file exists in the repository source tree.

    Excludes virtualenv, build, and cache directories whose py.typed
    files belong to third-party packages rather than the repo itself.
    """
    for candidate in root.rglob("py.typed"):
        parts = set(candidate.relative_to(root).parts)
        if parts & _EXCLUDE_DIRS:
            continue
        return True
    return False


# ---------------------------------------------------------------------------
# Guard detection: does the CI workflow contain the required assertion?
# ---------------------------------------------------------------------------

def _workflow_file_has_installed_typecheck(text: str) -> bool:
    """Return True if the workflow type-checks an *installed* package.

    Looks for patterns that suggest a wheel is installed into an
    isolated environment and then mypy/pyright is run against it —
    as opposed to running mypy against the source tree directly.
    """
    # Wheel install context
    has_install = bool(
        re.search(r"(?:uv\s+)?pip\s+install\s+.*\.whl", text)
        or re.search(r"install.*dist/", text)
    )
    # Type-check after install (mypy/pyright in same job)
    has_typecheck = bool(re.search(r"\bmypy\b|\bpyright\b", text))
    return has_install and has_typecheck


def _workflow_file_has_wheel_content_assertion(text: str) -> bool:
    """Return True if the workflow explicitly checks for py.typed inside a wheel."""
    # Must mention both py.typed and zipfile (or similar archive inspection)
    has_py_typed = bool(re.search(r"py\.typed", text))
    has_zip_inspection = bool(
        re.search(r"zipfile|ZipFile|namelist|unzip\s+-l", text)
    )
    return has_py_typed and has_zip_inspection


def _gather_workflow_texts(root: Path) -> list[tuple[Path, str]]:
    """Return (path, content) for every .yml file under .github/workflows/."""
    workflows_dir = root / ".github" / "workflows"
    if not workflows_dir.is_dir():
        return []
    result: list[tuple[Path, str]] = []
    for wf in sorted(workflows_dir.glob("*.yml")):
        result.append((wf, wf.read_text()))
    return result


# ---------------------------------------------------------------------------
# Main check
# ---------------------------------------------------------------------------


def main() -> int:
    root = REPO_ROOT

    # 1. Is this a type-aware package?
    pyproject = root / "pyproject.toml"
    is_typed = _has_typed_classifier(pyproject) or _has_py_typed_marker(root)

    if not is_typed:
        print("Not a type-aware package — nothing to check.")
        return 0

    print("Type-aware package detected — checking CI workflow guards ...")

    # 2. Scan workflow files
    workflows = _gather_workflow_texts(root)
    if not workflows:
        print(
            "ERROR: No .github/workflows/*.yml files found — "
            "a typed package must have at least one CI workflow."
        )
        return 1

    installed_check_found = False
    wheel_assertion_found = False

    for wf_path, wf_text in workflows:
        if _workflow_file_has_installed_typecheck(wf_text):
            installed_check_found = True
            print(f"  ✓ {wf_path.name}: installed type-check detected")
        if _workflow_file_has_wheel_content_assertion(wf_text):
            wheel_assertion_found = True
            print(f"  ✓ {wf_path.name}: wheel-content assertion detected")

    if installed_check_found or wheel_assertion_found:
        print("Guard satisfied — no action required.")
        return 0

    print(
        "\nERROR: This repository is a type-aware Python package but its CI "
        "workflows contain\nneither an installed type-check step nor a "
        "wheel-content assertion for the py.typed\nmarker.  At least one of "
        "these guards is required by the py.typed wheel guard\nstandard "
        "(docs/py-typed-wheel-guard.md).\n\n"
        "To fix, add one of the following to your CI workflow:\n"
        "  - A wheel-content assertion (zipfile check for py.typed inside "
        "the built wheel)\n"
        "  - An installed type-check step (build wheel, install in clean "
        "venv, run mypy/pyright)\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
