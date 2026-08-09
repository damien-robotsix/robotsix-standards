# Python CI workflow

> **Scope: every Python repository.** Every Python repo must ship a
> `.github/workflows/ci.yml` that runs lint, type-check, and test gates on
> every push to `main` and every pull request. The quality gates declared in
> `pyproject.toml` and `.pre-commit-config.yaml` are documentation;
> `ci.yml` is the enforcement mechanism.

## The rule

**Every Python repository must have a `ci.yml` workflow that runs, in order:
lint → type-check → test+coverage.** The workflow must trigger on `push` to
`main` and on `pull_request`. The three gates must run in sequence — a merge
PR must pass lint and type-check before the test suite runs — because running
tests when the code is already known to fail lint or type-check wastes CI
minutes and delays the developer's fix loop.

The required gates and their minimal invocations:

| Gate | Command | Notes |
|---|---|---|
| Lint | `uv run ruff check src/ --output-format=github` | `--output-format=github` surfaces annotations in the PR diff. |
| Format | `uv run ruff format --check src/` | Fails if any file needs formatting; separate from lint so the developer sees check vs. format failures distinctly. |
| Type-check | `uv run mypy` | Uses per-repo `pyproject.toml` mypy config (see [mypy strictness](mypy.md)). Must run on both `src/` and `tests/`. |
| Test | `uv run pytest tests/ --cov=<pkg> --cov-report=xml --cov-report=term-missing` | Coverage floor enforced fleet-wide; `coverage.xml` uploaded as a workflow artifact. |

