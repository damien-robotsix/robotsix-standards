#!/usr/bin/env python3
"""Reject Config-standard violations: ``ROBOTSIX_*`` env-overlay reads and
allowed bootstrap vars resolved more than once.

The config standard (docs/config-standard.md §1) mandates that a deployable
component's runtime config values come from **one JSON file** — no environment
overlay, no CLI-merge, and never from ``ROBOTSIX_*`` value variables.  The
only ``ROBOTSIX_*`` vars the standard defines are two *locate/history* vars
that name the file and cap its version history, each resolved exactly once in
a config bootstrap (docs/env-config-bootstrap.md rules 1-3):

- ``ROBOTSIX_CONFIG_FILE`` — read once in ``resolve_config_path()`` (locate
  only, never carries values).
- ``ROBOTSIX_CONFIG_MAX_VERSIONS`` — read once in the history store loader.

That MUST carried no machine gate — a repo that added
``os.getenv("ROBOTSIX_LOG_LEVEL")``, or read ``ROBOTSIX_CONFIG_FILE`` at a
second call site, slipped through green CI while quietly reintroducing
multi-source-config drift (OWASP Secrets Management / configuration-as-
secrets).  This hook makes the single-source MUST machine-checkable, the same
way ``check-secret-str`` machine-checks the SecretStr MUST (config-standard.md
§3).

Two blocking detection rules, both scoped to the ``ROBOTSIX_`` namespace:

1. **Env-overlay gate.** An env-read call site whose string-literal variable
   name matches ``ROBOTSIX_*`` and is **not** in ``ALLOWED_ROBOTSIX_VARS`` is
   a finding.
2. **Resolve-once gate.** Each allowed var read at ≥2 distinct call sites
   (distinct file + line) across the repo is a finding.

Env-read call-site forms matched (string-literal argument only):
``os.getenv("VAR")`` / ``os.getenv('VAR')``, ``os.environ["VAR"]``,
``os.environ.get("VAR")``, and bare ``getenv("VAR")``.  A ``ROBOTSIX_*`` name
in a whole-line ``#`` comment or in a string literal that is not such a call
site (prose, docstrings) is never flagged — no false positives.

A same-line exemption pragma with a **mandatory non-empty reason** exempts the
read on that line::

    os.getenv("ROBOTSIX_LOG_LEVEL")  # config-single-source: bootstrap only

A pragma with an empty or blank reason (``# config-single-source:``) does not
exempt; a pragma on any other line has no effect.

Non-``ROBOTSIX_*`` env reads (e.g. ``os.environ.get("REPO_PRIVATE")``,
``os.getenv("CI")``) are out of scope: the ``ROBOTSIX_*`` prefix is the only
mechanically identifiable config namespace.  General per-repo config env vars
(``SURVEY_*``, ...) remain self-policing.

Python-only (``types: [python]``), fail-closed:

Exit codes:
  0 — no ``ROBOTSIX_*`` single-source violations found
  1 — at least one env-overlay read or a resolve-once violation found
"""

from __future__ import annotations

import ast
import io
import re
import sys
import tokenize
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

# The only ROBOTSIX_* vars the config standard defines: a *locate* var and a
# *history* var, each read exactly once in the config bootstrap.  Kept as a
# tuple so the constant is immutable (no RUF012 mutable-class-attribute).
ALLOWED_ROBOTSIX_VARS = ("ROBOTSIX_CONFIG_FILE", "ROBOTSIX_CONFIG_MAX_VERSIONS")

# Config-env-var namespace: any other ROBOTSIX_*-prefixed name is a forbidden
# value variable.
_ROBOTSIX_VAR_RE = re.compile(r"^ROBOTSIX_")

# Same-line exemption pragma; the reason after the colon must be non-blank.
_PRAGMA_RE = re.compile(r"#\s*config-single-source:\s*(?P<reason>[^#]*)")

# Tuple for the same PEP 758 reason as check-secret-str.py: this script runs
# as a `language: script` pre-commit hook under the CONSUMER's system python3,
# which may predate 3.14 — the bare form is a SyntaxError there.
_TOKENIZE_ERRORS = (tokenize.TokenError, SyntaxError)

# ast.parse failures (syntax errors, null bytes).  A tuple for the same PEP 758
# reason as _TOKENIZE_ERRORS.
_PARSE_ERRORS = (SyntaxError, ValueError)

