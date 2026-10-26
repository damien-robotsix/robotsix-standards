#!/usr/bin/env python3
"""Flag publishes to public package indexes and public-registry credentials.

This script is the ``public-registry-check`` gate specified in the
*Enforcement* section of docs/distribution-packaging.md (rules 4 and 5: never
publish to a public package index; publish jobs must resolve to an
org-internal registry).  The page is the specification — this script
implements it and does not redefine it.

Scope: ``.github/workflows/*.yml`` / ``*.yaml``, ``package.json``, ``.npmrc``
and ``pyproject.toml``.  When file paths are passed on the command line (e.g.
the files changed by a PR) only those in scope are scanned; with no arguments
every in-scope file in the repo is scanned (a superset of the changed files).

It flags (see the pattern table in docs/distribution-packaging.md):
  - ``registry.npmjs.org`` in workflows, ``package.json``
    ``publishConfig.registry`` and ``.npmrc`` (rule 4);
  - ``upload.pypi.org`` / ``pypi.org/legacy`` / ``test.pypi.org`` in workflows
    and ``pyproject.toml`` ``[[tool.uv.index]]`` ``publish-url`` (rule 4);
  - ``npm publish`` without ``--registry`` pointing at an approved internal
    domain (rule 5);
  - ``twine upload`` / ``uv publish`` without ``--repository-url`` /
    ``--publish-url`` pointing at an approved internal domain (rule 5);
  - the ``pypa/gh-action-pypi-publish`` action (rule 4);
  - ``secrets.NPM_TOKEN`` / ``secrets.PYPI_TOKEN`` / ``secrets.PYPI_API_TOKEN``
    (rules 4-5).

Approved internal domains live in ``APPROVED_DOMAINS``; adding one needs
Platform Owner approval in the same change.  A Platform Owner-approved
per-repo exception is an entry in ``.public-registry-allowlist`` at the repo
root, one per line: ``<path> <rule-id> <approval reference ...>`` — the
approval reference is mandatory; inline suppressions are not supported.

Rollout: warning-first.  Before ``BLOCKING_FROM`` (2027-01-31) findings are
``::warning::`` annotations and the exit code is 0; from that date they are
``::error::`` annotations and the exit code is 1.

Exit codes:
  0 — no findings, or findings before the blocking date
  1 — findings on or after the blocking date
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ALLOWLIST_NAME = ".public-registry-allowlist"
BLOCKING_FROM = _dt.date(2027, 1, 31)

# Org-internal registries a publish may target (Platform Owner approval
# required to extend).
APPROVED_DOMAINS: tuple[str, ...] = ("npm.pkg.github.com",)

DOC_REF = "docs/distribution-packaging.md#enforcement"

_NPMJS = re.compile(r"registry\.npmjs\.org", re.IGNORECASE)
_PYPI_UPLOAD = re.compile(
    r"upload\.pypi\.org|pypi\.org/legacy|test\.pypi\.org", re.IGNORECASE
)
_NPM_PUBLISH = re.compile(r"\bnpm\s+publish\b")
_PY_PUBLISH = re.compile(r"\btwine\s+upload\b|\buv\s+publish\b")
_PYPI_ACTION = re.compile(r"pypa/gh-action-pypi-publish", re.IGNORECASE)
_TOKEN_SECRET = re.compile(r"\bsecrets\.(NPM_TOKEN|PYPI_TOKEN|PYPI_API_TOKEN)\b")
_REGISTRY_FLAG = re.compile(r"--registry[=\s]+(\S+)")
_PY_URL_FLAG = re.compile(r"--(?:repository-url|publish-url)[=\s]+(\S+)")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str
    message: str


def _approved(url: str) -> bool:
    return any(domain in url for domain in APPROVED_DOMAINS)


def _flag_points_internal(flag: re.Pattern[str], text: str) -> bool:
    return any(_approved(m.group(1)) for m in flag.finditer(text))


def _logical_lines(text: str) -> list[tuple[int, str]]:
    """Return (first line number, content) with ``\\`` continuations joined.

    Whole-line ``#`` comments are dropped so prose never trips the check.
    """
    out: list[tuple[int, str]] = []
    buf: list[str] = []
    start = 0
    for num, raw in enumerate(text.splitlines(), start=1):
        if not buf and raw.lstrip().startswith("#"):
            continue
        if not buf:
            start = num
        stripped = raw.rstrip()
        if stripped.endswith("\\"):
            buf.append(stripped[:-1])
            continue
        buf.append(stripped)
        out.append((start, " ".join(buf)))
        buf = []
    if buf:
        out.append((start, " ".join(buf)))
    return out


def scan_workflow(path: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    for num, line in _logical_lines(text):
        if _NPMJS.search(line):
            findings.append(Finding(path, num, "npmjs-registry",
                                    "public npm registry `registry.npmjs.org` (rule 4)"))
        if _PYPI_UPLOAD.search(line):
            findings.append(Finding(path, num, "pypi-upload",
                                    "public PyPI upload endpoint (rule 4)"))
        if _NPM_PUBLISH.search(line) and not _flag_points_internal(_REGISTRY_FLAG, line):
            findings.append(Finding(path, num, "npm-publish",
                                    "`npm publish` without `--registry` pointing at an "
                                    "approved internal domain (rule 5)"))
        if _PY_PUBLISH.search(line) and not _flag_points_internal(_PY_URL_FLAG, line):
            findings.append(Finding(path, num, "python-publish",
                                    "`twine upload` / `uv publish` without "
                                    "`--repository-url` / `--publish-url` pointing at an "
                                    "approved internal domain (rule 5)"))
        if _PYPI_ACTION.search(line):
            findings.append(Finding(path, num, "pypi-publish-action",
                                    "`pypa/gh-action-pypi-publish` targets public PyPI "
                                    "(rule 4)"))
        for m in _TOKEN_SECRET.finditer(line):
            findings.append(Finding(path, num, "registry-token",
                                    f"public-registry credential `secrets.{m.group(1)}` "
                                    "(rules 4-5)"))
    return findings


def scan_npmrc(path: str, text: str) -> list[Finding]:
    return [
        Finding(path, num, "npmjs-registry",
                "public npm registry `registry.npmjs.org` (rule 4)")
        for num, line in _logical_lines(text)
        if not line.lstrip().startswith(";") and _NPMJS.search(line)
    ]


def scan_package_json(path: str, text: str) -> list[Finding]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    publish = data.get("publishConfig") if isinstance(data, dict) else None
    registry = publish.get("registry") if isinstance(publish, dict) else None
    if isinstance(registry, str) and _NPMJS.search(registry):
        return [Finding(path, _line_of(text, "registry.npmjs.org"), "npmjs-registry",
                        "`publishConfig.registry` is the public npm registry (rule 4)")]
    return []


def scan_pyproject(path: str, text: str) -> list[Finding]:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return []
    indexes = data.get("tool", {}).get("uv", {}).get("index", [])
    findings: list[Finding] = []
    if not isinstance(indexes, list):
        return findings
    for index in indexes:
        url = index.get("publish-url") if isinstance(index, dict) else None
        if isinstance(url, str) and _PYPI_UPLOAD.search(url):
            findings.append(Finding(path, _line_of(text, url), "pypi-upload",
                                    "`[[tool.uv.index]]` `publish-url` is a public PyPI "
                                    "upload endpoint (rule 4)"))
    return findings


def _line_of(text: str, needle: str) -> int:
    for num, line in enumerate(text.splitlines(), start=1):
        if needle.lower() in line.lower():
            return num
    return 1


def scanner_for(rel: str):
    """Return the scanner for an in-scope repo-relative path, else None."""
    p = Path(rel)
    if p.parent.as_posix() == ".github/workflows" and p.suffix in (".yml", ".yaml"):
        return scan_workflow
    if p.name == "package.json":
        return scan_package_json
    if p.name == ".npmrc":
        return scan_npmrc
    if p.name == "pyproject.toml":
        return scan_pyproject
    return None


def discover(root: Path) -> list[str]:
    """Every in-scope file under ``root`` (skipping VCS / dependency dirs)."""
    skip = {".git", "node_modules", ".venv", "site"}
    found: list[str] = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in skip for part in rel.parts) or not path.is_file():
            continue
        if scanner_for(rel.as_posix()) is not None:
            found.append(rel.as_posix())
    return found


def parse_allowlist(text: str) -> set[tuple[str, str]]:
    """Parse ``<path> <rule-id> <approval ...>`` entries.

    An entry without an approval reference is ignored: every exception must
    name the Platform Owner approval it rests on.
    """
    entries: set[tuple[str, str]] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 2)
        if len(parts) == 3:
            entries.add((parts[0], parts[1]))
    return entries


def scan(root: Path, paths: list[str] | None = None) -> list[Finding]:
    rels = discover(root) if not paths else paths
    allow_file = root / ALLOWLIST_NAME
    allow = parse_allowlist(allow_file.read_text()) if allow_file.is_file() else set()
    findings: list[Finding] = []
    for rel in rels:
        scanner = scanner_for(rel)
        full = root / rel
        if scanner is None or not full.is_file():
            continue
        for f in scanner(rel, full.read_text(encoding="utf-8", errors="replace")):
            if (f.path, f.rule) not in allow:
                findings.append(f)
    return findings


def main(argv: list[str] | None = None, today: _dt.date | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    today = today or _dt.date.today()
    blocking = today >= BLOCKING_FROM
    level = "error" if blocking else "warning"
    findings = scan(REPO_ROOT, args)
    for f in findings:
        print(f"::{level} file={f.path},line={f.line}::[{f.rule}] {f.message} "
              f"— see {DOC_REF}")
    if not findings:
        print("Public-registry check: OK")
        return 0
    if blocking:
        return 1
    print(f"Public-registry check: {len(findings)} finding(s); warning-first "
          f"until {BLOCKING_FROM.isoformat()}, blocking from then")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
