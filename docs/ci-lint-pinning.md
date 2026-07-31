# CI lint tool pinning

> **Scope: every repository with a `.pre-commit-config.yaml`.** The
> pre-commit config is the single source of truth for lint-tool versions;
> every CI lint job that runs a tool already covered by a pre-commit hook
> must consume that same pinned version.

## The rule

**CI lint jobs must run the same version-pinned tools as
`.pre-commit-config.yaml`.** The pre-commit `rev:` field is the single
source of truth for every lint-tool version. A CI job that runs the same
tool from a different source — floating, latest, unpinned — is a
reproducibility bug: the gate validates against a **different tool version**
than the one local developers and pre-commit run.

This applies to every tool that appears in both places: yamllint,
shellcheck, hadolint, actionlint, codespell, markdownlint-cli, ruff,
mypy, and any future lint hook added to the standard pre-commit set.

## Why

When CI installs `yamllint` from `pip install yamllint` (latest) while
`.pre-commit-config.yaml` pins `rev: v1.35.1`, the two runs use different
versions. A check can pass in CI and fail locally — or vice versa — purely
because of version skew. The developer sees a red X on their PR, runs the
same tool locally, and gets a green pass, because their local version is
pinned and CI's isn't. The debugging loop is: update the tool, re-learn the
new rule set, and hope the versions converge. It never does for long.

Dependabot already bumps pre-commit `rev:` tags (the `pre-commit` ecosystem
block in `.github/dependabot.yml`). When CI consumes those same pins,
Dependabot keeps **both** paths in lockstep — one PR updates the pre-commit
config, and the next CI run automatically uses the new version.

## How

Two approaches are acceptable. Both satisfy the rule — choose the one
that fits the repo's CI workflow shape:

### Approach A: run the tool through pre-commit (preferred)

Run `pre-commit run <hook-id> --all-files` in CI. This is the simplest
path and the one the fleet's shared workflows use. The pre-commit runtime
installs exactly the `rev:`-pinned version into its own isolated
environment — CI and local dev are literally the same invocation.

```yaml
# In a CI job:
- uses: astral-sh/setup-uv@v6
  with:
    enable-cache: true
    cache-dependency-glob: "pyproject.toml"
- uses: tox-dev/action-pre-commit-uv@v1
  with:
    extra_args: --show-diff-on-failure --all-files
```

### Approach B: pin the CI install to the pre-commit `rev:` version

When a tool must run outside pre-commit (e.g. as a standalone CI step for
reporting reasons), pin its install command to the **exact same version**
declared in `.pre-commit-config.yaml`. Extract the version from the
pre-commit config — do not guess, do not round, do not default to latest:

```yaml
# Good — pinned to the pre-commit rev:
- run: pip install yamllint==1.35.1

# Good — action pinned to a release tag that matches the pre-commit rev:
- uses: hadolint/hadolint-action@v3.1.0
```

When the Dependabot PR bumps the pre-commit `rev:`, it must also bump
any standalone CI install lines that reference the same tool. A CI job
that references a version literal must carry a comment pointing back to
the pre-commit config so the reviewer of the Dependabot PR knows to update
both:

```yaml
# Keep in sync with .pre-commit-config.yaml → hadolint rev:
- uses: hadolint/hadolint-action@v3.1.0
```

## Anti-patterns: never install from floating/latest sources

Every one of these patterns is forbidden in CI lint jobs for tools that
also appear in `.pre-commit-config.yaml`:

| Forbidden | Why it drifts |
|---|---|
| `pip install <tool>` | Installs latest from PyPI — unrelated to the pre-commit `rev:`. |
| `npm install -g <tool>` | Installs latest from npm — same problem. |
| `apt-get install <tool>` | Installs whatever version the runner image ships — drifts across image updates. |
| `curl .../releases/latest/download/...` | Always fetches the latest release — the opposite of pinned. |
| `bash <(curl ...download-actionlint.bash)` | Unpinned download script — version is whatever the script resolves. |
| `docker run <image>:latest` | The `latest` tag moves — a moving target. |

## Exceptions

A CI job may deviate from the pre-commit pin when:

- **The tool runs exclusively in CI and has no pre-commit hook.** No
  conflict exists — there is no pre-commit version to stay in sync with.
  The tool must still be pinned (never `latest`), but the pin lives in the
  CI workflow itself rather than in `.pre-commit-config.yaml`.
- **The tool version is determined by an external constraint** (e.g. a
  language runtime version that the pre-commit hook doesn't cover). Document
  the constraint in a comment in the CI workflow.

Both exceptions are narrow and deliberate. The default is: if the tool has
a pre-commit hook, CI runs that same version.

## Failure modes prevented

- **Version-skew debugging loops.** Developer runs pre-commit locally
  (pinned), CI runs latest (different). The PR fails with a lint error the
  developer cannot reproduce — or passes a check that should have failed,
  because CI's newer version hasn't yet learned the rule that the pinned
  version enforces.
- **Dependabot drift.** Dependabot bumps the pre-commit `rev:` but the CI
  job still runs the old version. The local pre-commit hook enforces new
  rules that CI never checks — a false sense of gate coverage.
- **Runner-image drift.** `apt-get install shellcheck` on
  `ubuntu-24.04` installs a different version than `ubuntu-22.04`. A repo
  that upgrades its runner image gets a different lint tool — and
  potentially different results — with no code change.
- **Silent rule changes.** A tool's latest release adds a new check that
  fails on existing code. The pre-commit hook (pinned, unchanged) passes
  but CI (latest, freshly installed) fails — a broken build with no
  apparent cause.

## Relationship to other standards

- The pre-commit hook set is defined in [Python practices](python.md#pre-commit-hooks)
  and the [pre-commit baseline](pre-commit-baseline.md).
- The Dependabot `pre-commit` ecosystem block is referenced in
  [Python practices](python.md#tooling-uv) and the
  [security posture](security-posture.md).
- CI workflow standards (shared workflows, caching) live in
  [Python practices](python.md#ci-uv-setup-caching).