# Unreadable files (deps, mixed encoding, syntax errors) are skipped silently,
# exactly like check-secret-str.py.
_UNREADABLE = (OSError, SyntaxError, UnicodeDecodeError)

# Directories skipped during a recursive scan (deps, build/docs output, VCS).
_SKIP_DIRS = (
    ".git",
    ".venv",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    "build",
    "site",
)


@dataclass(frozen=True)
class Finding:
    """One violation: a ``ROBOTSIX_*`` env read outside the allowlist, or an
    allowed var resolved at more than one call site."""

    path: Path
    lineno: int
    col: int
    var: str
    kind: str  # "value-var" (Detection 1) | "resolve-once" (Detection 2)
    count: int = 1  # call-site count, populated for resolve-once findings


@dataclass(frozen=True)
class Read:
    """One ``ROBOTSIX_*`` env-read call site inside a file."""

    path: Path
    lineno: int
    col: int
    var: str


def _exempt_lines(source: str) -> set[int]:
    """Return line numbers carrying a valid ``config-single-source`` pragma.

    Uses ``tokenize`` so only real comments count (a ``#`` inside a string
    literal never exempts a read).  A pragma with an empty or blank reason is
    ignored.
    """
    lines: set[int] = set()
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except _TOKENIZE_ERRORS:
        return lines
    for token in tokens:
        if token.type != tokenize.COMMENT:
            continue
        match = _PRAGMA_RE.search(token.string)
        if match and match.group("reason").strip():
            lines.add(token.start[0])
    return lines


