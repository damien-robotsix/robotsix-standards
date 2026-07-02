# Repo baseline

> **Scope: every robotsix repository** — libraries and deployable components
> alike. Deployable components follow these conventions *and* the
> [component standard](component-standard.md).

Conventions every repository shares, so tooling, CI, and contributor workflow
are the same everywhere.

## Tooling: uv

**uv is the standard tool** for installing, running, and building robotsix
packages — `uv sync`, `uv add`, `uv run`, `uvx`, `uv build`. pip is not a
supported install path (it ignores `[tool.uv.sources]`, so first-party git
dependencies won't resolve). Build backend is `hatchling`.

## Distribution tier is explicit

A repo is **either** a library **or** a deployable component — decide and be
consistent. The tier determines which standards apply and how the package is
distributed.

| Tier | What it is | Ships as | How consumers/operators get it |
|---|---|---|---|
| **Library** | Imported by other packages; no runnable service | PyPI wheel + `py.typed` | `uv add <lib>` |
| **Deployable component** | Ships a runnable service | Container image | Run the container, or `uv sync` from a checkout |

A component's first-party git dependencies resolve under `uv sync` (uv honours
`[tool.uv.sources]`), so the from-checkout install works even when the package
is not published to PyPI. **Do not advertise a `pip install <component>` path.**

Deployable components additionally follow the [component standard](component-standard.md).

## `requires-python`

- **Libraries** target `>=3.11` so the widest set of consumers can depend on
  them.
- **Deployable components** target the stack runtime baseline (`>=3.14`).
- **Metadata is authoritative — keep prose in sync.** A README claiming a
  Python floor different from `pyproject.toml` hard-blocks users the docs
  invite. Fix the prose, not the metadata.

## Console scripts

- One primary entry point per package: `robotsix-<name>`.
- **Host-side ops tooling does not belong in `[project.scripts]`.** Update/deploy
  helpers (git-pull + `docker compose up`, etc.) aren't part of the shipped
  package and aren't copied into a runtime image — keep them in `scripts/`.

## Repo hygiene

- **Changelog.** Maintain `CHANGELOG.md` in [Keep a Changelog](https://keepachangelog.com)
  form under an `## 0.0.0 (unreleased)` heading; every PR adds an entry (CI
  enforces it).
- **Module registration.** Every file is registered in `docs/modules.yaml`
  under exactly one module; a drift check fails CI on unregistered or stale
  paths. New modules start by adding an entry there.
- **Truthful docs.** README / AGENT.md describe what the code actually does;
  don't let removed commands, renamed paths, or old version claims linger.
- **License.** MIT.

## CI and security gates

Prefer the fleet's shared reusable workflows; pin every third-party action to a
commit SHA (with a `# vX.Y.Z` comment). The standard gate set:

- **Lint & types:** `ruff check` + `ruff format --check`, `mypy` (strict),
  `vulture` (dead-code, with a whitelist), `deptry` (dependency hygiene).
- **Tests & coverage:** `pytest` with a coverage floor enforced in CI.
- **Docs:** `mkdocs build --strict` when the repo publishes a docs site.
- **Security:** CodeQL (SAST), secret scanning + push protection, and
  `dependency-review` on PRs (`fail-on-severity: high`).

> **Dependency-review needs the Dependency graph enabled.** The
> `dependency-review` action errors with *"Dependency review is not supported on
> this repository"* until the repo's **Dependency graph** is turned on (enable
> Dependabot alerts / automated security fixes, which turn it on). Enable it once
> per repo, or the gate can never go green.
