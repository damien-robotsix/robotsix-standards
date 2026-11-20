"""Unit tests for the single-source config gate (scripts/check-config-single-source.py).

The config standard (docs/config-standard.md §1) mandates that a deployable
component's config values come from one JSON file — no environment overlay and
no ``ROBOTSIX_*`` value variables; only ``ROBOTSIX_CONFIG_FILE`` and
``ROBOTSIX_CONFIG_MAX_VERSIONS`` exist in the namespace, each resolved exactly
once in a config bootstrap (docs/env-config-bootstrap.md).  This gate makes
that MUST machine-checkable: Detection 1 flags any ``ROBOTSIX_*`` env read
outside the two allowed vars; Detection 2 flags an allowed var read at ≥2
call sites.  These tests cover the violation cases (unknown value var,
duplicate read), the happy paths (allowed vars, single read), the pragma
exemption (with and without a reason), and the false-positive edges (comments,
docstrings, plain string literals).
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import ModuleType


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _findings_vars(check_config_single_source: ModuleType, path: Path) -> list[str]:
    """Return the vars flagged by Detection 1 (scan_file) for one file."""
    findings = check_config_single_source.scan_file(path)
    return [finding.var for finding in findings]


# --- Detection 1: env overlay (ROBOTSIX_* value variables) ---


def test_unknown_robotsix_value_var_is_flagged(
    check_config_single_source: ModuleType, tmp_path: Path
) -> None:
    # All four matched call-site forms yield a finding; the same var read via
    # two forms is flagged once per read.
    source = """\
import os
from os import getenv

LOG_LEVEL = os.getenv("ROBOTSIX_LOG_LEVEL")
PORT = os.environ["ROBOTSIX_PORT"]
LEVEL = os.environ.get("ROBOTSIX_LOG_LEVEL")
FOO = getenv("ROBOTSIX_FOO")
"""
    path = _write(tmp_path, "probe.py", source)
    assert _findings_vars(check_config_single_source, path) == [
        "ROBOTSIX_LOG_LEVEL",
        "ROBOTSIX_PORT",
        "ROBOTSIX_LOG_LEVEL",
        "ROBOTSIX_FOO",
    ]


def test_allowed_vars_are_not_flagged_by_detection_1(
    check_config_single_source: ModuleType, tmp_path: Path
) -> None:
    source = """\
import os

path = os.getenv("ROBOTSIX_CONFIG_FILE")
max_versions = os.getenv("ROBOTSIX_CONFIG_MAX_VERSIONS")
"""
    assert _findings_vars(check_config_single_source, _write(tmp_path, "probe.py", source)) == []


def test_non_robotsix_env_read_is_not_flagged(
    check_config_single_source: ModuleType, tmp_path: Path
) -> None:
    # e.g. check-runner-visibility.py reads os.environ.get("REPO_PRIVATE") —
    # outside the ROBOTSIX_* namespace, so it must never be flagged.
    source = """\
import os

private = os.environ.get("REPO_PRIVATE")
ci = os.getenv("CI")
"""
    assert _findings_vars(check_config_single_source, _write(tmp_path, "probe.py", source)) == []


def test_pragma_with_reason_exempts_read(
    check_config_single_source: ModuleType, tmp_path: Path
) -> None:
    source = (
        "import os\n"
        'x = os.getenv("ROBOTSIX_LOG_LEVEL")  # config-single-source: bootstrap only\n'
    )
    assert _findings_vars(check_config_single_source, _write(tmp_path, "probe.py", source)) == []


def test_pragma_without_reason_does_not_exempt(
    check_config_single_source: ModuleType, tmp_path: Path
) -> None:
    source = (
        "import os\n"
        'x = os.getenv("ROBOTSIX_LOG_LEVEL")  # config-single-source:\n'
        'y = os.getenv("ROBOTSIX_PORT")  # config-single-source:   \n'
    )
    vars_found = _findings_vars(check_config_single_source, _write(tmp_path, "probe.py", source))
    assert sorted(vars_found) == ["ROBOTSIX_LOG_LEVEL", "ROBOTSIX_PORT"]


def test_pragma_inside_string_literal_has_no_effect(
    check_config_single_source: ModuleType, tmp_path: Path
) -> None:
    source = (
        "import os\n"
        'x = os.getenv("ROBOTSIX_LOG_LEVEL")  # comment\n'
        'LABEL = "# config-single-source: not a real pragma"\n'
    )
    assert _findings_vars(check_config_single_source, _write(tmp_path, "probe.py", source)) == [
        "ROBOTSIX_LOG_LEVEL"
    ]


def test_comment_and_string_references_are_not_flagged(
    check_config_single_source: ModuleType, tmp_path: Path
) -> None:
    # A ROBOTSIX_* name in a whole-line comment, in a plain string literal, or
    # inside a docstring is prose, not an env-read call site.
    source = '''\
# ROBOTSIX_LOG_LEVEL is no longer read here
LABEL = "ROBOTSIX_CONFIG_FILE"
DOC = """os.getenv("ROBOTSIX_PORT") inside a docstring"""
'''
    assert _findings_vars(check_config_single_source, _write(tmp_path, "probe.py", source)) == []


def test_scratch_reads_derive_var_only_from_literal(
    check_config_single_source: ModuleType, tmp_path: Path
) -> None:
    # A non-literal argument (a variable holding the var name) is not a
    # string-literal call site and is out of scope.
    source = """\
