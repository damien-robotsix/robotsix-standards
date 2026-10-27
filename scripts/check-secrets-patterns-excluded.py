#!/usr/bin/env python3
"""Check the ``.secrets-patterns-excluded`` scanner-exclusion file and wiring.

This script is the automated enforcement gate for
docs/secret-files-are-never-tracked.md (the companion to
docs/security-posture.md gate 5).  The standard mandates a reviewed
``.secrets-patterns-excluded`` file at the repo root, listing one regular
expression per line, that TruffleHog reads directly via ``--exclude-paths``.
Two ways the mandate silently breaks — and this gate catches both:

  1. **A no-op detect-secrets wiring.**  detect-secrets' ``--exclude-files``
     flag takes a *single regex*, not a path to a pattern file.  Wiring
     ``--exclude-files .secrets-patterns-excluded`` in ``.pre-commit-config.yaml``
     makes detect-secrets treat the literal filename as a regex and never open
     the file, so every listed pattern is silently ignored.  A no-op produces
     no error, so only a structural check finds it.

  2. **Glob syntax where a regex is expected.**  The file is regex, not
     gitignore globs.  A line such as ``vendor/*`` is a valid glob but an
     invalid (or wrong-meaning) regex, so scanners would skip the wrong paths.
     Each non-comment line is compiled with Python's ``re`` to catch a pattern
     that will not parse.

Rollout: warning-first since 2026-09.  Before ``BLOCKING_FROM`` (2027-01-31)
problems are ``::warning::`` annotations and the exit code is 0; from that
date they are ``::error::`` annotations and the exit code is 1 — the same flip
date as the ``.gitignore`` deny-list gate (scripts/check-gitignore-denylist.py)
and scripts/check-public-registry.py.

Exit codes:
  0 — no problems, or problems found before the blocking date
  1 — problems found on or after the blocking date
"""

from __future__ import annotations

import datetime as _dt
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PATTERNS_FILE = REPO_ROOT / ".secrets-patterns-excluded"
PRECOMMIT = REPO_ROOT / ".pre-commit-config.yaml"
BLOCKING_FROM = _dt.date(2027, 1, 31)

# The exact no-op miswiring: detect-secrets ``--exclude-files`` fed the pattern
# file's name instead of a regex.  Matched tolerantly across the two-line
# (``- '--exclude-files'`` then ``- '.secrets-patterns-excluded'``) and inline
# (``--exclude-files .secrets-patterns-excluded``) argument spellings — the
# bounded ``.{0,40}?`` gap spans the YAML list separator (quotes, newline,
# ``-``) between the flag and the filename.
_NOOP_WIRING = re.compile(
    r"--exclude-files.{0,40}?\.secrets-patterns-excluded",
    re.DOTALL,
)


def pattern_lines(text: str) -> list[str]:
    """Return the non-blank, non-comment lines of the exclusion file.

    Blank lines and ``#`` comments are dropped; every remaining line is a
    regex the scanners are expected to compile.
    """
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    return lines


def invalid_patterns(text: str) -> list[str]:
    """Return the pattern lines that do not compile as a Python regex."""
    bad: list[str] = []
    for line in pattern_lines(text):
        try:
            re.compile(line)
        except re.error:
            bad.append(line)
    return bad


def detect_secrets_noop(precommit_text: str) -> bool:
    """True when detect-secrets is wired with the no-op ``--exclude-files`` form.

    The presence of ``--exclude-files .secrets-patterns-excluded`` (in either
    the split-argument or inline spelling) means detect-secrets treats the
    filename as a regex and never reads the file — a silent no-op.
    """
    return _NOOP_WIRING.search(precommit_text) is not None


def main(today: _dt.date | None = None) -> int:
    today = today or _dt.date.today()
    blocking = today >= BLOCKING_FROM
    level = "error" if blocking else "warning"
    ok = True

    if not PATTERNS_FILE.is_file():
        print(
            f"::{level}::.secrets-patterns-excluded is missing at repo root; "
            "every repo must ship it as the reviewed scanner-exclusion file "
            "(docs/secret-files-are-never-tracked.md)"
        )
        ok = False
    else:
        for line in invalid_patterns(PATTERNS_FILE.read_text()):
            print(
                f"::{level}::.secrets-patterns-excluded line `{line}` is not a "
                "valid regular expression — the file is newline-separated "
                "regexes (RE2/re), not gitignore globs "
                "(docs/secret-files-are-never-tracked.md)"
            )
            ok = False

    if PRECOMMIT.is_file() and detect_secrets_noop(PRECOMMIT.read_text()):
        print(
            f"::{level}::.pre-commit-config.yaml wires detect-secrets with "
            "`--exclude-files .secrets-patterns-excluded` — a silent no-op "
            "(--exclude-files takes a regex, not a file). Move path exclusions "
            "to the hook's `exclude:` regex "
            "(docs/secret-files-are-never-tracked.md)"
        )
        ok = False

    if ok:
        print(".secrets-patterns-excluded presence and wiring: OK")
        return 0
    if blocking:
        return 1
    print(
        ".secrets-patterns-excluded: problems found; warning-first until "
        f"{BLOCKING_FROM.isoformat()}, blocking from then"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
