"""Unit tests for the ``.secrets-patterns-excluded`` gate.

Covers scripts/check-secrets-patterns-excluded.py: the pattern-line parse
(comments and blanks dropped), regex validation (a gitignore glob is rejected),
detection of the no-op ``--exclude-files <file>`` detect-secrets wiring, the
drift-free-shape check on the committed baseline (no per-entry ``line_number``,
pinned ``generated_at``), and the dated rollout of main() (exit 0 with
``::warning::`` annotations before 2027-01-31, exit 1 with ``::error::``
annotations from then).  See docs/secret-files-are-never-tracked.md.
"""

from __future__ import annotations

import datetime as _dt
import json

BEFORE = _dt.date(2027, 1, 30)
ON = _dt.date(2027, 1, 31)

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

# The drift-free committed baseline: no per-entry line_number, pinned
# generated_at (see scripts/normalize-secrets-baseline.py).
NORMALIZED_BASELINE = json.dumps(
    {
        "version": "1.5.0",
        "results": {
            "docs/a.md": [
                {"type": "Secret Keyword", "hashed_secret": "abc", "is_verified": False}
            ]
        },
        "generated_at": "1970-01-01T00:00:00Z",
    }
)

# What `detect-secrets scan --baseline` writes back: line numbers and a
# wall-clock timestamp — the churn the gate must catch.
LINE_NUMBERED_BASELINE = json.dumps(
    {
        "version": "1.5.0",
        "results": {
            "docs/a.md": [
                {
                    "type": "Secret Keyword",
                    "hashed_secret": "abc",
                    "is_verified": False,
                    "line_number": 357,
                }
            ]
        },
        "generated_at": "2026-11-21T05:26:24Z",
    }
)


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
# baseline_violations(): drift-free baseline shape
# ---------------------------------------------------------------------------


def test_baseline_violations_none_when_normalized(check_secrets_patterns_excluded):
    assert (
        check_secrets_patterns_excluded.baseline_violations(NORMALIZED_BASELINE) == []
    )


def test_baseline_violations_flag_line_numbers(check_secrets_patterns_excluded):
    violations = check_secrets_patterns_excluded.baseline_violations(
        LINE_NUMBERED_BASELINE
    )
    assert any("line_number" in violation for violation in violations)


def test_baseline_violations_flag_wall_clock_timestamp(check_secrets_patterns_excluded):
    text = NORMALIZED_BASELINE.replace("1970-01-01T00:00:00Z", "2026-11-21T05:26:24Z")
    violations = check_secrets_patterns_excluded.baseline_violations(text)
    assert any("generated_at" in violation for violation in violations)


def test_baseline_violations_flag_unparsable(check_secrets_patterns_excluded):
    violations = check_secrets_patterns_excluded.baseline_violations("{not json")
    assert any("JSON" in violation for violation in violations)


# ---------------------------------------------------------------------------
# main(): dated warning-first -> blocking end-to-end gate
# ---------------------------------------------------------------------------


def _wire(
    monkeypatch,
    mod,
    tmp_path,
    patterns_text=None,
    precommit_text=None,
    baseline_text=None,
):
    patterns = tmp_path / ".secrets-patterns-excluded"
    if patterns_text is not None:
        patterns.write_text(patterns_text)
    precommit = tmp_path / ".pre-commit-config.yaml"
    precommit.write_text(precommit_text if precommit_text is not None else "")
    baseline = tmp_path / ".secrets.baseline"
    if baseline_text is not None:
        baseline.write_text(baseline_text)
    monkeypatch.setattr(mod, "PATTERNS_FILE", patterns)
    monkeypatch.setattr(mod, "PRECOMMIT", precommit)
    monkeypatch.setattr(mod, "BASELINE", baseline)


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
    assert check_secrets_patterns_excluded.main(today=BEFORE) == 0
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
    assert check_secrets_patterns_excluded.main(today=BEFORE) == 0
    out = capsys.readouterr().out
    assert "not a valid regular expression" in out
    assert "silent no-op" in out
    assert "::warning::" in out


def test_main_warns_on_line_numbered_baseline(
    tmp_path, check_secrets_patterns_excluded, monkeypatch, capsys
):
    _wire(
        monkeypatch,
        check_secrets_patterns_excluded,
        tmp_path,
        patterns_text=VALID_PATTERNS,
        precommit_text=PRECOMMIT_CLEAN,
        baseline_text=LINE_NUMBERED_BASELINE,
    )
    assert check_secrets_patterns_excluded.main(today=BEFORE) == 0
    out = capsys.readouterr().out
    assert "line_number" in out
    assert "normalize-secrets-baseline" in out
    assert "::warning::" in out


def test_main_ok_with_normalized_baseline(
    tmp_path, check_secrets_patterns_excluded, monkeypatch, capsys
):
    _wire(
        monkeypatch,
        check_secrets_patterns_excluded,
        tmp_path,
        patterns_text=VALID_PATTERNS,
        precommit_text=PRECOMMIT_CLEAN,
        baseline_text=NORMALIZED_BASELINE,
    )
    assert check_secrets_patterns_excluded.main(today=ON) == 0
    out = capsys.readouterr().out
    assert "OK" in out
    assert "::warning::" not in out
    assert "::error::" not in out


def test_main_blocks_from_blocking_date(
    tmp_path, check_secrets_patterns_excluded, monkeypatch, capsys
):
    _wire(
        monkeypatch,
        check_secrets_patterns_excluded,
        tmp_path,
        patterns_text=GLOB_SYNTAX,
        precommit_text=PRECOMMIT_NOOP_SPLIT,
    )
    assert check_secrets_patterns_excluded.BLOCKING_FROM == ON
    assert check_secrets_patterns_excluded.main(today=ON) == 1
    out = capsys.readouterr().out
    assert "::error::" in out
    assert "::warning::" not in out


def test_main_ok_after_blocking_date_when_clean(
    tmp_path, check_secrets_patterns_excluded, monkeypatch
):
    _wire(
        monkeypatch,
        check_secrets_patterns_excluded,
        tmp_path,
        patterns_text=VALID_PATTERNS,
        precommit_text=PRECOMMIT_CLEAN,
    )
    assert check_secrets_patterns_excluded.main(today=ON) == 0
