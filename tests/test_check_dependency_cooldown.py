"""Unit tests for the dependency release-age cooldown gate.

Covers scripts/check-dependency-cooldown.py: Renovate ``minimumReleaseAge`` /
``internalChecksFilter`` on auto-merge rules, the security-update exemption,
Dependabot ``cooldown: default-days`` on auto-merge-eligible ecosystems, the
accepted-risk allowlist, and the dated rollout of main() (warning-first before
2027-01-31, blocking from then).  See docs/security-posture.md gate 3.
"""

from __future__ import annotations

import datetime as _dt
import json

BEFORE = _dt.date(2027, 1, 30)
ON = _dt.date(2027, 1, 31)

GOOD_RENOVATE = {
    "packageRules": [
        {
            "matchUpdateTypes": ["minor", "patch"],
            "automerge": True,
            "minimumReleaseAge": "3 days",
            "internalChecksFilter": "strict",
        },
        {
            "matchSourceUrls": ["https://github.com/damien-robotsix/**"],
            "minimumReleaseAge": None,
        },
    ],
    "vulnerabilityAlerts": {"minimumReleaseAge": None},
}

BAD_RENOVATE = {"packageRules": [{"matchUpdateTypes": ["minor"], "automerge": True}]}

GOOD_DEPENDABOT = """\
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    cooldown:
      default-days: 3
  - package-ecosystem: pre-commit
    directory: /
  - package-ecosystem: docker
    directory: /
"""

BAD_DEPENDABOT = """\
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
  - package-ecosystem: npm
    directory: /
    cooldown:
      default-days: 1
"""


def _setup(tmp_path, mod, monkeypatch, renovate=None, dependabot=None, allow=None):
    gh = tmp_path / ".github"
    gh.mkdir()
    if renovate is not None:
        (tmp_path / "renovate.json").write_text(json.dumps(renovate))
    if dependabot is not None:
        (gh / "dependabot.yml").write_text(dependabot)
    if allow is not None:
        (tmp_path / ".dependency-cooldown-allowlist").write_text(allow)
    monkeypatch.setattr(mod, "RENOVATE", tmp_path / "renovate.json")
    monkeypatch.setattr(
        mod, "DEPENDABOT_CANDIDATES", (gh / "dependabot.yml", gh / "dependabot.yaml")
    )
    monkeypatch.setattr(mod, "ALLOWLIST", tmp_path / ".dependency-cooldown-allowlist")


def test_duration_days(check_dependency_cooldown):
    d = check_dependency_cooldown.duration_days
    assert d("3 days") == 3
    assert d("1 week") == 7
    assert d("72 hours") == 3
    assert d("2d") == 2
    assert d(None) is None
    assert d("soon") is None


def test_good_renovate_has_no_problems(check_dependency_cooldown):
    assert check_dependency_cooldown.renovate_problems(GOOD_RENOVATE) == []


def test_bad_renovate_reports_age_and_filter(check_dependency_cooldown):
    problems = check_dependency_cooldown.renovate_problems(BAD_RENOVATE)
    assert any("minimumReleaseAge" in p for p in problems)
    assert any("internalChecksFilter" in p for p in problems)


def test_short_release_age_is_rejected(check_dependency_cooldown):
    cfg = {
        "packageRules": [
            {
                "automerge": True,
                "minimumReleaseAge": "1 day",
                "internalChecksFilter": "strict",
            }
        ]
    }
    assert len(check_dependency_cooldown.renovate_problems(cfg)) == 1


def test_top_level_settings_apply_to_rules(check_dependency_cooldown):
    cfg = {
        "minimumReleaseAge": "3 days",
        "internalChecksFilter": "strict",
        "packageRules": [{"automerge": True}],
    }
    assert check_dependency_cooldown.renovate_problems(cfg) == []


def test_delayed_vulnerability_alerts_are_rejected(check_dependency_cooldown):
    cfg = {"vulnerabilityAlerts": {"minimumReleaseAge": "3 days"}}
    problems = check_dependency_cooldown.renovate_problems(cfg)
    assert any("vulnerabilityAlerts" in p for p in problems)


def test_dependabot_skips_non_automerge_ecosystems(check_dependency_cooldown):
    import yaml

    cfg = yaml.safe_load(GOOD_DEPENDABOT)
    assert check_dependency_cooldown.dependabot_problems(cfg) == []


def test_dependabot_reports_missing_and_short_cooldown(check_dependency_cooldown):
    import yaml

    cfg = yaml.safe_load(BAD_DEPENDABOT)
    ecosystems = [eco for eco, _ in check_dependency_cooldown.dependabot_problems(cfg)]
    assert ecosystems == ["github-actions", "npm"]


def test_allowlist_requires_approval_reference(check_dependency_cooldown):
    text = "# comment\ngithub-actions approved in robotsix-standards#123\nnpm\n"
    assert check_dependency_cooldown.parse_allowlist(text) == {"github-actions"}


def test_main_ok_when_configured(
    tmp_path, check_dependency_cooldown, monkeypatch, capsys
):
    _setup(
        tmp_path, check_dependency_cooldown, monkeypatch, GOOD_RENOVATE, GOOD_DEPENDABOT
    )
    assert check_dependency_cooldown.main(today=ON) == 0
    assert "OK" in capsys.readouterr().out


def test_main_warns_before_blocking_date(
    tmp_path, check_dependency_cooldown, monkeypatch, capsys
):
    _setup(
        tmp_path, check_dependency_cooldown, monkeypatch, BAD_RENOVATE, BAD_DEPENDABOT
    )
    assert check_dependency_cooldown.main(today=BEFORE) == 0
    out = capsys.readouterr().out
    assert "::warning::" in out
    assert "::error::" not in out


def test_main_blocks_from_blocking_date(
    tmp_path, check_dependency_cooldown, monkeypatch, capsys
):
    _setup(
        tmp_path, check_dependency_cooldown, monkeypatch, BAD_RENOVATE, BAD_DEPENDABOT
    )
    assert check_dependency_cooldown.BLOCKING_FROM == ON
    assert check_dependency_cooldown.main(today=ON) == 1
    assert "::error::" in capsys.readouterr().out


def test_main_honors_accepted_risk(tmp_path, check_dependency_cooldown, monkeypatch):
    _setup(
        tmp_path,
        check_dependency_cooldown,
        monkeypatch,
        BAD_RENOVATE,
        BAD_DEPENDABOT,
        allow="renovate approved in robotsix-standards#1\n"
        "github-actions approved in robotsix-standards#1\n"
        "npm approved in robotsix-standards#1\n",
    )
    assert check_dependency_cooldown.main(today=ON) == 0


def test_repo_own_config_passes(check_dependency_cooldown):
    # This repo's renovate.json / dependabot.yml must satisfy its own gate.
    assert check_dependency_cooldown.collect_problems() == []
