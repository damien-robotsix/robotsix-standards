"""Unit tests for the detect-secrets baseline normalizer.

Covers scripts/normalize-secrets-baseline.py: stripping the per-entry
``line_number`` (informational only — detect-secrets validates by
``filename`` + ``hashed_secret``) and pinning ``generated_at`` so the committed
baseline is insensitive to line-number / clock drift, plus idempotence and the
exit codes of main().  See docs/secret-files-are-never-tracked.md.
"""

from __future__ import annotations

import json

PINNED = "1970-01-01T00:00:00Z"

# A baseline as detect-secrets regenerates it: per-entry line numbers and a
# wall-clock generated_at.
LINE_NUMBERED = {
    "version": "1.5.0",
    "plugins_used": [{"name": "AWSKeyDetector"}],
    "filters_used": [{"path": "detect_secrets.filters.common.is_baseline_file"}],
    "results": {
        "docs/a.md": [
            {
                "type": "Secret Keyword",
                "filename": "docs/a.md",
                "hashed_secret": "abc123",  # pragma: allowlist secret
                "is_verified": False,
                "line_number": 357,
            }
        ]
    },
    "generated_at": "2026-11-21T05:26:24Z",
}


def test_normalize_strips_line_number_and_pins_timestamp(
    normalize_secrets_baseline,
):
    out = normalize_secrets_baseline.normalize(LINE_NUMBERED)
    entry = out["results"]["docs/a.md"][0]
    assert "line_number" not in entry
    # Verdict-relevant fields are untouched.
    assert entry["hashed_secret"] == "abc123"
    assert entry["is_verified"] is False
    assert entry["type"] == "Secret Keyword"
    assert out["generated_at"] == PINNED
    assert out["version"] == "1.5.0"
    assert out["plugins_used"] == LINE_NUMBERED["plugins_used"]


def test_normalize_is_idempotent(normalize_secrets_baseline):
    once = normalize_secrets_baseline.normalize(LINE_NUMBERED)
    twice = normalize_secrets_baseline.normalize(once)
    assert twice == once


def test_main_rewrites_a_line_numbered_baseline(
    tmp_path, normalize_secrets_baseline, capsys
):
    path = tmp_path / ".secrets.baseline"
    path.write_text(json.dumps(LINE_NUMBERED))
    assert normalize_secrets_baseline.main(["--baseline", str(path)]) == 0
    out = json.loads(path.read_text())
    assert "line_number" not in out["results"]["docs/a.md"][0]
    assert out["generated_at"] == PINNED
    stdout = capsys.readouterr().out
    assert "removed 1 line_number field" in stdout
    assert "pinned generated_at" in stdout


def test_main_noop_when_already_normalized(
    tmp_path, normalize_secrets_baseline, capsys
):
    path = tmp_path / ".secrets.baseline"
    normalized = normalize_secrets_baseline.normalize(LINE_NUMBERED)
    canonical = json.dumps(normalized, indent=2) + "\n"
    path.write_text(canonical)
    mtime_ns = path.stat().st_mtime_ns
    assert normalize_secrets_baseline.main(["--baseline", str(path)]) == 0
    # Idempotent: the already-canonical file is left byte-identical (content
    # normalized AND trailing newline present).
    assert path.read_text() == canonical
    assert path.stat().st_mtime_ns == mtime_ns
    assert "already normalized" in capsys.readouterr().out


def test_main_restores_missing_trailing_newline(
    tmp_path, normalize_secrets_baseline, capsys
):
    path = tmp_path / ".secrets.baseline"
    normalized = normalize_secrets_baseline.normalize(LINE_NUMBERED)
    # Content is already line-number-free / pinned, but the file does not end
    # with a newline (as a detect-secrets regeneration or a copy-paste commit
    # can leave it).  The normalizer must restore the canonical trailing
    # newline so a stock `end-of-file-fixer` cannot rewrite the committed
    # baseline and reintroduce the 'files were modified by this hook' churn.
    path.write_text(json.dumps(normalized, indent=2))
    assert normalize_secrets_baseline.main(["--baseline", str(path)]) == 0
    canonical = json.dumps(normalized, indent=2) + "\n"
    assert path.read_text() == canonical
    out = capsys.readouterr().out
    assert "restored canonical trailing newline" in out
    # Content was already normalized, so only the newline change is reported.
    assert "line_number" not in out


def test_main_fails_on_missing_file(tmp_path, normalize_secrets_baseline):
    missing = tmp_path / "does-not-exist.json"
    assert normalize_secrets_baseline.main(["--baseline", str(missing)]) == 1
