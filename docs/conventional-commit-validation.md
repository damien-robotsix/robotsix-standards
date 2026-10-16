# Conventional commit validation

> **Scope: Python repositories** — This page prescribes the **Python toolchain**
> for validating Conventional Commits using commitizen (`pyproject.toml` configuration).
> While every repo that wires release-please must validate commit messages per
> [release-please rule 1](release-please.md#1-every-repo-wires-release-please),
> this page covers only the Python implementation; the commit-message grammar and
> prefix-to-bump mapping are canonical in [release-please § Conventional commits](release-please.md#conventional-commits).
> Non-Python ecosystems (Node.js, PHP, ROS 2, Dart, …) wire the equivalent local
> hook per
> [Conventional commit validation (multi-language)](conventional-commit-validation-languages.md);
> the commitlint CI check is identical across every language.

Release-please derives every version bump and changelog entry from the
Conventional Commits prefix on the commits that land on the default branch.
That contract is only as reliable as the commit messages feeding it, yet
nothing in the baseline actually *checks* the format: a malformed subject
(`Fixed the bug`, `feature: …`, a bare `WIP`) sails through, and release-please
silently treats it as a non-releasable commit — no bump, no changelog line.

Validation is two layers, because neither alone is sufficient:

1. **[commitizen](https://commitizen-tools.github.io/commitizen/) (`cz check`)
   as a `commit-msg` pre-commit hook** — gives the developer immediate, local
   feedback the moment they write a non-conforming message, before the commit
   object even exists.
2. **a commitlint GitHub Action in CI** — validates the message that actually
   reaches the default branch. On a **squash merge** (the fleet default) the
   merged commit's subject is the *PR title*, which no local `commit-msg` hook
   ever saw. Only a CI check on the PR title/merge commit can catch it.

## Why both layers

A `commit-msg` hook runs on the developer's machine and only on the commits
they author locally. It cannot see the squash-merge commit GitHub synthesises
from the PR title, and it is trivially bypassed (`git commit --no-verify`,
web-UI edits, agents that commit without installing hooks). The CI check is the
authoritative gate — it runs host-side on every PR and blocks the merge — while
the pre-commit hook exists to shorten the feedback loop so the CI gate rarely
has to fail.

## Pre-commit hook

Add the commitizen hook to `.pre-commit-config.yaml`, registered on the
`commit-msg` stage (not the default `pre-commit` stage — it validates the
message, which does not exist yet at `pre-commit` time):

```yaml
  - repo: https://github.com/commitizen-tools/commitizen
    rev: v4.19.2
    hooks:
      - id: commitizen
        stages: [commit-msg]
```

The `rev` follows the fleet pinning rule — a tagged release, bumped
deliberately, never floating (`main` / `master`). Because the hook runs at the
`commit-msg` stage, `pre-commit install` alone is not enough; the repo's dev
setup must also run `pre-commit install --hook-type commit-msg` (the shared
developer-setup target already does this). commitizen reads its ruleset from
`[tool.commitizen]` in `pyproject.toml`; the default `cz_conventional_commits`
ruleset matches the prefix set release-please recognises, so no extra
configuration is required.

## CI check

CI validates the Conventional Commits format on the PR title (the future
squash-merge subject) and the merge commit using a commitlint GitHub Action.
Following the fleet convention that standards pages never embed
GitHub-workflow YAML, this page does not reproduce the workflow: the caller
stub lives in the
[robotsix-github-workflows](https://github.com/damien-robotsix/robotsix-github-workflows)
README, version-pinned alongside the workflow it calls, so the two cannot
drift. A repo wires the stub in `.github/workflows/`; the check is a required
status on the default branch so a non-conforming PR title cannot merge.

## Rules

### 1. Every release-please repo validates commit messages

**Rule:** Every repo that wires release-please carries both the commitizen
`commit-msg` pre-commit hook and the commitlint CI check. Neither substitutes
for the other.

**Rationale:** The pre-commit hook gives fast local feedback but cannot see
squash-merge commits or unhooked authors; the CI check is authoritative but
only reports after the PR is open. Together they catch malformed messages at
both the point of authorship and the point of merge.

> **Failure mode this prevents.** A malformed subject (`Fixed login`,
> `feature: add retry`, `WIP`) reaches the default branch. release-please does
> not recognise the prefix, so it silently drops the commit from the release
> PR: no version bump, no changelog entry. The change ships, but the release
> notes and the tag never reflect it — and the omission is invisible until a
> consumer asks why a shipped fix is absent from the changelog.

### 2. The CI check gates the PR title, not just local commits

**Rule:** The commitlint CI check validates the PR title (the squash-merge
subject) and is a required status check on the default branch.

**Rationale:** The fleet squash-merges, so the message release-please reads is
the PR title — a string no local `commit-msg` hook ever validates. A check that
only inspected the individual commits of the branch would pass a PR whose title
is malformed and let the bad subject land on `main`.

> **Failure mode this prevents.** A PR with well-formed local commits but a
> free-text title (`Update the poller`) squash-merges a non-conforming subject
> onto the default branch, defeating the entire pre-commit layer and breaking
> the release-please bump exactly as in rule 1.
