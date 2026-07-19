# Python practices

> **Scope: every Python repository.** These are the language-specific
> practices; the language-agnostic rules (tiers, hygiene, CI philosophy) live
> in the [repo baseline](repo-baseline.md).

## Project layout

- **src layout, one primary package:** code lives in `src/robotsix_<name>/`,
  the snake_case of the repo name. Every package ships **`py.typed`** — any
  package may be imported by tests or tooling, and downstream type-checking
  must see the annotations.
- **Modules are subdirectories** of the package, mirrored by
  `tests/<module>/` and `docs/<module>/` — the same convention
  `docs/modules.yaml`'s default globs assume (see the
  [repo baseline](repo-baseline.md#repo-hygiene)).
- **Secondary packages are deliberate**, for one named reason: a client
  library siblings can import without pulling the service's dependencies
  (`robotsix_board_client` next to `robotsix_board_agent` is the exemplar).
  Each extra package registers in `modules.yaml` like anything else.

## Tooling: uv

**uv is the standard tool** for installing, running, and building robotsix
packages — `uv sync`, `uv add`, `uv run`, `uvx`, `uv build`. pip is not a
supported install path (it ignores `[tool.uv.sources]`, so first-party git
dependencies won't resolve). **Do not advertise a `pip install` path.**

**First-party dependencies are pinned to commit SHAs** in `[tool.uv.sources]`, never
branch refs — a branch ref drifts silently when `uv lock` re-resolves.
See the [repo baseline](repo-baseline.md#pin-to-a-commit-sha-not-a-branch)
for the pin rule and the auto-bump workflow. **Third-party dependencies**
go through Dependabot's `uv` ecosystem; `.github/dependabot.yml` must
declare it in every Python repo (the baseline-check gate verifies this).

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
- **No upper bound.** `>=3.14`, never `>=3.14,<3.15`: a cap poisons
  resolution for every dependent (uv must satisfy the intersection of all
  bounds, so one capped package caps the whole tree) and encodes a breakage
  that hasn't happened. Cap only for a known, linked incompatibility, and
  remove the cap when it's fixed.
- **Metadata is authoritative — keep prose in sync.** A README claiming a
  Python floor different from `pyproject.toml` hard-blocks users the docs
  invite. Fix the prose, not the metadata.

### 3.14 syntax notes

- **PEP 758: parentheses around multiple exception types are optional.**
  `except ValueError, KeyError:` is valid 3.14 syntax, exactly equivalent to
  `except (ValueError, KeyError):` — and `ruff format` on a `>=3.14` target
  normalises to the parens-free form, making it the tool-enforced style.
  Don't misread it as the legacy Python-2 `except E, var:` bind-as form, and
  don't "fix" it back to parentheses.

## Datetimes

**UTC everywhere; naive datetimes are forbidden in stored or emitted data.**
`datetime.now(tz=UTC)`, never bare `now()`/`utcnow()` — a naive datetime
means "whatever timezone the host happens to run" (the deploy host runs
CEST). Serialize ISO-8601 with explicit offset. Rendering local time is a UI
concern (see the [component standard](component-standard.md#logging)).

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

Ruff's pydocstyle rules (`D`) enforce the fleet [docstring convention](docstrings.md)
at lint time — every repo enables the standard rule set so that API docs
built by mkdocstrings don't silently drop parameter descriptions.

The shared `python-security.yml` workflow is a separate gate that additionally
runs `pip-audit` (a second CVE audit pass), TruffleHog for secret scanning
(PR-diff and full-repo), and generates a CycloneDX SBOM uploaded as a workflow
artifact.

**CodeQL** runs as a separate SAST gate via the shared security workflow —
see the [security posture](security-posture.md#1-sast-codeql) for details.

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

**deptry and CLI-tool dependencies:** a package installed as a *tool* but
never imported (a linter or formatter in an optional group) gets flagged as
unused by deptry and fails CI. Register it under `DEP002` in
`[tool.deptry.per_rule_ignores]`, with a comment — same convention as the
ruff suppressions above.

## CI: uv setup caching

**Every CI job that calls `astral-sh/setup-uv` MUST enable caching.**
Set `enable-cache: true` with a `cache-dependency-glob` that covers
`pyproject.toml` and `uv.lock` (the minimalset — no broader globs that
would invalidate the cache on unrelated changes). The action version must
be **v6 or later** (v5 and earlier do not support `enable-cache`).

**Rationale:** without caching, every CI run re-downloads the full
dependency set from PyPI — `uv sync --frozen` cold is ~30–60 s; from a
hot cache it is ~2–5 s.  That saving multiplies across every Python-repo
CI run in the fleet.  The tight `cache-dependency-glob` ensures the cache
is invalidated only when dependencies actually change, not on every
source-file edit.  This is the industry-standard pattern (used by
FastAPI, pydantic, pandas).

**Release/deploy workflows MAY disable caching** (`enable-cache: false`)
as a security hardening measure — avoiding potential cache-poisoning risk
on sensitive publish steps.

### Pre-commit jobs

**CI jobs that run pre-commit via `tox-dev/action-pre-commit-uv` add an
explicit `astral-sh/setup-uv` step before the pre-commit action** to
control cache settings (the action's internal setup-uv call does not
expose cache configuration).  Cache `~/.cache/pre-commit` separately via
`actions/cache@v4`, keyed on the hash of `.pre-commit-config.yaml`.

**Rationale:** rebuilding pre-commit environments from scratch takes
20–40 s per run; caching them cuts that to near-zero on cache hits.  The
explicit setup-uv step ensures the uv package cache is also warm when
pre-commit hooks install Python tools.

## Tests

- `pytest`, with coverage gated at **one fleet-wide floor: 80%**, the same in
  every repo. The floor is enforced by the shared `python-ci.yml` workflow —
  it lives in one place, so no repo can slide under it — and
  `[tool.coverage.report] fail_under = 80` in each repo keeps local runs
  honest. No per-repo thresholds, no ratchet to maintain: coverage above the
  floor is welcome, but the gate stops caring beyond 80.
- **The floor moves only fleet-wide.** When every repo measures above a
  higher value, the floor in the shared workflow is raised for everyone at
  once — one PR in robotsix-github-workflows, a deliberate decision. It never
  rises above what the weakest repo clears, and it never moves per-repo.
- **Test layout mirrors the package:** tests for module X live under
  `tests/X/`, never at the `tests/` root. New modules get a matching test
  directory.
- **The default test run is offline and credential-free**: declare
  `addopts = ["-m", "not live", "--strict-markers", "--strict-config"]`.
  Tests that genuinely need the network or real credentials carry the
  **`live` marker** and run only by explicit opt-in (`pytest -m live`),
  never in the standard CI gate — in mill sandboxes (egress-proxied) and CI,
  an accidental network call is a hang or a paid flake. `--strict-markers`
  makes a misspelled marker an error instead of an always-running test.
  `tests/.env.example` lists exactly the live-suite credentials — nothing
  else.
- **Shared fixtures live in `conftest.py`:** when two test files under the
  same `tests/<module>/` define the same fixture, extract it to
  `tests/<module>/conftest.py` — pytest discovers it for all sibling tests.
  Duplicated fixtures drift apart; this recurs especially in agent-written
  PRs.

## Pre-commit hooks

Every repo ships `.pre-commit-config.yaml` with the standard set (this is the
fleet's converged practice, not a minimum to improvise beyond).
**Content-only repos** (as defined in the [security posture](security-posture.md))
— repos with no `src/` directory and no container image — may omit `ruff`,
`ruff-format`, `mypy`, `vulture`, and `hadolint`. The "standard set" is the
full set for repos that ship Python packages; content-only repos use the subset
documented in the template's `.pre-commit-config.yaml`.

- **File checks:** `end-of-file-fixer`, `trailing-whitespace`,
  `check-merge-conflict`, `check-added-large-files`, `check-yaml`,
  `check-toml`, `check-json`, `detect-private-key`.
- **Code:** `ruff` (with `--fix`), `ruff-format`, `mypy`.
- **Secrets:** `detect-secrets` (with a committed `.secrets.baseline`) —
  catches credentials *before* the commit exists, complementing CI's push
  protection; this matters more when agents author most commits.
- **Workflows:** `actionlint` — catches broken workflow/caller YAML at commit
  time.
- **Dead code:** `vulture` — agent-written changes are prone to orphaned
  helpers.
- **Image-shipping repos additionally:** `hadolint` — the
  [Dockerfile pattern](docker-standard.md) is a standard; hadolint keeps it
  one.

Deliberately not in the set: `bandit` as a hook (it already gates in CI via
the shared workflow, and ruff's `S` rules cover the commit-time subset — a
slow duplicate hook buys little). Dev setup is:

```sh
uv sync
pre-commit install
```

CI runs `pre-commit run --all-files` so the hooks and the gates can't drift.

## Docs

**Every repo publishes its docs site**: `mkdocs` (material theme), built and
deployed to GitHub Pages by the shared `python-docs.yml` reusable workflow,
gated in CI by `mkdocs build --strict`. The fleet's sites are indexed on the
standards' [fleet page](fleet.md).
