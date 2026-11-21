#!/usr/bin/env python3
"""Restore the committed ``.secrets.baseline`` to its stable, drift-free form.

The committed baseline is the allowlist of reviewed findings that the
detect-secrets pre-commit hook validates against.  detect-secrets matches a
scanned finding to a baseline entry by ``filename`` + ``hashed_secret`` (and the
secret ``type``) — never by line number, which is informational triage data and
not part of the verdict.  Yet the stock Yelp pre-commit hook rewrites the
baseline whenever a committed file shifts a flagged line: it re-keys the strict
"should I rewrite?" comparison on the stored line number, and pre-commit then
fails with 'files were modified by this hook'.  A one-line docs edit near a
baselined secret therefore used to force a separate fix-on-top regeneration.

The repo's committed baseline stores NO per-entry ``line_number`` and pins
``generated_at`` to a constant.  detect-secrets treats a missing line number as
"untracked" and skips strict line-number comparison, so a docs edit that shifts
a flagged line is byte-identical to a no-op run: the hook passes without
touching the baseline, while a genuinely new secret (same file, new
``hashed_secret``) still fails it.

This script is the regeneration tail.  The standard regeneration
``detect-secrets scan --baseline .secrets.baseline`` merges new findings and
re-writes the baseline *with* line numbers and a fresh timestamp; run this right
after to restore the line-number-free, clock-free form before committing.
Idempotent: a baseline that is already normalized is left untouched.

Exit codes:
  0 — baseline was already normalized, or was rewritten to the normalized form
  1 — the baseline could not be read or is malformed
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# A single pinned timestamp instead of a wall-clock time, so a regeneration
# that changes nothing produces byte-identical output.  detect-secrets ignores
# this field for validation; it is informational metadata only.
PINNED_GENERATED_AT = "1970-01-01T00:00:00Z"

DEFAULT_BASELINE = ".secrets.baseline"


def normalize(baseline: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with every per-entry ``line_number`` stripped and
    ``generated_at`` pinned.  All verdict-relevant fields
    (``filename`` / ``hashed_secret`` / ``type`` / ``is_verified``) are kept.
    """
    output = dict(baseline)
    results: dict[str, Any] = {}
    for filename, secrets in baseline.get("results", {}).items():
        results[filename] = [
            {key: value for key, value in secret.items() if key != "line_number"}
            for secret in secrets
        ]
    output["results"] = results
    output["generated_at"] = PINNED_GENERATED_AT
    return output


def _line_number_count(baseline: dict[str, Any]) -> int:
    return sum(
        1
        for secrets in baseline.get("results", {}).values()
        for secret in secrets
        if "line_number" in secret
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize .secrets.baseline to the line-number-free, "
            "clock-independent form the detect-secrets hook validates against."
        )
    )
    parser.add_argument(
        "--baseline",
        default=DEFAULT_BASELINE,
        help=f"baseline file to normalize (default: {DEFAULT_BASELINE})",
    )
    args = parser.parse_args(argv)

    path = Path(args.baseline)
    try:
        baseline = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"::error::could not read baseline {path}: {exc}")
        return 1

    stripped = _line_number_count(baseline)
    normalized = normalize(baseline)
    if normalized == baseline:
        print(
            f"{path}: already normalized "
            f"(no line_number fields, generated_at pinned to {PINNED_GENERATED_AT})"
        )
        return 0

    path.write_text(json.dumps(normalized, indent=2) + "\n")
    print(
        f"{path}: normalized — removed {stripped} line_number field(s), "
        f"pinned generated_at to {PINNED_GENERATED_AT}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
