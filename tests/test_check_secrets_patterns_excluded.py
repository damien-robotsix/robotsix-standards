"""Unit tests for the ``.secrets-patterns-excluded`` gate.

Covers scripts/check-secrets-patterns-excluded.py: the pattern-line parse
(comments and blanks dropped), regex validation (a gitignore glob is rejected),
detection of the no-op ``--exclude-files <file>`` detect-secrets wiring, and
the warning-first main() (which always exits 0 while emitting ``::warning::``
annotations).  See docs/secret-files-are-never-tracked.md.
"""

from __future__ import annotations

VALID_PATTERNS = """\
# Directories that never contain secrets.
^tests/fixtures/
^docs/examples/
^vendor/
"""

# Gitignore globs that are not valid regexes: a leading `*` has nothing to
# repeat, and an unclosed `[` is a bad character class.
GLOB_SYNTAX = """\
# Wrong: gitignore globs, not regexes.
*secret*
tests/[fixtures
"""

PRECOMMIT_NOOP_SPLIT = """\
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args:
          - '--exclude-files'
          - '.secrets-patterns-excluded'
          - '--baseline'
          - '.secrets.baseline'
"""

PRECOMMIT_NOOP_INLINE = """\
        entry: detect-secrets-hook --exclude-files .secrets-patterns-excluded
"""

PRECOMMIT_CLEAN = """\
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args:
          - '--baseline'
          - '.secrets.baseline'
        exclude: '\\.secrets\\.baseline$'
"""


def test_pattern_lines_drops_comments_and_blanks(check_secrets_patterns_excluded):
    text = "# a comment\n\n^vendor/\n  ^tests/  \n"
    assert check_secrets_patterns_excluded.pattern_lines(text) == [
        "^vendor/",
        "^tests/",
    ]


def test_valid_patterns_have_no_invalid(check_secrets_patterns_excluded):
    assert check_secrets_patterns_excluded.invalid_patterns(VALID_PATTERNS) == []


def test_glob_syntax_is_flagged_invalid(check_secrets_patterns_excluded):
    bad = check_secrets_patterns_excluded.invalid_patterns(GLOB_SYNTAX)
    assert "*secret*" in bad
    assert "tests/[fixtures" in bad


def test_detect_secrets_noop_split_form(check_secrets_patterns_excluded):
    assert check_secrets_patterns_excluded.detect_secrets_noop(PRECOMMIT_NOOP_SPLIT)


def test_detect_secrets_noop_inline_form(check_secrets_patterns_excluded):
    assert check_secrets_patterns_excluded.detect_secrets_noop(PRECOMMIT_NOOP_INLINE)


def test_detect_secrets_clean_wiring_not_flagged(check_secrets_patterns_excluded):
    assert not check_secrets_patterns_excluded.detect_secrets_noop(PRECOMMIT_CLEAN)


# ---------------------------------------------------------------------------
# main(): warning-first end-to-end gate
# ---------------------------------------------------------------------------


def _wire(monkeypatch, mod, tmp_path, patterns_text=None, precommit_text=None):
    patterns = tmp_path / ".secrets-patterns-excluded"
    if patterns_text is not None:
        patterns.write_text(patterns_text)
    precommit = tmp_path / ".pre-commit-config.yaml"
    precommit.write_text(precommit_text if precommit_text is not None else "")
    monkeypatch.setattr(mod, "PATTERNS_FILE", patterns)
    monkeypatch.setattr(mod, "PRECOMMIT", precommit)


def test_main_ok_when_valid_and_clean(
    tmp_path, check_secrets_patterns_excluded, monkeypatch, capsys
):
    _wire(
        monkeypatch,
        check_secrets_patterns_excluded,
        tmp_path,
        patterns_text=VALID_PATTERNS,
        precommit_text=PRECOMMIT_CLEAN,
    )
    assert check_secrets_patterns_excluded.main() == 0
    out = capsys.readouterr().out
    assert "OK" in out
    assert "::warning::" not in out


def test_main_warns_when_file_missing(
    tmp_path, check_secrets_patterns_excluded, monkeypatch, capsys
):
    _wire(
        monkeypatch,
        check_secrets_patterns_excluded,
        tmp_path,
        patterns_text=None,
        precommit_text=PRECOMMIT_CLEAN,
    )
    assert check_secrets_patterns_excluded.main() == 0
    assert "missing at repo root" in capsys.readouterr().out


def test_main_warns_on_glob_and_noop_wiring(
    tmp_path, check_secrets_patterns_excluded, monkeypatch, capsys
):
    _wire(
        monkeypatch,
        check_secrets_patterns_excluded,
        tmp_path,
        patterns_text=GLOB_SYNTAX,
        precommit_text=PRECOMMIT_NOOP_SPLIT,
    )
    # Warning-first: exit 0 even with problems present.
    assert check_secrets_patterns_excluded.main() == 0
    out = capsys.readouterr().out
    assert "not a valid regular expression" in out
    assert "silent no-op" in out