The workflow must use `uv` for all Python tool invocations — no bare `pip
install`, no `python -m`, no tool installed outside the project's locked
environment.  `astral-sh/setup-uv` with `enable-cache: true` and a tight
`cache-dependency-glob` covering `pyproject.toml` and `uv.lock` is required
(see [Python practices: CI uv setup caching](python.md#ci-uv-setup-caching)).

The `UV_MALWARE_CHECK` environment variable must be set to `"1"` in every
Python CI job that runs `uv sync`.

## Why

The quality gates declared in `pyproject.toml` and
`.pre-commit-config.yaml` describe what *should* happen when a developer types
`uv run ruff check` or `uv run mypy`.  Without a `ci.yml` that runs those same
commands, the gates are documentation — a wish, not a fact.  A repo that
declares `my_strict = true` but has no CI workflow running mypy ships code
whose type-safety is unknown.

Several fleet repos (hexarchy and others identified in the 2026-07 survey)
declare `fail_under = 70` in their coverage config and `[tool.mypy]` strict
blocks in `pyproject.toml`, but their `.github/workflows/` directory contains
only a Docker publish workflow — lint, type-check, and test never execute in
CI.  The `README.md` claims "CI runs pytest plus pre-commit hooks (ruff, mypy)
on every push," but the claim is false because no workflow exists to back it.

A single canonical `ci.yml` shape — consumed either as a shared reusable
workflow or as a per-repo copy — closes this gap.  Every Python repo gets the
same gates, run the same way, with the same failure signals.  A developer
moving between repos sees the same CI shape and the same annotations in the PR
diff.

## How to comply

### Preferred: use the shared reusable workflow

The fleet maintains a shared `python-ci.yml` reusable workflow in
[robotsix-github-workflows](https://github.com/damien-robotsix/robotsix-github-workflows).
Every Python repo should call it from its `.github/workflows/ci.yml`:

- **Do not inline the workflow YAML into this page.** The caller template
  lives in the robotsix-github-workflows README, alongside the workflow it
  calls — that is the single source of truth.  This page states the rule;
  the workflow repo owns the template.
- **Pin the reusable workflow to a full commit SHA** (not a branch or tag
  ref).  The commit SHA in the caller's `uses:` line ties the repo to a
  specific, auditable revision of the shared workflow.
- **The shared workflow already includes** ruff check + format, mypy (with
  the `tests.*` override), pytest with coverage, and `coverage.xml` upload.
  A repo calling it gets all required gates automatically.

### Fallback: standalone `ci.yml`

When a repo cannot use the shared workflow (e.g. it has an unusual package
layout that the shared workflow doesn't support), it must ship a standalone
`ci.yml` that runs the same four gates in the same order, using the same `uv
run` invocations.  The standalone workflow must still follow the
[CI lint tool pinning](ci-lint-pinning.md) rule — every lint tool version
must match `.pre-commit-config.yaml`.

A repo that ships a standalone `ci.yml` must carry a comment at the top of the
file explaining why it cannot use the shared workflow, so a future reviewer
knows the deviation is deliberate.

## Jobs and ordering

The workflow must run the gates in order — lint (ruff check + format) before
type-check, type-check before test — for two reasons:

1. **Fast-fail.**  If ruff finds a syntax-level problem, there is no point
   spending CI minutes on type-checking or running tests.  The developer needs
   the lint failure first, not a test failure three minutes later.
2. **Signal isolation.**  When lint, type-check, and test run in parallel and
   all three fail, the developer sees a wall of red and has to disentangle
   which failure is causal.  Sequential gates surface the root-cause failure
   first.

The jobs may run as separate GitHub Actions jobs with `needs:` dependencies,
or as sequential steps within a single job.  Either shape is acceptable as
long as the ordering is enforced.

### Parallel auxiliary gates

These gates may run in parallel with the main sequence, as separate jobs (or
steps) that do not block the main gate chain:

- **Security SAST** (Semgrep, bandit) — runs in the shared
  `python-security.yml` workflow, not in `ci.yml`.
- **Dependency hygiene** (deptry).
- **Dependency audit** (`uv audit`).
- **Pre-commit hooks** (via `tox-dev/action-pre-commit-uv`) — these run
  the same hooks as local development, providing a second pass at file-level
  hygiene beyond ruff.

## What `ci.yml` does not cover

The `ci.yml` workflow is the *quality gate* — it verifies that the code as
written is lint-clean, type-safe, and passes its tests.  It does not:

- **Build or publish container images.**  That is the Docker publish workflow
  ([docker build & release](docker-standard.md)).
- **Run security scans (Semgrep, SBOM, secret scanning).**  Those run in the
  shared `python-security.yml` workflow.
- **Run integration tests against a live deployment.**  `ci.yml` runs the
  unit/functional test suite; integration tests that require a running service
  belong in a separate workflow triggered on deployment events.
- **Auto-release or changelog compilation.**  That is the changelog-driven
  release workflow ([changelog & releases](changelog-driven-releases.md)).

## Failure modes prevented

- **Silent gate drift.**  The `pyproject.toml` declares `strict = true` but
  no workflow runs mypy — the type-safety of the codebase is unknown and
  degrades silently with every commit.
- **Test rot.**  The test suite exists (`tests/` with `pytest`) but the
  coverage report is never generated in CI — `fail_under = 80` is a dead
  letter, and coverage can drop below the floor with no signal.
- **False README claims.**  A repo's README asserts that CI runs lint, type,
  and test gates, but the workflow directory contains only a Docker publish
  job.  The README becomes a lie the moment the workflow is missing, and no
  automated check catches the discrepancy.
- **Per-repo CI reinvention.**  Without a standard shape, each repo invents
  its own CI invocation — different tool versions, different ordering,
  different failure handling.  A developer moving between repos must relearn
  the CI shape each time, and a shared fix (e.g. a new ruff rule) must be
  applied to N different workflow files instead of one.
- **Cache waste.**  A repo that invokes lint and test through separate,
  uncached `uv sync` calls in different workflows pays the full dependency
  install cost multiple times per push.  The standard `ci.yml` shape with
  `enable-cache: true` amortizes the cost across every CI run.

## Relationship to other standards

- **[Python practices](python.md#ci-uv-setup-caching)** — `setup-uv` caching
  requirement, pre-commit CI integration, and the
  [optional-dependency import guard rule](python.md) (deptry enforcement).
- **[CI lint tool pinning](ci-lint-pinning.md)** — CI lint tools must match
  `.pre-commit-config.yaml` versions; applies to both the shared and
  standalone `ci.yml` paths.
- **[Mypy strictness](mypy.md)** — mypy as a hard CI gate, the `tests.*`
  override, and baseline-driven migration.
- **[Pytest practices](pytest.md)** — `fail_under`, coverage configuration,
  and strict-mode pytest flags.
- **[Ruff lint rules](ruff-lint-rules.md)** — the standard ruff rule families.
- **[Pre-commit baseline](pre-commit-baseline.md)** — the pre-commit hooks
  that `ci.yml`'s pre-commit job verifies.
- **[Repo baseline](repo-baseline.md)** — CI and security gates are a
  language-agnostic requirement; this page defines the Python-specific shape.
