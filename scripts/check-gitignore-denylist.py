#!/usr/bin/env python3
"""Check that ``.gitignore`` covers the credential/secret-file deny list.

This script is the automated enforcement gate for gate 5 of
docs/security-posture.md, subsection *"Credential and secret files are never
tracked"* (see also docs/secret-files-are-never-tracked.md and
docs/repo-baseline.md).  The deny list is the **sole** defense for credential
*files* that content scanners (detect-secrets, TruffleHog, push protection)
cannot match — a bcrypt ``.htpasswd`` has no cleartext pattern, a templated
``wp-config.php`` hides its credentials, and a ``*.p12`` bundle is opaque — so
a missing ``.gitignore`` entry means such a file can be committed with no gate
firing.  This script makes the MUST mechanically checkable rather than
manual-only.

Rule enforced (per docs/security-posture.md):
  Every repo's ``.gitignore`` covers, at minimum:
    - ``.htpasswd``
    - ``.env`` and ``.env.*``
    - ``wp-config.php`` and ``wp-config*.php``
    - ``*.pem``, ``*.key`` (and other private-key files)
    - ``*secret*``
    - ``*.p12``

Per-repo negating exceptions (``!pattern`` lines) are honored: a repo that
deliberately tracks a file matched by one of the deny-list patterns (e.g. a
public certificate, a detect-secrets baseline) negates just that file with a
comment.  Negation lines never count as coverage and never mark a requirement
missing — coverage is decided solely by the positive patterns.

Warning-first (2026-09): missing patterns are reported as GitHub annotations
but do NOT fail the build, mirroring the SECURITY.md baseline-check treatment.
A follow-up gate flips this to fail-closed once the fleet is compliant.

Exit codes:
  0 — always (warning-first); missing patterns are emitted as ``::warning::``
"""

from __future__ import annotations

import fnmatch
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GITIGNORE = REPO_ROOT / ".gitignore"

# Each requirement is (human label, a representative filename of that
# credential class).  A requirement is satisfied when at least one positive
# ``.gitignore`` pattern matches its representative filename.  ``.env`` and
# ``.env.*`` are separate requirements on purpose: a bare ``.env`` entry does
# not cover ``.env.production`` (a repo needs ``.env.*`` or ``.env*`` for
# that), exactly as the standard spells them out separately.
REQUIREMENTS: list[tuple[str, str]] = [
    (".htpasswd", ".htpasswd"),
    (".env", ".env"),
    (".env.*", ".env.production"),
    ("wp-config.php", "wp-config.php"),
    ("wp-config*.php", "wp-config-sample.php"),
    ("*.pem", "server.pem"),
    ("*.key", "server.key"),
    ("*secret*", "app.secret"),
    ("*.p12", "client.p12"),
]


def _normalize(pattern: str) -> str:
    """Strip gitignore anchoring so a bare filename can be matched by fnmatch.

    Leading ``/`` (repo-root anchor), a leading ``**/`` (any-depth prefix) and
    a trailing ``/`` (directory marker) are decoration for our purposes: the
    deny-list patterns target files by name, so we compare the pattern's
    filename shape against a representative filename.
    """
    pattern = pattern.strip()
    if pattern.startswith("**/"):
        pattern = pattern[3:]
    if pattern.startswith("/"):
        pattern = pattern[1:]
    if pattern.endswith("/"):
        pattern = pattern[:-1]
    return pattern


def positive_patterns(text: str) -> list[str]:
    """Return the normalized, non-negated, non-comment ``.gitignore`` patterns.

    Blank lines, ``#`` comments and negation lines (``!pattern``) are dropped.
    Negations are intentionally excluded: they carve out a specific tracked
    file and must not be read as coverage of a deny-list requirement.
    """
    patterns: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        norm = _normalize(line)
        if norm:
            patterns.append(norm)
    return patterns


def _covers(patterns: list[str], filename: str) -> bool:
    """True when any positive pattern matches ``filename`` (gitignore-style)."""
    return any(fnmatch.fnmatchcase(filename, pat) for pat in patterns)


def missing_requirements(text: str) -> list[str]:
    """Return the labels of deny-list requirements not covered by ``text``."""
    patterns = positive_patterns(text)
    return [label for label, sample in REQUIREMENTS if not _covers(patterns, sample)]


def main() -> int:
    if not GITIGNORE.is_file():
        print(
            "::warning::.gitignore is missing at repo root; it must cover the "
            "credential/secret-file deny list (docs/security-posture.md gate 5)"
        )
        return 0

    text = GITIGNORE.read_text()
    missing = missing_requirements(text)

    if missing:
        for label in missing:
            print(
                f"::warning::.gitignore does not cover `{label}` — the "
                "credential/secret-file deny list requires it "
                "(docs/security-posture.md gate 5)"
            )
    else:
        print(".gitignore credential/secret-file deny list: OK")

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
