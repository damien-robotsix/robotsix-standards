"""Unit tests for the bidirectional TOC-sync gate (scripts/check-toc-sync.py).

Covers the happy path (a fully synchronized mini docs repo) and the failure
edges the gate exists to catch: a nav entry missing from README.md or
docs/index.md, and a page linked from README.md / docs/index.md that is
orphaned (not in the mkdocs.yml nav).
"""

from __future__ import annotations

from pathlib import Path

import yaml

NAV_YAML = """\
nav:
  - Home: index.md
  - Every repo:
      - Repo baseline: repo-baseline.md
      - Pytest practices: pytest.md
  - Deployable components:
      - Component standard: component-standard.md
  - Deployment system:
      - The deployment system: deployment-system.md
  - Meta:
      - Changelog & releases: changelog-driven-releases.md
"""

README_MD = """\
# Robotsix Standards

**Every repository**

| Title | Link | Description |
| --- | --- | --- |
| Repo baseline | [repo-baseline.md](docs/repo-baseline.md) | baseline |
| Pytest practices | [pytest.md](docs/pytest.md) | pytest |

**Deployable components**

| Title | Link | Description |
| --- | --- | --- |
| Component standard | [component-standard.md](docs/component-standard.md) | cmp |

**The deployment system**

| Title | Link | Description |
| --- | --- | --- |
| The deployment system | [deployment-system.md](docs/deployment-system.md) | dep |

**Meta**

| Title | Link | Description |
| --- | --- | --- |
| Changelog & releases | [changelog-driven-releases.md](docs/changelog-driven-releases.md) | chg |
"""

INDEX_MD = """\
# Index

### Every repository

- [Repo baseline](repo-baseline.md)
- [Pytest practices](pytest.md)

### Deployable components

- [Component standard](component-standard.md)

### The deployment system

- [The deployment system](deployment-system.md)

### Meta

- [Changelog & releases](changelog-driven-releases.md)
"""


def _write_docs(
    tmp_path: Path, *, readme: str = README_MD, index: str = INDEX_MD
) -> tuple[Path, Path, Path]:
    """Write mkdocs.yml + README.md + docs/index.md and return their paths."""
    (tmp_path / "docs").mkdir()
    mkdocs = tmp_path / "mkdocs.yml"
    mkdocs.write_text(NAV_YAML)
    readme_path = tmp_path / "README.md"
    readme_path.write_text(readme)
    index_path = tmp_path / "docs" / "index.md"
    index_path.write_text(index)
    return mkdocs, readme_path, index_path


def _point_at(tmp_path, check_toc_sync, monkeypatch, *, readme=README_MD, index=INDEX_MD):
    mkdocs, readme_path, index_path = _write_docs(tmp_path, readme=readme, index=index)
    monkeypatch.setattr(check_toc_sync, "MKDOCS_YML", mkdocs)
    monkeypatch.setattr(check_toc_sync, "README_MD", readme_path)
    monkeypatch.setattr(check_toc_sync, "INDEX_MD", index_path)


# ---------------------------------------------------------------------------
# extract_pages / missing_pages / _all_nav_pages
# ---------------------------------------------------------------------------


def test_extract_pages_list_section(check_toc_sync):
    nav = yaml.safe_load(NAV_YAML)["nav"]
    assert check_toc_sync.extract_pages(nav, "Every repo") == [
        "repo-baseline.md",
        "pytest.md",
    ]


def test_extract_pages_string_section(check_toc_sync):
    assert check_toc_sync.extract_pages([{"Meta": "meta.md"}], "Meta") == ["meta.md"]


def test_extract_pages_absent_section(check_toc_sync):
    nav = yaml.safe_load(NAV_YAML)["nav"]
    assert check_toc_sync.extract_pages(nav, "Does not exist") == []


def test_missing_pages_finds_absent(tmp_path, check_toc_sync):
    f = tmp_path / "README.md"
    f.write_text("contains repo-baseline.md only")
    assert check_toc_sync.missing_pages(["repo-baseline.md", "pytest.md"], f) == [
        "pytest.md"
    ]


def test_missing_pages_none_missing(tmp_path, check_toc_sync):
    f = tmp_path / "README.md"
    f.write_text("repo-baseline.md and pytest.md are both present here")
    assert check_toc_sync.missing_pages(["repo-baseline.md", "pytest.md"], f) == []


def test_all_nav_pages_gathers_every_section(check_toc_sync):
    nav = yaml.safe_load(NAV_YAML)["nav"]
    pages = check_toc_sync._all_nav_pages(nav)
    assert {
        "index.md",
        "repo-baseline.md",
        "pytest.md",
        "component-standard.md",
        "deployment-system.md",
        "changelog-driven-releases.md",
    } <= pages


# ---------------------------------------------------------------------------
# main(): happy path and failure edges
# ---------------------------------------------------------------------------


def test_main_happy_path(tmp_path, check_toc_sync, monkeypatch):
    _point_at(tmp_path, check_toc_sync, monkeypatch)
    assert check_toc_sync.main() == 0


def test_main_missing_nav_entry_in_readme(tmp_path, check_toc_sync, monkeypatch, capsys):
    readme = README_MD.replace(
        "| Repo baseline | [repo-baseline.md](docs/repo-baseline.md) | baseline |\n",
        "",
    )
    _point_at(tmp_path, check_toc_sync, monkeypatch, readme=readme)
    assert check_toc_sync.main() == 1
    assert "MISSING from README.md: repo-baseline.md" in capsys.readouterr().out


def test_main_missing_nav_entry_in_index(tmp_path, check_toc_sync, monkeypatch, capsys):
    index = INDEX_MD.replace("- [Repo baseline](repo-baseline.md)\n", "")
    _point_at(tmp_path, check_toc_sync, monkeypatch, index=index)
    assert check_toc_sync.main() == 1
    assert "MISSING from docs/index.md: repo-baseline.md" in capsys.readouterr().out


def test_main_orphaned_page_in_readme(tmp_path, check_toc_sync, monkeypatch, capsys):
    readme = README_MD.replace(
        "| Repo baseline | [repo-baseline.md](docs/repo-baseline.md) | baseline |\n",
        "| Repo baseline | [repo-baseline.md](docs/repo-baseline.md) | baseline |\n"
        "| Fleet overview | [fleet-overview.md](docs/fleet-overview.md) | new |\n",
    )
    _point_at(tmp_path, check_toc_sync, monkeypatch, readme=readme)
    assert check_toc_sync.main() == 1
    assert "ORPHANED in README.md" in capsys.readouterr().out


def test_main_orphaned_page_in_index(tmp_path, check_toc_sync, monkeypatch, capsys):
    index = INDEX_MD.replace(
        "- [Repo baseline](repo-baseline.md)\n",
        "- [Repo baseline](repo-baseline.md)\n- [Fleet overview](fleet-overview.md)\n",
    )
    _point_at(tmp_path, check_toc_sync, monkeypatch, index=index)
    assert check_toc_sync.main() == 1
    assert "ORPHANED in docs/index.md" in capsys.readouterr().out
