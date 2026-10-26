"""Unit tests for the public-registry gate.

Covers scripts/check-public-registry.py: each row of the pattern table in
docs/distribution-packaging.md § Enforcement, the approved internal-domain
exemption, the per-repo allow-list, and the warning-first rollout that turns
blocking on 2027-01-31.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

WF = ".github/workflows/release.yml"


def _rules(findings):
    return sorted(f.rule for f in findings)


def test_npm_publish_without_registry_flagged(check_public_registry):
    text = "jobs:\n  p:\n    steps:\n      - run: npm publish\n"
    assert _rules(check_public_registry.scan_workflow(WF, text)) == ["npm-publish"]


def test_npm_publish_to_internal_registry_ok(check_public_registry):
    text = "      - run: npm publish --registry https://npm.pkg.github.com\n"
    assert check_public_registry.scan_workflow(WF, text) == []


def test_npm_publish_continuation_line_joined(check_public_registry):
    text = "      run: npm publish \\\n        --registry=https://npm.pkg.github.com\n"
    assert check_public_registry.scan_workflow(WF, text) == []


def test_python_publish_flagged(check_public_registry):
    text = "      - run: uv publish\n      - run: twine upload dist/*\n"
    assert _rules(check_public_registry.scan_workflow(WF, text)) == [
        "python-publish",
        "python-publish",
    ]


def test_public_endpoints_action_and_tokens_flagged(check_public_registry):
    text = (
        "      - uses: pypa/gh-action-pypi-publish@abc\n"
        "        with:\n"
        "          repository-url: https://upload.pypi.org/legacy/\n"
        "          password: ${{ secrets.PYPI_API_TOKEN }}\n"
        "      - run: echo //registry.npmjs.org/:_authToken=${{ secrets.NPM_TOKEN }}\n"
    )
    assert _rules(check_public_registry.scan_workflow(WF, text)) == [
        "npmjs-registry",
        "pypi-publish-action",
        "pypi-upload",
        "registry-token",
        "registry-token",
    ]


def test_comment_lines_ignored(check_public_registry):
    text = "# never run npm publish or uv publish here\n"
    assert check_public_registry.scan_workflow(WF, text) == []


def test_package_json_publish_config(check_public_registry):
    bad = '{"publishConfig": {"registry": "https://registry.npmjs.org/"}}'
    good = '{"publishConfig": {"registry": "https://npm.pkg.github.com"}}'
    assert _rules(check_public_registry.scan_package_json("package.json", bad)) == [
        "npmjs-registry"
    ]
    assert check_public_registry.scan_package_json("package.json", good) == []


def test_npmrc(check_public_registry):
    text = "registry=https://registry.npmjs.org/\n"
    assert _rules(check_public_registry.scan_npmrc(".npmrc", text)) == [
        "npmjs-registry"
    ]


def test_pyproject_publish_url(check_public_registry):
    text = (
        "[[tool.uv.index]]\n"
        'name = "pypi"\n'
        'url = "https://pypi.org/simple"\n'
        'publish-url = "https://upload.pypi.org/legacy/"\n'
    )
    findings = check_public_registry.scan_pyproject("pyproject.toml", text)
    assert _rules(findings) == ["pypi-upload"]
    assert findings[0].line == 4


def test_scope_and_allowlist(check_public_registry, tmp_path: Path):
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "release.yml").write_text("      - run: npm publish\n")
    (tmp_path / "README.md").write_text("npm publish\n")
    assert _rules(check_public_registry.scan(tmp_path)) == ["npm-publish"]

    # An entry with no approval reference is not honored.
    (tmp_path / ".public-registry-allowlist").write_text(f"{WF} npm-publish\n")
    assert _rules(check_public_registry.scan(tmp_path)) == ["npm-publish"]

    (tmp_path / ".public-registry-allowlist").write_text(
        f"{WF} npm-publish Platform Owner approval #123\n"
    )
    assert check_public_registry.scan(tmp_path) == []


def test_warning_first_then_blocking(check_public_registry, tmp_path, monkeypatch, capsys):
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "release.yml").write_text("      - run: uv publish\n")
    monkeypatch.setattr(check_public_registry, "REPO_ROOT", tmp_path)

    assert check_public_registry.main([], today=dt.date(2027, 1, 30)) == 0
    assert "::warning file=.github/workflows/release.yml,line=1::" in capsys.readouterr().out

    assert check_public_registry.main([], today=dt.date(2027, 1, 31)) == 1
    assert "::error file=" in capsys.readouterr().out


def test_this_repo_is_clean(check_public_registry):
    assert check_public_registry.main([], today=dt.date(2030, 1, 1)) == 0