import os

name = "ROBOTSIX_LOG_LEVEL"
x = os.getenv(name)
"""
    assert _findings_vars(check_config_single_source, _write(tmp_path, "probe.py", source)) == []


# --- Detection 2: resolve once ---


def test_allowed_var_read_once_has_no_resolve_once_finding(
    check_config_single_source: ModuleType, tmp_path: Path
) -> None:
    path = _write(tmp_path, "probe.py", 'import os\npath = os.getenv("ROBOTSIX_CONFIG_FILE")\n')
    assert check_config_single_source.resolve_once_findings([path]) == []


def test_allowed_var_read_twice_in_one_file_is_flagged(
    check_config_single_source: ModuleType, tmp_path: Path
) -> None:
    source = """\
import os

path = os.getenv("ROBOTSIX_CONFIG_FILE")
path2 = os.getenv("ROBOTSIX_CONFIG_FILE")
"""
    path = _write(tmp_path, "probe.py", source)
    findings = check_config_single_source.resolve_once_findings([path])
    assert [finding.var for finding in findings] == ["ROBOTSIX_CONFIG_FILE"]
    assert findings[0].count == 2


def test_allowed_var_read_in_two_files_is_flagged(
    check_config_single_source: ModuleType, tmp_path: Path
) -> None:
    a = _write(tmp_path, "a.py", 'import os\nx = os.getenv("ROBOTSIX_CONFIG_FILE")\n')
    b = _write(tmp_path, "b.py", 'import os\nx = os.getenv("ROBOTSIX_CONFIG_FILE")\n')
    findings = check_config_single_source.resolve_once_findings([a, b])
    assert [finding.var for finding in findings] == ["ROBOTSIX_CONFIG_FILE"]
    assert findings[0].count == 2


def test_pragma_exempts_read_from_resolve_once_count(
    check_config_single_source: ModuleType, tmp_path: Path
) -> None:
    source = (
        "import os\n"
        'x = os.getenv("ROBOTSIX_CONFIG_FILE")\n'
        'y = os.getenv("ROBOTSIX_CONFIG_FILE")  # config-single-source: CI-only fallback\n'
    )
    path = _write(tmp_path, "probe.py", source)
    assert check_config_single_source.resolve_once_findings([path]) == []


def test_two_reads_on_same_line_are_one_call_site(
    check_config_single_source: ModuleType, tmp_path: Path
) -> None:
    source = (
        "import os\n"
        'x = os.getenv("ROBOTSIX_CONFIG_FILE"); y = os.getenv("ROBOTSIX_CONFIG_FILE")\n'
    )
    path = _write(tmp_path, "probe.py", source)
    assert check_config_single_source.resolve_once_findings([path]) == []


# --- main() / integration ---


def test_main_exit_codes(check_config_single_source: ModuleType, tmp_path: Path) -> None:
    clean = _write(tmp_path, "clean.py", 'import os\npath = os.getenv("ROBOTSIX_CONFIG_FILE")\n')
    dirty = _write(tmp_path, "dirty.py", 'import os\nlevel = os.getenv("ROBOTSIX_LOG_LEVEL")\n')
    dup = _write(
        tmp_path,
        "dup.py",
        'import os\n'
        'path = os.getenv("ROBOTSIX_CONFIG_FILE")\n'
        'path2 = os.getenv("ROBOTSIX_CONFIG_FILE")\n',
    )

    assert check_config_single_source.main([str(clean)]) == 0
    assert check_config_single_source.main([str(dirty)]) == 1
    assert check_config_single_source.main([str(dup)]) == 1


def test_hook_script_parses_on_python_310_grammar() -> None:
    """The hook runs under the consumer's python3 (language: script), so it
    must not use 3.14-only syntax such as PEP 758 `except A, B:`."""
    src = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "check-config-single-source.py"
    ).read_text()
    ast.parse(src, feature_version=(3, 10))
