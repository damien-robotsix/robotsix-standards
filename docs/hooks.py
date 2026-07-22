"""MkDocs build-time hooks.

Surface the root CHANGELOG.md inside docs_dir so it can appear in the nav,
rewriting repo-root-relative doc links (``docs/foo.md`` → ``foo.md``) so they
resolve correctly from within ``docs/``.
"""

from __future__ import annotations

import re
from pathlib import Path


def on_pre_build(**kwargs) -> None:  # noqa: ANN003, ARG001
    """Copy root CHANGELOG.md into docs/ with link rewriting."""
    repo_root = Path(__file__).resolve().parent.parent
    changelog_src = repo_root / "CHANGELOG.md"
    changelog_dst = repo_root / "docs" / "CHANGELOG.md"

    content = changelog_src.read_text()

    # Rewrite docs/foo.md → foo.md (repo-root-relative doc links to
    # docs_dir-relative).
    content = re.sub(r"\]\(docs/([^)]+\.md)\)", r"](\1)", content)

    changelog_dst.write_text(content)
