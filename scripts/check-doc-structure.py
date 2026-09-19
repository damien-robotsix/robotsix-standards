#!/usr/bin/env python3
"""Doc-structure gate: every rule standard page states a failure mode.

AGENT.md codifies a hard rule — *"Every rule added to a standard states the
failure it prevents."* This script is the mechanical gate for it (parity with
the aspiration/standard doctrine in docs/mill-agents.md). It parses the
mkdocs.yml nav, enumerates every page, and — for every page that is not in the
explicit ``EXEMPT`` set — checks that the page states at least one failure mode
in one of the phrasings the corpus already uses.

A non-exempt page passes iff its content states a failure mode in any phrasing
the corpus uses — i.e. it contains (case-insensitive) the phrase ``failure
mode`` / ``failure modes`` or ``failure prevented`` anywhere. This deliberately
accepts every structural variant in the tree:

- a heading, e.g. ``## Failure modes this prevents`` / ``## Failure prevented``;
- an inline bold marker, e.g. ``**Failure mode:**`` / ``**Failure prevented:**``;
- an inline italic marker, e.g. ``*Failure prevented:*``;
- plain prose, e.g. "two failure modes the old setup allowed".

The corpus uses ~17 phrasing variants and AGENT.md deliberately preserves
structural freedom, so the gate matches the *statement*, not a single rigid
heading. This mirrors the divergent-page discovery command
(``git grep -L -i -e 'failure mode' -e 'failure prevented'``).

Exits 0 when every non-exempt page states a failure mode, 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml  # type: ignore[import-untyped]

REPO_ROOT = Path(__file__).resolve().parent.parent

MKDOCS_YML = REPO_ROOT / "mkdocs.yml"
DOCS_DIR = REPO_ROOT / "docs"

# Pages that legitimately carry no rules of their own, so the failure-mode rule
# does not apply. One justification comment per entry.
EXEMPT = frozenset(
    {
        "index.md",  # site landing page — links, no rules
        "fleet.md",  # fleet status/overview page — no rules
        "CHANGELOG.md",  # generated release notes — no rules
        "mill-agents.md",  # Meta nav: repo-operational, not a fleet standard
        "towncrier.md",  # superseded/historical page
        "changelog-driven-releases.md",  # superseded/historical page
        "config-ownership-audit.md",  # audit snapshot — no rules of its own
        "integrating-a-service.md",  # task-oriented how-to; rules live in linked pages
        "deploy-contract.md",  # pointer page; canonical doc in robotsix-central-deploy
    }
)

# A failure-mode statement in any phrasing: the phrase `failure mode(s)` or
# `failure prevented`, case-insensitive, in a heading, bold/italic marker, or
# plain prose. Mirrors the `git grep -i -e 'failure mode' -e 'failure
# prevented'` command used to enumerate divergent pages.
MARKER_RE = re.compile(r"failure\s+(modes?|prevented)", re.IGNORECASE)

ACCEPTED_PHRASINGS = (
    "a 'failure mode(s)' / 'failure prevented' statement in any form — a "
    "'## Failure modes this prevents' heading, a '**Failure mode:**' bold "
    "marker, a '*Failure prevented:*' italic marker, or inline prose"
)


def extract_pages(nav: list[object]) -> list[str]:
    """Return every page filename referenced anywhere in the *nav* (recursive)."""
    pages: list[str] = []
    for item in nav:
        if isinstance(item, str):
            pages.append(item)
        elif isinstance(item, dict):
            for value in item.values():
                if isinstance(value, str):
                    pages.append(value)
                elif isinstance(value, list):
                    pages.extend(extract_pages(value))
    return pages


def page_states_failure_mode(content: str) -> bool:
    """True iff *content* states a failure mode in an accepted phrasing."""
    return bool(MARKER_RE.search(content))


def main() -> int:
    with MKDOCS_YML.open() as fh:
        config = yaml.safe_load(fh)

    nav: list[object] = config.get("nav", [])
    pages = sorted(set(extract_pages(nav)))

    checked = 0
    failing: list[str] = []
    for page in pages:
        if page in EXEMPT:
            continue
        path = DOCS_DIR / page
        if not path.exists():
            print(f"WARNING: nav page not found on disk, skipping: {page}")
            continue
        checked += 1
        if not page_states_failure_mode(path.read_text()):
            failing.append(page)

    print(f"Checked {checked} non-exempt page(s) for failure-mode statements ...")

    if failing:
        for page in failing:
            print(f"  MISSING failure-mode statement: docs/{page}")
        print(
            f"\n{len(failing)} page(s) state no failure mode.  Each rule "
            "standard page must state the failure it prevents "
            f"({ACCEPTED_PHRASINGS})."
        )
        return 1

    print("All rule standard pages state a failure mode.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
