# Release-please release automation

> **Scope: every robotsix repository** — libraries and deployable components
> alike. This page prescribes
> [release-please](https://github.com/googleapis/release-please) as the
> fleet-wide release-automation tool — replacing the previous towncrier-based
> workflow documented in [changelog & releases](changelog-driven-releases.md)
> and [towncrier](towncrier.md).

Release-please owns the entire release pipeline: it reads the static version
from `pyproject.toml`, opens a release PR that bumps the version and generates
release notes from conventional commits, and on merge creates the git tag and
GitHub Release — all driven by the `googleapis/release-please-action` GitHub
Action.

## Why release-please

The previous towncrier-based workflow required per-PR fragment files in
`changelog.d/`, a CI gate to enforce them, and a separate auto-release workflow
that ran weekly to classify fragments, bump the version, compile the changelog,
and push a tag. This worked but added friction: every PR needed a fragment file
with the right extension, the CI gate blocked PRs that forgot one, and the
release workflow was a separate scheduled job whose output (tag, changelog,
version bump) was opaque until it ran.

Release-please replaces this with **conventional commits** — the commit message
itself is the changelog entry and the bump signal. No fragment files, no
separate release workflow, no manual bump classification. A release PR opens
automatically whenever releasable commits land on the default branch; merging
it publishes the release.

## Configuration

Every repo carries two config files at its root:

### `release-please-config.json`

```json
{
  "$schema": "https://raw.githubusercontent.com/googleapis/release-please/main/schemas/config.json",
  "release-type": "python",
  "changelog-path": "CHANGELOG.md",
  "include-v-in-tag": true,
  "packages": {
    ".": {}
  }
}
```

- **`release-type`** — `"python"`. Release-please reads the static
  `[project].version` from `pyproject.toml`, bumps it according to the
  conventional-commit types in the release PR, and writes it back.
- **`changelog-path`** — `"CHANGELOG.md"`. Generated release notes are
  prepended to this file at the top of the `##` section for the new version.
- **`include-v-in-tag`** — `true`. Tags are `vX.Y.Z` (matching the existing
  `docker-release.yml` tag filter `["*.*.*"]` — the `v` prefix is part of
  the tag name).
- **`packages`** — a single root package `"."`. Monorepo repos with multiple
  publishable packages list each package directory here; single-package repos
  use the root.

### `.release-please-manifest.json`

```json
{
  ".": "0.1.0"
}
```

The manifest records the last released version for each package. Release-please
reads it on startup to know where the previous release left off; it updates
the manifest automatically when a release PR is merged. The initial value is
the current version in `pyproject.toml`.

## How it works

1. **On every push to the default branch**, the `googleapis/release-please-action`
   inspects commits since the last release (tracked in
   `.release-please-manifest.json`).
2. **If releasable commits exist** (commits with `feat:`, `fix:`, or
   `feat!:`/`fix!:` prefixes), release-please opens or updates a **release PR**
   that:
   - Bumps the version in `pyproject.toml` and `.release-please-manifest.json`
     (minor for `feat`, patch for `fix`, major for `!` breaking markers).
   - Prepends generated release notes to `CHANGELOG.md` under a new `## X.Y.Z`
     heading.
3. **When the release PR is merged**, the same action:
   - Creates a git tag `vX.Y.Z` on the merge commit.
   - Creates a GitHub Release with the generated notes.

The action runs on two triggers: `push` to the default branch (to open/update
the release PR) and `pull_request` `closed` on the default branch (to create
the tag and release when the release PR is merged).

## Workflow file

Every repo wires the action in `.github/workflows/release-please.yml`:

```yaml
name: release-please

on:
  push:
    branches:
      - main
  pull_request:
    types:
      - closed
    branches:
      - main

permissions:
  contents: write
  pull-requests: write

jobs:
  release-please:
    runs-on: ubuntu-latest
    if: |
      github.event_name == 'push' ||
      (github.event_name == 'pull_request' &&
       github.event.pull_request.merged == true &&
       github.event.pull_request.head.ref == 'release-please--branches--main')
    steps:
      - uses: googleapis/release-please-action@<COMMIT_SHA>  # see pinning note below
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
```

The `if` guard ensures the action only creates tags/releases on merge of its
own release PR, not on merge of any other PR.

> **Pinning.** Pin the action to a commit SHA, not a tag. Resolve the SHA
> with:
>
> ```bash
> url=https://github.com/googleapis/release-please-action.git
> git ls-remote "$url" "refs/tags/v4^{}" "refs/tags/v4" \
>   | awk '/\^\{\}$/{c=$1} !/\^\{\}$/{p=$1} END{print (c!=""?c:p)}'
> ```

## Shared reusable workflow

Optionally, the fleet may carry a shared reusable workflow in
[robotsix-github-workflows](https://github.com/damien-robotsix/robotsix-github-workflows)
(`release-please.yml`) so member repos adopt it in one `uses:` line —
mirroring the existing `docker-release.yml` pattern:

```yaml
jobs:
  release-please:
    uses: damien-robotsix/robotsix-github-workflows/.github/workflows/release-please.yml@<COMMIT_SHA>
    secrets: inherit
```

When the shared workflow exists, member repos use it instead of inlining the
action. Until then, the inline workflow above is the canonical setup.

## Conventional commits

Release-please determines the semver bump from
[Conventional Commits](https://www.conventionalcommits.org/) prefixes in merge
commit messages:

| Prefix | Bump | Example |
|---|---|---|
| `fix:` | patch | `fix: handle empty mail poller response` |
| `feat:` | minor | `feat: add retry to the mail poller` |
| `fix!:` / `feat!:` | major | `feat!: drop support for Python 3.12` |
| `docs:`, `chore:`, `test:`, `ci:` | none — not included in release notes | `chore: bump ruff` |

The `!` marker (before the colon) signals a breaking change. A commit footer
`BREAKING CHANGE:` also triggers a major bump.

Commits with types outside the conventional set (`docs`, `chore`, `test`,
`ci`, `style`, `refactor`, `perf`, `build`) do not appear in the generated
release notes and do not trigger a bump — release-please ignores them for
versioning purposes.

## Rules

### 1. Every repo wires release-please

**Rule:** Every robotsix repo carries a `release-please-config.json`, a
`.release-please-manifest.json`, and a `.github/workflows/release-please.yml`
(or the shared reusable workflow equivalent).

**Rationale:** Without release-please, a repo has no mechanism to create
version tags or compile changelogs automatically. Tags must be pushed by hand,
and the shared `docker-release.yml` workflow — which gates Docker publishing
on `tags: ["*.*.*"]` — never fires.

> **Failure mode.** A repo that lacks release-please accumulates conventional
> commits on its default branch with no release PR, no version bump, and no
> tag. The version in `pyproject.toml` stays at the last manually-set value;
> downstream consumers resolving via git see a dirty `0.x.dev` version
> forever, and there is no auditable changelog of what changed.

### 2. The release PR is the sole version-bump mechanism

**Rule:** `pyproject.toml` `[project].version` is never edited by hand.
Release-please owns the version — it is the only writer of the version field.
The `.release-please-manifest.json` is likewise never hand-edited; it tracks
the last released version and release-please updates it automatically.

**Rationale:** A hand-edited version drifts from the manifest, causing
release-please to open a release PR for the wrong version or to skip versions
entirely. The manifest is the source of truth for "what was last released";
editing it by hand breaks the automation.

> **Failure mode.** A contributor bumps the version in `pyproject.toml`
> directly (e.g. from `0.3.0` to `0.4.0`) without going through release-please.
> Release-please sees the manifest still at `0.3.0` and opens a release PR
> proposing `0.3.1` — a downgrade. The tag `v0.3.1` is created on a tree that
> already declares `0.4.0`, and every runtime version check thereafter reports
> a mismatch.

### 3. Conventional commits are the single source of changelog content

**Rule:** Every PR that changes user-visible behaviour uses a conventional
commit prefix (`fix:`, `feat:`, or the `!` breaking marker). The commit
message body — what appears under the prefix — is the changelog entry. There
are no fragment files; `CHANGELOG.md` is written exclusively by release-please.

**Rationale:** Conventional commits eliminate the fragment-file overhead
(per-PR file creation, CI gate, skip-changelog label, fragment registration in
`modules.yaml`). The commit message is already written as part of the PR; using
it as the changelog entry removes a duplicate step.

> **Failure mode.** A repo adopts release-please but contributors do not use
> conventional commit prefixes. Release-please sees no releasable commits and
> never opens a release PR. The version stays frozen, and the changelog is
> empty despite months of merged PRs.

### 4. Versions stay 0.x until 1.0.0 is declared deliberately

**Rule:** Versions stay `0.x` under semver. Bumping to `1.0.0` is a human
decision — it is never automated. Under 0.x there is no compatibility promise,
which matches the stack's pre-release, clean-cutover stance.

**Rationale:** Semver `0.x` means "no stability guarantee" — the public API may
change at any minor bump. This is the correct posture for a stack under active
development where clean cutover is the default migration strategy. Automating a
`1.0.0` bump would make an unintended stability promise.

> **Failure mode.** A repo whose release-please workflow bumps to `1.0.0`
> automatically signals API stability that does not exist — consumers treat
> minor bumps as safe and are broken by a breaking change that arrived without
> a major-version signal.

### 5. Config files are registered in docs/modules.yaml

**Rule:** When a new `release-please-config.json` or
`.release-please-manifest.json` file is created, its path must be added to
`docs/modules.yaml` under the appropriate module's `paths` list. This applies
even when no Python files are modified.

**Rationale:** The module-registration drift check fails CI when a file matches
no module's globs. Without this rule, every new release-please config file
would fail CI until someone manually registers it.

> **Failure mode.** A contributor adds the config files, CI fails with a drift
> error, and the contributor either removes the files (breaking release
> automation) or spends time diagnosing a registration failure.

## Reference

- **release-please:** [https://github.com/googleapis/release-please](https://github.com/googleapis/release-please)
- **release-please-action:** [https://github.com/googleapis/release-please-action](https://github.com/googleapis/release-please-action)
- **Conventional Commits:** [https://www.conventionalcommits.org/](https://www.conventionalcommits.org/)
- **Python release-type:** release-please reads `[project].version` from
  `pyproject.toml` and writes the bumped version back to the same field.
