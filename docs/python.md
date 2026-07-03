# Python practices

> **Scope: every Python repository.** These are the language-specific
> practices; the language-agnostic rules (tiers, hygiene, CI philosophy) live
> in the [repo baseline](repo-baseline.md).

## Tooling: uv

**uv is the standard tool** for installing, running, and building robotsix
packages — `uv sync`, `uv add`, `uv run`, `uvx`, `uv build`. pip is not a
supported install path (it ignores `[tool.uv.sources]`, so first-party git
dependencies won't resolve). **Do not advertise a `pip install` path.**

## Packaging

- **Build backend: `hatchling`.** `[tool.hatch.metadata]
  allow-direct-references = true` is only needed when `[project.dependencies]`
  itself contains direct URL references (`pkg @ git+https://…`). The standard
  pattern — plain dependency names resolved through `[tool.uv.sources]` — does
  not need it, because the git pin lives in uv's config, not in the project
  metadata hatchling validates.
- **No PyPI.** Nothing is published to a package index (see the
  [repo baseline](repo-baseline.md#no-package-index-consume-libraries-from-git)).
  Repos carry **no index-publish workflow** — no `pypi-publish`, no
  release-please, no PyPI token. (The shared auto-release workflow tags
  versions and compiles the changelog — see
  [changelog & releases](repo-baseline.md#changelog-releases) — but publishes
  nothing to any index.)
- **Libraries** are consumed straight from git via uv `[tool.uv.sources]`
  (`{ git = "…", rev = "…" }`), pinned by revision. They still ship `py.typed`
  for downstream type-checking.
- **Deployable components** ship a container image; the from-checkout path is
  `uv sync` (uv honours `[tool.uv.sources]`).
- Dev tooling goes in a PEP 735 `[dependency-groups] dev` group, pulled in by
  default via `[tool.uv] default-groups`.

## `requires-python`

- **Every repo — libraries and deployable components alike — targets the
  stack runtime baseline: `requires-python = ">=3.14"`.** The stack has no
  external consumers (no package index; first-party deps come from git), so a
  lower library floor buys nothing and costs real things: three years of
  language features forgone, and either a CI matrix for versions nothing
  runs, or a support claim CI never tests.
- **Lowering the floor is the exception, made deliberately** — when a library
  gains a genuine consumer on an older runtime. Like PyPI publishing: added
  back on purpose, never the default.
- **Metadata is authoritative — keep prose in sync.** A README claiming a
  Python floor different from `pyproject.toml` hard-blocks users the docs
  invite. Fix the prose, not the metadata.

## Console scripts

- One primary entry point per package: `robotsix-<name>`.
- **Host-side ops tooling does not belong in `[project.scripts]`.** Update/deploy
  helpers (git-pull + `docker compose up`, etc.) aren't part of the shipped
  package and aren't copied into a runtime image — keep them in `scripts/`.

## Lint, types, and security lint

Run via the shared `python-ci.yml` reusable workflow:

- `ruff check` + `ruff format --check`
- `mypy --strict`
- `deptry` (dependency hygiene)
- `bandit` (security SAST) and a dependency CVE audit (`uv audit`)

**Security lint convention:** enable ruff's bandit rules in `pyproject.toml`
(`[tool.ruff.lint] extend-select = ["S"]`). Suppressions are per-file ignores,
and **every ignore carries a comment justifying it** — a reviewer should never
have to guess why `S105` is off for a file:

```toml
[tool.ruff.lint]
extend-select = ["S"]

[tool.ruff.lint.per-file-ignores]
# S105: "secrets.key" is a filename, not a hardcoded credential.
"src/<pkg>/config.py" = ["S105"]
# Test files routinely use hard-coded sentinel strings and asserts.
"tests/**/*.py" = ["S101", "S105", "S106"]
```

## Tests

- `pytest`, with coverage enforced in CI via the shared workflow's
  `coverage-threshold` (`--cov-fail-under`). The fleet floor is **80%**; the
  gate **ratchets** — pin it at (or just below) current measured coverage,
  raise it as coverage grows, never lower it. Set
  `[tool.coverage.report] fail_under` to the same value: the CLI flag
  overrides it, so a lower `coverage-threshold` silently weakens the gate.
- **Test layout mirrors the package:** tests for module X live under
  `tests/X/`, never at the `tests/` root. New modules get a matching test
  directory.

## Pre-commit hooks

Every repo ships `.pre-commit-config.yaml` with at least: `ruff` (lint),
`ruff-format`, `mypy`, and the standard file checks (end-of-file,
trailing-whitespace, merge-conflict markers, large files). Dev setup is:

```sh
uv sync
pre-commit install
```

CI runs `pre-commit run --all-files` so the hooks and the gates can't drift.

## Docs

Repos that publish a docs site build with `mkdocs` (material theme) and gate
CI on `mkdocs build --strict`.
