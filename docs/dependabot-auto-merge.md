# Dependabot auto-merge

> **Scope: every repository that enables Dependabot auto-merge.** The
> auto-merge gate must be CI-status-driven — it must wait for required
> status checks to pass before merging — not purely actor-driven.  Actor-gated
> auto-merge (`if: github.actor == 'dependabot[bot]'`) that does not wait on
> CI status is the anti-pattern this standard forbids.

## The rule

**Dependabot auto-merge MUST be gated on required CI passing.** The
merged-in PR must not land before its required status checks complete. The
canonical safe mechanism is to poll the PR's `mergeable_state` (via the
GitHub API) and only call the merge endpoint once it reports `"clean"`.
Purely actor-gated auto-merge — a workflow that merges a Dependabot PR
solely because the actor is `dependabot[bot]`, without waiting for CI —
MUST NOT be used.

Additionally:

- **Restrict auto-merge to low-risk, non-breaking updates.** The trigger
  must constrain the target to `minor` and/or `patch` dependency updates
  so a major version bump to a build or test tool never lands without a
  human review.
- **Exclude Docker image and pre-commit ecosystem bumps from auto-merge.**
  These ecosystems rewrite build environments (`/.devcontainer/Dockerfile`,
  image digests) or pin/refactor hook versions (rewrites code or images) and
  warrant human review. Every repo's `.github/dependabot.yml` must exclude
  the `docker` and `pre-commit` ecosystems from the auto-merge group.

## Why

GitHub's native auto-merge is only safe when branch protection requires
status checks. Without that, native auto-merge can merge a PR whose CI is
still running — or worse, whose CI has failed. An actor-gated workflow that
triggers on `pull_request` and merges immediately because
`github.actor == 'dependabot[bot]'` reproduces the same defect: it can merge
a broken PR before any check has run.

The failure mode is a silent broken build. Dependabot bumps a lint tool to a
new major version that introduces a new rule. The auto-merge gate — gated
only on the actor — merges the bump before CI runs. The next contributor's
PR fails with a lint error they did not introduce, and the root cause (the
unreviewed auto-merged bump) is buried in the git history.

Waiting for `mergeable_state == "clean"` guarantees that every required
check in the branch-protection rule set has passed before the merge API is
called. The merge is CI-gated, not actor-gated.

Excluding `docker` and `pre-commit` ecosystems from auto-merge prevents a
second class of silent breakage:

- A `docker` bump rewrites a base-image digest; the new image may carry a
  breaking runtime change (different `PATH`, removed CA certificates,
  incompatible libc) that only surfaces at deploy time.
- A `pre-commit` bump rewrites hook `rev:` tags; a new hook release may
  introduce a lint rule that fails on existing code — exactly the same
  failure mode as a major lint-tool bump, but harder to spot because the
  diff is a single `rev:` line change in `.pre-commit-config.yaml`.

Both ecosystems deserve a human reviewer who understands the blast radius
before the merge lands.

## How

The fleet's shared reusable workflow
(`damien-robotsix/robotsix-github-workflows/.github/workflows/dependabot-auto-merge.yml`)
implements this convention. Every repo consumes it via a thin caller
workflow:

```yaml
# .github/workflows/dependabot-auto-merge.yml
name: Dependabot auto-merge

on:
  pull_request:

permissions: {}

jobs:
  auto-merge:
    if: github.actor == 'dependabot[bot]'
    permissions:
      contents: write
      pull-requests: write
    uses: damien-robotsix/robotsix-github-workflows/.github/workflows/dependabot-auto-merge.yml@<pinned-sha>
```

The reusable workflow triggers on `pull_request_target` (so it has write
access to merge), accepts a `target` input (`minor` or `patch`), and
internally polls `mergeable_state` until it reports `"clean"` before
calling the merge API.

The calling repo's `.github/dependabot.yml` must additionally exclude
`docker` and `pre-commit` ecosystems from the auto-merge group so those
bumps never reach the auto-merge workflow:

