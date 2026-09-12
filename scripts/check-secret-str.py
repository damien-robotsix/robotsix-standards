#!/usr/bin/env python3
"""Reject ``str``-typed secret fields in pydantic config models.

The config standard (docs/config-standard.md §3) mandates that a secret field
is declared with ``pydantic.SecretStr`` — masked on read and rendered as
``writeOnly`` in the JSON Schema.  A secret field annotated as plain ``str``
passes every other gate (mypy, ruff, the schema-drift check) while storing and
logging the secret as plaintext, so this hook makes the SecretStr convention
machine-checkable: it fails on any pydantic model field whose name matches a
secret pattern (``api_key``, ``apikey``, ``token``, ``password``, ``passwd``,
``secret``) and whose annotation is ``str`` (or ``Optional[str]`` /
``str | None``) instead of ``SecretStr``.

Nested containers are not flagged: ``keys: dict[str, SecretStr]`` is the
documented pattern for secret maps and is correctly typed (the *value* type is
what carries the secret).  Fields on classes that do not subclass pydantic's
``BaseModel`` (directly or through an in-file chain) are also out of scope.

Exit codes:
  0 — no offending fields found
  1 — at least one secret-named field is typed ``str``
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

# Field-name substrings (case-insensitive) that identify a secret.  Kept as a
# tuple so the constant is immutable (no RUF012 mutable-class-attribute).
SECRET_PATTERNS = ("api_key", "apikey", "token", "password", "passwd", "secret")

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
    """One offending field: a secret-named field annotated ``str``."""

    path: Path
    lineno: int
    col: int
    cls: str
    field: str


def _is_secret_name(name: str) -> bool:
    """True if *name* contains a secret pattern, e.g. ``api_key`` / ``token``."""
    lowered = name.lower()
    return any(pattern in lowered for pattern in SECRET_PATTERNS)


def _is_scalar_str(annotation: ast.expr) -> bool:
    """True if *annotation* is ``str``, ``Optional[str]``, ``str | None``.

    Container annotations (``list[str]``, ``dict[str, SecretStr]``) are
    deliberately not treated as scalar ``str``: a secret *map* uses
    ``SecretStr`` as its value type, and the value type is what the hook must
    not false-positive on.
    """
    if isinstance(annotation, ast.Name):
        return annotation.id == "str"
    if (
        isinstance(annotation, ast.Subscript)
        and isinstance(annotation.value, ast.Name)
        and annotation.value.id == "Optional"
        and isinstance(annotation.slice, ast.Name)
        and annotation.slice.id == "str"
    ):
        return True
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        left = annotation.left
        right = annotation.right
        left_is_str = isinstance(left, ast.Name) and left.id == "str"
        right_is_str = isinstance(right, ast.Name) and right.id == "str"
        left_is_none = isinstance(left, ast.Constant) and left.value is None
        right_is_none = isinstance(right, ast.Constant) and right.value is None
        return (left_is_str and right_is_none) or (left_is_none and right_is_str)
    return False


def _collect_models(classes: dict[str, ast.ClassDef]) -> set[str]:
    """Return names of pydantic model classes (fixpoint over in-file bases).

    A class is a model if any base is ``BaseModel`` (or ``pydantic.BaseModel``)
    or is itself a model defined in the same module.  Imported base classes we
    cannot resolve are treated as non-models; the standard's config models
    subclass pydantic's ``BaseModel`` directly.
    """
    models: set[str] = set()
    changed = True
    while changed:
        changed = False
        for name, classdef in classes.items():
            if name in models:
                continue
            for base in classdef.bases:
                if isinstance(base, ast.Attribute) and base.attr == "BaseModel":
                    models.add(name)
                    changed = True
                    break
                if isinstance(base, ast.Name) and (
                    base.id == "BaseModel" or base.id in models
                ):
                    models.add(name)
                    changed = True
                    break
    return models


def _findings_in_model(
    classdef: ast.ClassDef, path: Path, models: set[str]
) -> list[Finding]:
    """Return findings for secret-named ``str`` fields in one model class."""
    findings: list[Finding] = []
    for node in classdef.body:
        if not isinstance(node, ast.AnnAssign):
            continue
        target = node.target
        if not isinstance(target, ast.Name):
            continue
        if not _is_secret_name(target.id):
            continue
        if node.annotation is not None and _is_scalar_str(node.annotation):
            findings.append(
                Finding(
                    path=path,
                    lineno=node.lineno,
                    col=node.col_offset,
                    cls=classdef.name,
                    field=target.id,
                )
            )
    return findings


def scan_file(path: Path) -> list[Finding]:
    """Scan one Python file and return secret-named ``str`` field findings."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return []
    classes = {
        node.name: node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
    }
    models = _collect_models(classes)
    findings: list[Finding] = []
    for classdef in classes.values():
        if classdef.name in models:
            findings.extend(_findings_in_model(classdef, path, models))
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
    args = list(argv) if argv is not None else sys.argv[1:]
    paths = [Path(p) for p in args] or [Path.cwd()]
    findings: list[Finding] = []
    for file in _py_files(paths):
        findings.extend(scan_file(file))

    findings.sort(key=lambda finding: (str(finding.path), finding.lineno, finding.col))
    for finding in findings:
        print(
            f"{finding.path}:{finding.lineno}:{finding.col + 1}: "
            f"{finding.cls}.{finding.field} is typed str; "
            f"declare it pydantic.SecretStr (docs/config-standard.md §3)"
        )
    if findings:
        print(
            f"\n{len(findings)} secret field(s) typed str in config models: "
            "a plain str passes every other gate while storing/logging the "
            "secret as plaintext."
        )
        return 1
    print("No str-typed secret fields found in config models.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
