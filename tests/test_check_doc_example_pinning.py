"""Unit tests for the doc-example pinning gate (scripts/check-doc-example-pinning.py).

Covers tag-pinned and branch-pinned ``uses:`` refs (fail), the ``@<sha>``
placeholder with a version comment and a real 40-char SHA (pass), prose
mentions outside fenced blocks (ignored), a ``uses:``-free doc (pass), and
main()'s exit codes against a mini docs tree and the real repo tree.
"""

from __future__ import annotations

from pathlib import Path

SHA = "86dae89b637dad27ddba0aaa5f9430e083288365"


def _fenced(line: str) -> str:
    return f"# Page\n\n```yaml\nsteps:\n  {line}\n```\n"


def test_tag_pinned_uses_fails(check_doc_example_pinning):
    assert check_doc_example_pinning.find_mutable_refs(
        _fenced("- uses: actions/checkout@v4")
    ) == [5]


def test_dotted_tag_without_v_fails(check_doc_example_pinning):
    assert check_doc_example_pinning.find_mutable_refs(
        _fenced("- uses: foo/bar@3.1.0")
    ) == [5]


def test_sha_placeholder_with_version_comment_passes(check_doc_example_pinning):
    assert (
        check_doc_example_pinning.find_mutable_refs(
            _fenced("- uses: hadolint/hadolint-action@<sha>  # v3.1.0")
        )
        == []
    )


def test_real_sha_pin_passes(check_doc_example_pinning):
    assert (
        check_doc_example_pinning.find_mutable_refs(
            _fenced(f"- uses: actions/checkout@{SHA}  # v4")
        )
        == []
    )


def test_main_branch_ref_fails(check_doc_example_pinning):
    assert check_doc_example_pinning.find_mutable_refs(
        _fenced("- uses: foo/bar@main")
    ) == [5]


def test_master_branch_ref_fails(check_doc_example_pinning):
    assert check_doc_example_pinning.find_mutable_refs(
        _fenced("uses: org/repo/.github/workflows/x.yml@master")
    ) == [5]


def test_version_comment_after_hash_ignored(check_doc_example_pinning):
    assert (
        check_doc_example_pinning.find_mutable_refs(
            _fenced("- uses: foo/bar@<sha>  # was uses: foo/bar@v1")
        )
        == []
    )


def test_prose_outside_fence_ignored(check_doc_example_pinning):
    content = "Prose mentioning `uses: actions/cache@v4` inline.\n"
    assert check_doc_example_pinning.find_mutable_refs(content) == []


def test_doc_without_uses_passes(check_doc_example_pinning):
    content = "# Page\n\n```bash\nuv sync\n```\n\nNo actions here.\n"
    assert check_doc_example_pinning.find_mutable_refs(content) == []


def test_tilde_fence_is_scanned(check_doc_example_pinning):
    content = "~~~yaml\n- uses: foo/bar@v1\n~~~\n"
    assert check_doc_example_pinning.find_mutable_refs(content) == [2]


def test_main_clean_tree(tmp_path: Path, check_doc_example_pinning, monkeypatch):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text(_fenced("- uses: foo/bar@<sha>  # v1"))
    (docs / "b.md").write_text("# No uses here\n")
    monkeypatch.setattr(check_doc_example_pinning, "DOCS_DIR", docs)
    assert check_doc_example_pinning.main() == 0


def test_main_flags_mutable_ref(
    tmp_path: Path, check_doc_example_pinning, monkeypatch, capsys
):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text(_fenced("- uses: foo/bar@v1"))
    monkeypatch.setattr(check_doc_example_pinning, "DOCS_DIR", docs)
    assert check_doc_example_pinning.main() == 1
    assert "docs/a.md:5" in capsys.readouterr().out


def test_main_real_repo_tree_passes(check_doc_example_pinning):
    assert check_doc_example_pinning.main() == 0
