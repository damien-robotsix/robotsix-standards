"""Unit tests for the doc-structure gate (scripts/check-doc-structure.py).

Covers the accepted phrasings (heading form, inline bold form, italic/prose
form), a failing page that states no failure mode, exempt pages being skipped,
the recursive nav extraction, and main()'s exit codes against a mini docs tree
and against the real repo tree (which must be 0 post-remediation).
"""

from __future__ import annotations

from pathlib import Path

import yaml

NAV_YAML = """\
nav:
  - Home: index.md
  - Every repo:
      - Repo baseline: repo-baseline.md
      - Nested section:
          - Deep page: deep.md
  - Meta:
      - Mill agents: mill-agents.md
"""

HEADING_PAGE = """\
# Repo baseline

Some rule text.

## Failure modes this prevents

- Something bad happens without the rule.
"""

BOLD_PAGE = """\
# Deep page

A rule with an inline marker.

**Failure mode:** the container never shuts down cleanly.
"""

# Deliberately contains neither "failure mode(s)" nor "failure prevented".
FAILING_PAGE = """\
# A page with rules but no stated consequence

Do this. Do that. No stated consequence anywhere.
"""

PROSE_PAGE = """\
# A page stating consequences in prose

These approaches work but they share two failure modes: A and B.
"""

ITALIC_PAGE = """\
# A page with an italic marker

Set the flag. *Failure prevented:* the process leaks a file descriptor.
"""

# index.md and mill-agents.md are exempt, so their content is irrelevant.
EXEMPT_STUB = "# Exempt\n\nNo rules here.\n"


def _write_tree(
    tmp_path: Path,
    *,
    repo_baseline: str = HEADING_PAGE,
    deep: str = BOLD_PAGE,
) -> tuple[Path, Path]:
    """Write mkdocs.yml + docs/ and return (mkdocs path, docs dir)."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (tmp_path / "mkdocs.yml").write_text(NAV_YAML)
    (docs / "index.md").write_text(EXEMPT_STUB)
    (docs / "mill-agents.md").write_text(EXEMPT_STUB)
    (docs / "repo-baseline.md").write_text(repo_baseline)
    (docs / "deep.md").write_text(deep)
    return tmp_path / "mkdocs.yml", docs


def _point_at(tmp_path, check_doc_structure, monkeypatch, **kwargs):
    mkdocs, docs = _write_tree(tmp_path, **kwargs)
    monkeypatch.setattr(check_doc_structure, "MKDOCS_YML", mkdocs)
    monkeypatch.setattr(check_doc_structure, "DOCS_DIR", docs)


# ---------------------------------------------------------------------------
# extract_pages / page_states_failure_mode
# ---------------------------------------------------------------------------


def test_extract_pages_is_recursive(check_doc_structure):
    nav = yaml.safe_load(NAV_YAML)["nav"]
    pages = check_doc_structure.extract_pages(nav)
    assert set(pages) == {
        "index.md",
        "repo-baseline.md",
        "deep.md",
        "mill-agents.md",
    }


def test_heading_form_passes(check_doc_structure):
    assert check_doc_structure.page_states_failure_mode(HEADING_PAGE)


def test_inline_bold_form_passes(check_doc_structure):
    assert check_doc_structure.page_states_failure_mode(BOLD_PAGE)


def test_failure_prevented_heading_variant_passes(check_doc_structure):
    assert check_doc_structure.page_states_failure_mode(
        "## Failure prevented\n\nbody\n"
    )


def test_case_insensitive_match(check_doc_structure):
    assert check_doc_structure.page_states_failure_mode(
        "**FAILURE MODE:** shouted but still valid"
    )


def test_italic_marker_passes(check_doc_structure):
    assert check_doc_structure.page_states_failure_mode(ITALIC_PAGE)


def test_prose_statement_passes(check_doc_structure):
    assert check_doc_structure.page_states_failure_mode(PROSE_PAGE)


def test_page_without_failure_mode_fails(check_doc_structure):
    assert not check_doc_structure.page_states_failure_mode(FAILING_PAGE)


# ---------------------------------------------------------------------------
# main(): mini-tree happy path, failure edge, exempt-skip
# ---------------------------------------------------------------------------


def test_main_happy_path(tmp_path, check_doc_structure, monkeypatch):
    _point_at(tmp_path, check_doc_structure, monkeypatch)
    assert check_doc_structure.main() == 0


def test_main_flags_missing_failure_mode(
    tmp_path, check_doc_structure, monkeypatch, capsys
):
    _point_at(tmp_path, check_doc_structure, monkeypatch, repo_baseline=FAILING_PAGE)
    assert check_doc_structure.main() == 1
    out = capsys.readouterr().out
    assert "MISSING failure-mode statement: docs/repo-baseline.md" in out


def test_main_skips_exempt_pages(tmp_path, check_doc_structure, monkeypatch):
    # index.md and mill-agents.md carry no failure mode, but both are exempt,
    # so a tree whose only non-exempt pages conform still passes.
    _point_at(tmp_path, check_doc_structure, monkeypatch)
    assert "index.md" in check_doc_structure.EXEMPT
    assert "mill-agents.md" in check_doc_structure.EXEMPT
    assert check_doc_structure.main() == 0


# ---------------------------------------------------------------------------
# main(): the real repo tree must pass post-remediation
# ---------------------------------------------------------------------------


def test_main_real_repo_tree_passes(check_doc_structure):
    assert check_doc_structure.main() == 0
