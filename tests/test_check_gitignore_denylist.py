"""Unit tests for the credential/secret-file deny-list gate.

Covers scripts/check-gitignore-denylist.py: the positive-pattern parse
(negations and comments dropped), the coverage decision for each deny-list
requirement, honoring of ``!`` negating exceptions, and the warning-first
main() (which always exits 0 while emitting ``::warning::`` annotations for
missing patterns).  See docs/security-posture.md gate 5.
"""

from __future__ import annotations

# A .gitignore that satisfies every deny-list requirement. ``.env*`` covers
# both ``.env`` and ``.env.*``; ``wp-config*.php`` covers both wp-config forms.
COMPLETE = """\
# Credential & secret files (docs/security-posture.md gate 5)
.htpasswd
.env
.env.*
wp-config.php
wp-config*.php
*.pem
*.key
*secret*
*.p12
"""

# Umbrella spellings that still cover every requirement in fewer lines.
COMPLETE_UMBRELLA = """\
.htpasswd
.env
.env*
wp-config*.php
*.pem
*.key
*secret*
*.p12
"""

MISSING_SOME = """\
# Missing wp-config*, *secret* and *.p12
.htpasswd
.env
.env.*
*.pem
*.key
"""


def test_positive_patterns_drops_comments_and_negations(check_gitignore_denylist):
    text = "# a comment\n\n*.pem\n!public-cert.pem\n  *.key  \n"
    assert check_gitignore_denylist.positive_patterns(text) == ["*.pem", "*.key"]


def test_positive_patterns_normalizes_anchoring(check_gitignore_denylist):
    text = "/.env\n**/*.key\nbuild/\n"
    assert check_gitignore_denylist.positive_patterns(text) == [
        ".env",
        "*.key",
        "build",
    ]


def test_complete_gitignore_has_no_missing(check_gitignore_denylist):
    assert check_gitignore_denylist.missing_requirements(COMPLETE) == []


def test_umbrella_spellings_cover_everything(check_gitignore_denylist):
    assert check_gitignore_denylist.missing_requirements(COMPLETE_UMBRELLA) == []


def test_missing_requirements_reports_gaps(check_gitignore_denylist):
    missing = check_gitignore_denylist.missing_requirements(MISSING_SOME)
    assert "wp-config*.php" in missing
    assert "*secret*" in missing
    assert "*.p12" in missing
    # wp-config.php is also uncovered here.
    assert "wp-config.php" in missing


def test_bare_env_does_not_cover_env_suffix(check_gitignore_denylist):
    # A bare `.env` entry must not satisfy the `.env.*` requirement.
    missing = check_gitignore_denylist.missing_requirements(".env\n")
    assert ".env.*" in missing
    assert ".env" not in missing


def test_negation_does_not_count_as_coverage(check_gitignore_denylist):
    # A negating exception alone provides no coverage — the umbrella pattern
    # must still be present.
    missing = check_gitignore_denylist.missing_requirements("!keep.pem\n")
    assert "*.pem" in missing


def test_negation_is_honored_when_umbrella_present(check_gitignore_denylist):
    # A repo that deliberately tracks a public cert negates just that file;
    # the umbrella `*.pem` still counts as coverage.
    text = "*.pem\n!public-cert.pem\n"
    assert "*.pem" not in check_gitignore_denylist.missing_requirements(text)


def test_empty_gitignore_reports_all(check_gitignore_denylist):
    missing = check_gitignore_denylist.missing_requirements("")
    labels = {label for label, _ in check_gitignore_denylist.REQUIREMENTS}
    assert set(missing) == labels


# ---------------------------------------------------------------------------
# main(): warning-first end-to-end gate
# ---------------------------------------------------------------------------


def test_main_ok_when_complete(tmp_path, check_gitignore_denylist, monkeypatch, capsys):
    gi = tmp_path / ".gitignore"
    gi.write_text(COMPLETE)
    monkeypatch.setattr(check_gitignore_denylist, "GITIGNORE", gi)
    assert check_gitignore_denylist.main() == 0
    out = capsys.readouterr().out
    assert "OK" in out
    assert "::warning::" not in out


def test_main_warns_but_passes_when_missing(
    tmp_path, check_gitignore_denylist, monkeypatch, capsys
):
    gi = tmp_path / ".gitignore"
    gi.write_text(MISSING_SOME)
    monkeypatch.setattr(check_gitignore_denylist, "GITIGNORE", gi)
    # Warning-first: exit 0 even with missing patterns.
    assert check_gitignore_denylist.main() == 0
    out = capsys.readouterr().out
    assert "::warning::" in out
    assert "*.p12" in out


def test_main_warns_when_gitignore_absent(
    tmp_path, check_gitignore_denylist, monkeypatch, capsys
):
    monkeypatch.setattr(check_gitignore_denylist, "GITIGNORE", tmp_path / ".gitignore")
    assert check_gitignore_denylist.main() == 0
    assert "::warning::" in capsys.readouterr().out
