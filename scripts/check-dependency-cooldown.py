#!/usr/bin/env python3
"""Check that auto-merged dependency updates wait out a release-age cooldown.

This script is the automated enforcement gate for gate 3 of
docs/security-posture.md (see also docs/repo-baseline.md
§ Release-age cooldown and docs/ci-dependency-standard.md §1).  The fleet
auto-merges minor/patch dependency updates once required CI passes; CI cannot
catch a freshly published malicious release (it behaves normally in tests, and
CI *runs* it), but most such releases are yanked within hours to a few days.
A minimum release age before auto-merge avoids most of them.

Rules enforced:
  - ``renovate.json`` (when present): every ``packageRules`` entry (and the
    top level) with ``"automerge": true`` has an effective
    ``minimumReleaseAge`` of at least 3 days and
    ``"internalChecksFilter": "strict"``; ``vulnerabilityAlerts`` must not set
    a ``minimumReleaseAge`` (security fixes are never delayed).
  - ``.github/dependabot.yml`` (when present): every auto-merge-eligible
    ecosystem — every ecosystem except ``docker`` and ``pre-commit``, which are
    excluded from auto-merge — has ``cooldown: default-days:`` of at least 3.

Accepted risk: a repo that cannot carry the cooldown on one target adds an
entry to ``.dependency-cooldown-allowlist`` at the repo root, one per line:
``<target> <approval reference ...>`` where ``<target>`` is a Dependabot
ecosystem name (e.g. ``github-actions``) or ``renovate``.  The approval
reference is mandatory; an entry without one is ignored.

Rollout: warning-first.  Before ``BLOCKING_FROM`` (2027-01-31) problems are
``::warning::`` annotations and the exit code is 0; from that date they are
``::error::`` annotations and the exit code is 1 (the same flip date as the
other baseline gates).

Exit codes:
  0 — cooldown configured everywhere, or problems found before the blocking date
  1 — problems found on or after the blocking date
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import sys
from pathlib import Path

import yaml  # type: ignore[import-untyped]

REPO_ROOT = Path(__file__).resolve().parent.parent
RENOVATE = REPO_ROOT / "renovate.json"
DEPENDABOT_CANDIDATES = (
    REPO_ROOT / ".github" / "dependabot.yml",
    REPO_ROOT / ".github" / "dependabot.yaml",
)
ALLOWLIST = REPO_ROOT / ".dependency-cooldown-allowlist"
BLOCKING_FROM = _dt.date(2027, 1, 31)
MIN_DAYS = 3
# Ecosystems excluded from auto-merge (docs/dependabot-auto-merge.md): a human
# reviews every PR, so the cooldown is recommended there but not required.
NON_AUTOMERGE_ECOSYSTEMS = frozenset({"docker", "pre-commit"})
DOC = "docs/repo-baseline.md#release-age-cooldown"

_DURATION_RE = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*"
    r"(m|mins?|minutes?|h|hrs?|hours?|d|days?|w|weeks?)\s*$",
    re.IGNORECASE,
)
_UNIT_DAYS = {"m": 1 / 1440, "h": 1 / 24, "d": 1.0, "w": 7.0}


def duration_days(value: object) -> float | None:
    """Return a Renovate duration string (``"3 days"``) in days, or None."""
    if not isinstance(value, str):
        return None
    match = _DURATION_RE.match(value)
    if not match:
        return None
    unit = match.group(2).lower()
    key = "m" if unit.startswith("m") else unit[0]
    return float(match.group(1)) * _UNIT_DAYS[key]


def parse_allowlist(text: str) -> set[str]:
    """Parse ``<target> <approval reference ...>`` accepted-risk entries."""
    targets: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) == 2 and parts[1].strip():
            targets.add(parts[0])
    return targets


def renovate_problems(config: dict) -> list[str]:
    """Return cooldown problems in a parsed ``renovate.json``."""
    problems: list[str] = []
    top_age = config.get("minimumReleaseAge")
    top_filter = config.get("internalChecksFilter")
    scopes: list[tuple[str, dict]] = []
    if config.get("automerge") is True:
        scopes.append(("top level", config))
    for index, rule in enumerate(config.get("packageRules") or []):
        if isinstance(rule, dict) and rule.get("automerge") is True:
            scopes.append((f"packageRules[{index}]", rule))
    for label, scope in scopes:
        age = scope.get("minimumReleaseAge", top_age)
        days = duration_days(age)
        if days is None or days < MIN_DAYS:
            problems.append(
                f"renovate.json {label}: auto-merge without "
                f'"minimumReleaseAge" of at least "{MIN_DAYS} days" (got {age!r})'
            )
        if scope.get("internalChecksFilter", top_filter) != "strict":
            problems.append(
                f'renovate.json {label}: auto-merge without "internalChecksFilter": '
                '"strict"'
            )
    alerts = config.get("vulnerabilityAlerts")
    if isinstance(alerts, dict) and alerts.get("minimumReleaseAge") is not None:
        problems.append(
            "renovate.json vulnerabilityAlerts: sets minimumReleaseAge — security "
            "updates must never be delayed"
        )
    return problems


def dependabot_problems(config: dict) -> list[tuple[str, str]]:
    """Return ``(ecosystem, problem)`` pairs for a parsed ``dependabot.yml``."""
    problems: list[tuple[str, str]] = []
    for update in config.get("updates") or []:
        if not isinstance(update, dict):
            continue
        ecosystem = str(update.get("package-ecosystem", ""))
        if not ecosystem or ecosystem in NON_AUTOMERGE_ECOSYSTEMS:
            continue
        cooldown = update.get("cooldown")
        days = cooldown.get("default-days") if isinstance(cooldown, dict) else None
        if not isinstance(days, int) or days < MIN_DAYS:
            message = (
                f"dependabot.yml {ecosystem} (directory "
                f"{update.get('directory', '?')}): auto-merge-eligible ecosystem "
                f"without `cooldown: default-days: {MIN_DAYS}` or more "
                f"(got {days!r})"
            )
            problems.append((ecosystem, message))
    return problems


def collect_problems() -> list[str]:
    """Return every unaccepted cooldown problem in this repo."""
    allowed = parse_allowlist(ALLOWLIST.read_text()) if ALLOWLIST.is_file() else set()
    problems: list[str] = []
    if RENOVATE.is_file() and "renovate" not in allowed:
        try:
            config = json.loads(RENOVATE.read_text())
        except json.JSONDecodeError as exc:
            problems.append(f"renovate.json: not valid JSON ({exc})")
        else:
            if isinstance(config, dict):
                problems.extend(renovate_problems(config))
    for path in DEPENDABOT_CANDIDATES:
        if not path.is_file():
            continue
        config = yaml.safe_load(path.read_text()) or {}
        if isinstance(config, dict):
            problems.extend(
                msg for eco, msg in dependabot_problems(config) if eco not in allowed
            )
    return problems


def main(today: _dt.date | None = None) -> int:
    today = today or _dt.date.today()
    blocking = today >= BLOCKING_FROM
    level = "error" if blocking else "warning"

    problems = collect_problems()
    if not problems:
        print("Dependency release-age cooldown: OK")
        return 0
    for problem in problems:
        print(f"::{level}::{problem} ({DOC})")
    if blocking:
        return 1
    print(
        f"Dependency release-age cooldown: {len(problems)} problem(s); "
        f"warning-first until {BLOCKING_FROM.isoformat()}, blocking from then"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