```yaml
# In .github/dependabot.yml — exclude docker and pre-commit from auto-merge
version: 2
updates:
  # ... other ecosystems ...
  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
    # No auto-merge group — these PRs require human review.
    open-pull-requests-limit: 5

  - package-ecosystem: "pre-commit"
    directory: "/"
    schedule:
      interval: "weekly"
    # No auto-merge group — these PRs require human review.
    open-pull-requests-limit: 5
```

When the `docker` or `pre-commit` ecosystem blocks have no `groups:` key
(or are absent from the auto-merge group), Dependabot still opens PRs for
them, but those PRs are not eligible for auto-merge — they land in the
review queue like any normal PR.

## Anti-patterns

Every one of these patterns is forbidden for Dependabot auto-merge:

| Forbidden | Why it fails |
|---|---|
| Auto-merge gated only on `github.actor == 'dependabot[bot]'` with no CI-status poll | Merges before CI runs — a broken build can land silently. |
| Native GitHub auto-merge without branch-protection status checks | GitHub's auto-merge is only safe when branch protection requires status checks; without them it can merge with absent or failed CI. |
| Including `docker` or `pre-commit` ecosystems in the auto-merge group | These ecosystems rewrite build environments or hook versions — a bump can break the build or the deploy environment with no human review. |
| Auto-merging major version bumps (`target: major`) | A major version bump to a build or test tool (e.g. ruff 1.x → 2.x) can introduce breaking changes that need human triage. |
| Using `pull_request` (instead of `pull_request_target`) for the merge workflow | `pull_request` runs in the PR's context with read-only tokens — it cannot merge. `pull_request_target` runs in the base branch's context with write access, which is correct for a merge workflow. |

## Exceptions

A repo may deviate from the CI-gated auto-merge rule when:

- **The repo has no CI.** If there are no required status checks,
  `mergeable_state` is always `"clean"` and the CI gate is vacuously
  satisfied. The repo still follows the ecosystem-exclusion rule
  (no `docker`/`pre-commit` in the auto-merge group) and the
  minor/patch-only rule.
- **The repo does not use Dependabot at all.** No auto-merge workflow is
  needed; the rule does not apply.

Both exceptions are narrow. The default is: if Dependabot auto-merge is
enabled, it is CI-gated, minor/patch-only, and excludes `docker` and
`pre-commit` ecosystems.

## Failure modes prevented

- **Silent broken builds from unreviewed auto-merges.** A Dependabot bump
  that passes no CI gates lands a broken change that surfaces on the next
  contributor's PR, with no obvious root cause.
- **Docker-image drift at deploy time.** A base-image digest bump that
  changes the runtime environment (CA certificates, libc, `PATH`) lands
  without review and breaks at deploy — potentially days after the merge.
- **Pre-commit hook version surprises.** A hook `rev:` bump introduces a
  new lint rule that fails on existing code. Without the ecosystem
  exclusion, this lands automatically and every subsequent PR fails with an
  unrelated lint error.
- **Major tool-version breakage.** A major version bump to a build or test
  tool (e.g. mypy 1.x → 2.x) changes the type-checking surface without a
  human reviewer understanding the impact.

## Relationship to other standards

- The Dependabot ecosystem configuration is defined in the
  [repo baseline](repo-baseline.md#automated-dependency-updates).
- The CI workflow that must pass before auto-merge is defined in the
  [Python CI workflow](python-ci-workflow.md) standard.
- The pre-commit hook set that must be excluded from auto-merge is defined
  in [Python practices](python.md#pre-commit-hooks) and the
  [pre-commit baseline](pre-commit-baseline.md).
- CI lint-tool pinning — the rule that keeps CI and pre-commit versions in
  lockstep — is defined in
  [CI lint tool pinning](ci-lint-pinning.md). The Dependabot auto-merge
  exclusion of the `pre-commit` ecosystem prevents an auto-merged hook bump
  from breaking that lockstep without review.