def _var_from_literal(node: ast.expr) -> str | None:
    """Return *node*'s value if it is a ``ROBOTSIX_*`` string literal."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        if _ROBOTSIX_VAR_RE.match(node.value):
            return node.value
    return None


def _is_os_getenv(func: ast.expr) -> bool:
    """True for ``os.getenv``."""
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "getenv"
        and isinstance(func.value, ast.Name)
        and func.value.id == "os"
    )


def _is_os_environ_get(func: ast.expr) -> bool:
    """True for ``os.environ.get``."""
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "get"
        and isinstance(func.value, ast.Attribute)
        and func.value.attr == "environ"
        and isinstance(func.value.value, ast.Name)
        and func.value.value.id == "os"
    )


def _is_bare_getenv(func: ast.expr) -> bool:
    """True for a bare ``getenv`` (as imported from ``os``)."""
    return isinstance(func, ast.Name) and func.id == "getenv"


def _is_os_environ_subscript(node: ast.Subscript) -> bool:
    """True for a subscript of ``os.environ`` (``os.environ["VAR"]``)."""
    return (
        isinstance(node.value, ast.Attribute)
        and node.value.attr == "environ"
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "os"
    )


def _call_var(node: ast.Call) -> str | None:
    """Return the ``ROBOTSIX_*`` var read by an env-read *call*, if any."""
    if (
        _is_os_getenv(node.func)
        or _is_os_environ_get(node.func)
        or _is_bare_getenv(node.func)
    ):
        if node.args:
            return _var_from_literal(node.args[0])
    return None


def _subscript_var(node: ast.Subscript) -> str | None:
    """Return the ``ROBOTSIX_*`` var read by an ``os.environ[...]`` read."""
    if _is_os_environ_subscript(node):
        return _var_from_literal(node.slice)
    return None


def _collect_reads(tree: ast.Module, path: Path) -> list[Read]:
    """Collect every ``ROBOTSIX_*`` env-read call site in one parsed module."""
    reads: list[Read] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            var = _call_var(node)
            if var is not None:
                reads.append(
                    Read(path=path, lineno=node.lineno, col=node.col_offset, var=var)
                )
        elif isinstance(node, ast.Subscript):
            var = _subscript_var(node)
            if var is not None:
                reads.append(
                    Read(path=path, lineno=node.lineno, col=node.col_offset, var=var)
                )
    return reads


def _parse_file(path: Path) -> tuple[str | None, ast.Module | None]:
    """Read and parse *path*; ``(None, None)`` when unreadable or unparsable."""
    try:
        source = path.read_text(encoding="utf-8")
    except _UNREADABLE:
        return None, None
    try:
        tree = ast.parse(source, filename=str(path))
    except _PARSE_ERRORS:
        return None, None
    return source, tree


def scan_file(path: Path) -> list[Finding]:
    """Scan one Python file and return env-overlay (Detection 1) findings.

    Every ``ROBOTSIX_*`` env read whose name is not in ``ALLOWED_ROBOTSIX_VARS``
    — and is not exempted by a same-line ``config-single-source`` pragma — is a
    finding.  Reads of the two allowed vars are left to the repo-wide
    resolve-once pass (Detection 2, see ``resolve_once_findings``).
    """
    source, tree = _parse_file(path)
    if source is None or tree is None:
        return []
    exempt = _exempt_lines(source)
    findings: list[Finding] = []
    for read in _collect_reads(tree, path):
        if read.lineno in exempt:
            continue
        if read.var not in ALLOWED_ROBOTSIX_VARS:
            findings.append(
                Finding(
                    path=read.path,
                    lineno=read.lineno,
                    col=read.col,
                    var=read.var,
                    kind="value-var",
                )
            )
    return findings


def resolve_once_findings(files: Sequence[Path]) -> list[Finding]:
    """Return resolve-once (Detection 2) findings across a set of files.

    An allowed var resolved at ≥2 distinct call sites — distinct ``(file,
    line)`` pairs — is a finding.  Reads exempted by a same-line pragma are
    not counted.  One finding is produced per offending var, anchored at its
    first call site, with the total distinct call-site count.
    """
    sites_by_var: dict[str, set[tuple[Path, int]]] = {}
    first_by_var: dict[str, Read] = {}
    for file in files:
        source, tree = _parse_file(file)
        if source is None or tree is None:
            continue
        exempt = _exempt_lines(source)
        for read in _collect_reads(tree, file):
            if read.var not in ALLOWED_ROBOTSIX_VARS or read.lineno in exempt:
                continue
            sites_by_var.setdefault(read.var, set()).add((read.path, read.lineno))
            first_by_var.setdefault(read.var, read)
    findings: list[Finding] = []
    for var, sites in sites_by_var.items():
        if len(sites) >= 2:
            anchor = first_by_var[var]
            findings.append(
                Finding(
                    path=anchor.path,
                    lineno=anchor.lineno,
                    col=anchor.col,
                    var=var,
                    kind="resolve-once",
                    count=len(sites),
                )
            )
    return findings


def _py_files(paths: Sequence[Path]) -> list[Path]:
    """Expand *paths* into a sorted, de-duplicated list of ``.py`` files."""
    files: set[Path] = set()
    for path in paths:
        if path.is_file():
            if path.suffix == ".py":
                files.add(path)
        elif path.is_dir():
            for child in path.rglob("*.py"):
                if not any(part in _SKIP_DIRS for part in child.parts):
                    files.add(child)
    return sorted(files)


def main(argv: Sequence[str] | None = None) -> int:
    """Flag ``ROBOTSIX_*`` env-overlay and resolve-once violations.

    Scans the given paths (or the current directory) for env-read call sites
    in the ``ROBOTSIX_*`` namespace: any read of a var outside
    ``ALLOWED_ROBOTSIX_VARS`` (env overlay, docs/config-standard.md §1) and
    any allowed var resolved at more than one call site (resolve-once,
    docs/env-config-bootstrap.md).

    Exit codes:
      0 — no ``ROBOTSIX_*`` single-source violations found
      1 — one or more violations found
    """
    args = list(argv) if argv is not None else sys.argv[1:]
    paths = [Path(p) for p in args] or [Path.cwd()]
    files = _py_files(paths)

    findings: list[Finding] = []
    for file in files:
        findings.extend(scan_file(file))
    findings.extend(resolve_once_findings(files))

    findings.sort(key=lambda finding: (str(finding.path), finding.lineno, finding.col))
    for finding in findings:
        if finding.kind == "resolve-once":
            print(
                f"{finding.path}:{finding.lineno}:{finding.col + 1}: "
                f"{finding.var} is resolved at {finding.count} call sites; "
                f"resolve it exactly once in the config bootstrap "
                f"(docs/env-config-bootstrap.md)"
            )
        else:
            print(
                f"{finding.path}:{finding.lineno}:{finding.col + 1}: "
                f"{finding.var} read as a config value; config values come only "
                f"from the one config file, never from ROBOTSIX_* value "
                f"variables (docs/config-standard.md §1)"
            )
    if findings:
        print(
            f"\n{len(findings)} ROBOTSIX_* single-source violation(s): the one "
            f"config file is the only source of config values "
            f"(docs/config-standard.md §1), and the allowed bootstrap vars "
            f"resolve exactly once (docs/env-config-bootstrap.md)."
        )
        return 1
    print("No ROBOTSIX_* single-source violations found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
