# CI dependency management

> **Scope: every Python repository using uv.** This standard defines the
> fleet's approach to automated dependency updates, lockfile integrity
> checks, and git-pinned dependency refresh for uv-based Python repos.
> Non-Python ecosystems (`github-actions`, `pre-commit`, `docker`, `npm`)
> continue to use Dependabot as described in the
> [repo baseline](repo-baseline.md#automated-dependency-updates).

## The rules

1. **Renovate over Dependabot for Python/uv lockfile updates.**
2. **Every Python repo's CI must include a `uv lock --check` gate.**
3. **Repos with git-pinned `[tool.uv.sources]` dependencies must have a
   scheduled refresh workflow.**
4. **A minimum-dependency CI leg must use `uv sync --resolution
   lowest-direct`, never `--resolution lowest`.**

---

## 1. Renovate for Python/uv

**Use Renovate (Mend) with the `uv` package manager for all Python repos
using uv.** Dependabot's `uv` ecosystem has unresolved lockfile update
bugs ([dependabot-core#13912](https://github.com/dependabot/dependabot-core/issues/13912),
still open as of mid-2026) — every Dependabot PR that touches a uv lockfile
risks a broken lockfile and a CI failure. Renovate's uv support (v38+) handles
lockfile updates correctly, and uv workspace/monorepo support landed in
v41.63.0.

### Configuration

Every Python repo must include a `renovate.json` at the repo root:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended"],
  "packageRules": [
    {
      "matchUpdateTypes": ["minor", "patch"],
      "groupName": "non-major dependencies",
      "automerge": true
    }
  ],
  "lockFileMaintenance": {
    "enabled": true,
    "schedule": ["before 5am on monday"]
  }
}
```

- `"extends": ["config:recommended"]` — Renovate's curated defaults (labels,
  onboarding PR, rate-limiting).
- The `packageRules` block groups minor and patch updates into a single PR
  and enables auto-merge (`"automerge": true`).  Major updates remain
  individual and require human review.
- `"lockFileMaintenance"` — weekly lockfile refresh (re-resolves transitive
  deps within `pyproject.toml` constraints and re-locks `uv.lock`).

Repos that already have a `renovate.json` (e.g. bundling Renovate for
non-Python ecosystems) must add the `uv` manager configuration to their
existing file rather than replacing it.

### Dependabot stays for non-Python ecosystems

Renovate replaces Dependabot **only for the `uv` ecosystem**.  Dependabot
remains the bumper for `github-actions`, `pre-commit`, `docker`, and `npm`
as declared in the [repo baseline](repo-baseline.md#automated-dependency-updates).
A repo using Renovate for `uv` must therefore carry both a `renovate.json`
and a `.github/dependabot.yml`.

### Why Renovate over Dependabot for uv

Dependabot's `uv` ecosystem produces broken lockfiles — the generated
`uv.lock` is not consistent with `pyproject.toml` constraints, causing
`uv sync --frozen` to fail on every Dependabot PR.  The Django project's
infrastructure team [explicitly switched from Dependabot to Renovate](https://github.com/django/django-docker-box/pull/219)
in 2025 citing stagnant development and unresolved uv issues.  The failure
mode is wasted human review time: every Dependabot PR arrives with a red CI,
requires a manual `uv lock` fix, and trains reviewers to ignore red CI on
dependency PRs — which is exactly the signal that should be actionable.

Renovate's uv support is actively maintained and handles lockfile updates
correctly.  The `lockFileMaintenance` schedule keeps the lockfile fresh
without noise.

---

## 2. `uv lock --check` CI gate

**Every Python repo's CI must include a `uv lock --check` step as the first
step in the dependency-validation job, before `uv sync --frozen`.**

```yaml
- name: Check lockfile consistency
  run: uv lock --check
```

`uv sync --frozen` validates that the lockfile is **internally consistent**
(all hashes match, no missing entries) but does **not** detect drift from
`pyproject.toml` — if a developer bumps a dependency version in
`pyproject.toml` without running `uv lock`, `uv sync --frozen` succeeds
using the stale lockfile.  `uv lock --check` is the only way to catch this:
it exits non-zero when `uv.lock` would change if re-resolved from the
current `pyproject.toml`.

**Placement:** before `uv sync --frozen`, in whichever job installs
dependencies.  In the standard
[Python CI workflow](python-ci-workflow.md), this is the first step after
the `setup-uv` action.

### Why uv lock --check

The failure mode is silent lockfile drift.  A developer bumps a lower-bound
in `pyproject.toml` (e.g. `httpx>=0.28` → `httpx>=0.29`), forgets to run
`uv lock`, and pushes.  CI runs `uv sync --frozen`, which reads the old
lockfile — all hashes are valid, no error.  The new lower-bound is
effectively not enforced in CI; a contributor or deployment can pick up the
old transitive version.  `uv lock --check` fails loudly on this condition
and forces the developer to run `uv lock` before the PR can merge.

---

## 3. Scheduled refresh for git-pinned dependencies

**Repos with `[tool.uv.sources]` git-pinned inter-project dependencies must
have a scheduled weekly workflow that runs `uv lock --upgrade-package <pkg>`
and creates a PR.**

Neither Dependabot nor Renovate can update git-pinned dependencies declared
in `[tool.uv.sources]` — those are first-party fleet libraries pinned to
commit SHAs (see the
[repo baseline: pin to a commit SHA](repo-baseline.md#pin-to-a-commit-sha-not-a-branch)).
They need a dedicated workflow.

### Workflow shape

```yaml
name: Refresh git-pinned dependencies
on:
  schedule:
    - cron: "0 6 * * 1"  # Monday 06:00 UTC
  workflow_dispatch:

jobs:
  refresh:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@<sha>  # v4.x
      - uses: astral-sh/setup-uv@<sha>  # v6.x
        with:
          enable-cache: true
          cache-dependency-glob: "pyproject.toml"
      - name: Upgrade git-pinned dependencies
        run: |
          uv lock --upgrade-package robotsix-config
          uv lock --upgrade-package robotsix-llmio
      - uses: peter-evans/create-pull-request@<sha>  # v7.x
        with:
          title: "chore: refresh git-pinned dependencies"
          branch: "chore/refresh-git-pins"
          commit-message: "chore: refresh git-pinned dependencies"
          body: |
            Weekly refresh of `[tool.uv.sources]` git-pinned dependencies.
            Updates each pinned commit SHA to the latest commit on its
            default branch.
          labels: "dependencies"
```

Each `--upgrade-package` line names one git-pinned dependency.  The list
must be repo-specific — a repo with two git-pinned deps runs two
`--upgrade-package` commands.  The schedule (Monday morning) runs before
any scheduled release workflow so refreshed pins land in a release PR if
one opens that week.

### Why scheduled refresh

Git-pinned dependencies are opaque to standard dependency bots — neither
Dependabot nor Renovate understands `[tool.uv.sources]` git references.
Without a dedicated workflow, first-party library pins silently rot: the
pinned commit drifts further from its upstream default branch with every
upstream change, and the consuming repo never picks up bug fixes or API
additions until a developer manually notices and runs `uv lock --upgrade-package`.

The failure mode is a stale pin that blocks an upgrade — a security fix
lands upstream in `robotsix-config`, but every consumer is pinned to a
commit from six weeks ago.  No automated PR opens, no human notices, and
the fix sits unused until someone stumbles on the drift.

---

## 4. Minimum-dependency testing uses `--resolution lowest-direct`

**Every Python library repo that runs a minimum-dependency CI leg must use
`uv sync --resolution lowest-direct`, never `--resolution lowest`.**

```yaml
- name: Install minimum dependencies
  run: uv sync --resolution lowest-direct --group dev --group test
```

`--resolution lowest` descends the **entire** transitive dependency tree and
pins every package — direct or transitive — to its floor version.  For a
library that is the wrong signal: an unrelated transitive package's lower
bound can conflict with another transitive package's floor, or predate the
library's `requires-python`, and the min-deps leg fails for a reason the
owning library does not control.  The failure is amplified when a library
targets a recent interpreter (`requires-python = ">=3.14"`) while dev/docs
transitive deps are unpinned — `lowest` floats them down and can resolve to
releases without Python 3.14 wheels.

`--resolution lowest-direct` (uv >= 0.4.1) honors lower bounds **only on
directly-declared dependencies** (e.g. `PyYAML>=6`, `jsonschema>=4`) while
floating transitive deps to their current versions.  That yields a stable
signal that the library truly supports the minimums it advertises, without
inheriting unrelated transitive-floor incompatibilities.

### The trade-off

`lowest-direct` is a **weaker** signal than `lowest`: it can mask a deep
transitive-floor interaction (one direct dependency's floor requiring a
newer transitive version than another direct dependency's floor).  The
stable, non-noisy result is the standard choice; `lowest` is reserved for
projects that deliberately pin their whole transitive floor via a
constraint file, where descending the full tree is meaningful.

### Why lowest-direct

The failure mode is false-failure noise.  `--resolution lowest` reports a
break in a transitive package the library does not control as if it were the
library's breakage; developers learn to ignore the min-deps leg, and the
signal that *should* catch a real lower-bound regression — the library
declares `PyYAML>=6` but the code uses an API introduced in 6.1 — gets
buried.  `lowest-direct` keeps the leg pointed at the library's own declared
lower bounds.

---

## Failure modes prevented

- **Broken Dependabot PRs.** Dependabot's `uv` ecosystem generates
  inconsistent lockfiles — every PR arrives with a red CI, trains reviewers
  to ignore red CI on dependency PRs, and wastes human time on manual
  `uv lock` fixes.
- **Silent lockfile drift.** `uv sync --frozen` does not detect when
  `uv.lock` is stale relative to `pyproject.toml`.  `uv lock --check` is
  the only gate that catches this.
- **Minimum-dependency false failures.** `--resolution lowest` pins
  transitive floors the library does not control, breaking CI on unrelated
  transitive incompatibilities and training developers to ignore the
  min-deps leg.  `--resolution lowest-direct` keeps the signal on the
  library's own declared lower bounds.
- **Stale git pins.** First-party fleet-library pins are invisible to
  dependency bots — without a scheduled refresh, they sit at an ever-staler
  commit and never pick up upstream bug fixes or API additions.

## Relationship to other standards

- **[Repo baseline](repo-baseline.md)** — the language-agnostic dependency
  update rules; this page defines the Python/uv-specific replacement for
  the Dependabot `uv` ecosystem.
- **[Python CI workflow](python-ci-workflow.md)** — the standard `ci.yml`
  shape that must include the `uv lock --check` gate.
- **[Python practices](python.md)** — uv as the standard tool, first-party
  git-pinning convention, and CI uv setup caching.
- **[Dependabot auto-merge](dependabot-auto-merge.md)** — the auto-merge
  gate for Dependabot PRs (which remain for non-Python ecosystems).
