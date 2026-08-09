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

## Prerequisite: let Actions open pull requests

**Before any of the configuration below matters**, the repository must allow
GitHub Actions to open pull requests. Release-please's entire mechanism is
opening a release PR, so without this it can do nothing.

Settings → Actions → General → *"Allow GitHub Actions to create and approve
pull requests"*, or via the API:

```bash
# check
gh api repos/damien-robotsix/<repo>/actions/permissions/workflow \
  -q '.can_approve_pull_request_reviews'
# enable
gh api -X PUT repos/damien-robotsix/<repo>/actions/permissions/workflow \
  -f default_workflow_permissions=read -F can_approve_pull_request_reviews=true
```

> **Failure mode.** With the setting off, the run gets as far as building the
> tree and the release commit, then dies with
> `release-please failed: GitHub Actions is not permitted to create or approve
> pull requests.` The workflow and both config files can be perfectly correct
> and the repo still never releases. On 2026-08-08 this was off in 9 of 15
> fleet repos, which is why release-please had produced nothing anywhere.

## Configuration

Every repo carries two config files at its root:

### `release-please-config.json`

```json
{
  "$schema": "https://raw.githubusercontent.com/googleapis/release-please/main/schemas/config.json",
  "release-type": "python",
  "changelog-path": "CHANGELOG.md",
  "include-v-in-tag": true,
  "bump-minor-pre-major": true,
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
- **`bump-minor-pre-major`** — `true`. **Required to satisfy rule 5 below.**
  Without it a breaking conventional commit (`feat!:` / `fix!:`) bumps the
  *major* version even from `0.x`, so the first breaking change in any repo
  proposes `1.0.0`. With it, breaking changes bump the minor while the version
  stays below `1.0.0`, which is what a 0.x posture means.
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
  workflow_dispatch:

# Serialise releases per branch. Deliberately NOT cancel-in-progress: a cancel
# between pushing the release commit and creating the tag would leave the repo
# half-released.
concurrency:
  group: ${{ github.workflow }}-${{ github.ref_name }}
  cancel-in-progress: false

# Job-scoped below, not here.
permissions: {}

jobs:
  release-please:
    name: Release Please
    runs-on: ubuntu-latest
    permissions:
      contents: write       # create the release commit, tag and GitHub Release
      pull-requests: write  # open and update the release PR
    if: |
      github.event_name == 'push' ||
      github.event_name == 'workflow_dispatch' ||
      (github.event_name == 'pull_request' &&
       github.event.pull_request.merged == true &&
       github.event.pull_request.head.ref == 'release-please--branches--main')
    steps:
      # Mint a GitHub App installation token. NOT GITHUB_TOKEN — see below.
      - name: Mint a GitHub App installation token
        id: app-token
        uses: actions/create-github-app-token@fee1f7d63c2ff003460e3d139729b119787bc349  # v2.2.2
        with:
          app-id: ${{ vars.RELEASE_APP_ID }}
          private-key: ${{ secrets.RELEASE_APP_PRIVATE_KEY }}
          # Scope the token. Without at least one `permission-*` input it
          # inherits the App's blanket installation permissions, which zizmor
          # flags as a high-severity finding.
          permission-contents: write        # release commit, tag, Release
          permission-pull-requests: write   # open and update the release PR

      - uses: googleapis/release-please-action@<COMMIT_SHA>  # see pinning note below
        with:
          token: ${{ steps.app-token.outputs.token }}
```

> **The token must not be `GITHUB_TOKEN`.** GitHub deliberately suppresses
> workflow runs for events created by `GITHUB_TOKEN`, to prevent recursion. A
> release PR opened with it therefore triggers **no CI at all** — every
> required status check stays pending forever and the PR can never be merged
> on a protected branch. The PR looks fine; it simply reports
> `no checks reported on the 'release-please--branches--main' branch`.
>
> Observed 2026-08-08 across six repos at once: llmio, board, standards, mill,
> http and auto-mail all opened release PRs that could not merge.
> `robotsix-file-hub` released successfully only because its default branch is
> unprotected.
>
> `RELEASE_APP_ID` (variable) and `RELEASE_APP_PRIVATE_KEY` (secret) are the
> same fleet App credentials used elsewhere; see the prerequisite section
> above.

The `if` guard ensures the action only creates tags/releases on merge of its
own release PR, not on merge of any other PR.

**Every element above is load-bearing** — an earlier version of this template
omitted four of them and failed the fleet's own `lint-workflows` audit:

- **`permissions: {}` at the top with write scopes on the job.** zizmor's
  `excessive-permissions` rejects workflow-level `contents: write` /
  `pull-requests: write`, because they are then granted to every job.
- **A comment on each permission.** zizmor's `undocumented-permissions`.
- **`name:` on the job.** zizmor's `anonymous-definition` is only *info*
  severity, but the shared `lint-workflows` reusable fails on it (exit 11).
- **A `concurrency:` block.** zizmor's `concurrency-limits` (exit 12).

**`workflow_dispatch`** is not required by zizmor but is required in practice:
without it the workflow can only be exercised by landing a commit on the
default branch, so a misconfiguration cannot be verified until after it has
already failed on `main`.

> **Baseline pin.** A repo migrating from towncrier must also bump its
> `baseline-check.yml` caller to `a6378ac` or later. Earlier revisions require
> `changelog.d/` and `[tool.towncrier]` unconditionally, so they fail the very
> commit that removes them.
>
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

### 3. The version is declared statically

**Rule:** `pyproject.toml` declares the version as a literal in `[project]`:

```toml
[project]
version = "0.4.0"
```

It must **not** be computed. Specifically, `dynamic = ["version"]` combined
with a VCS-derived source is disallowed:

```toml
# DISALLOWED — the version is computed from git tags at build time
[build-system]
requires = ["hatchling", "hatch-vcs"]

[tool.hatch.version]
source = "vcs"
```

The equivalent `setuptools_scm` configuration is disallowed for the same
reason.

**Rationale:** Release-please's model is *edit the version files, commit, then
tag*. Its Python strategy rewrites `[project].version` in `pyproject.toml`,
`__version__` in the package's `__init__.py`, and
`.release-please-manifest.json`, then tags the resulting commit.

A VCS-derived version inverts that arrow — the tag produces the version, so
there is no file to rewrite. The two mechanisms then disagree about who owns
the number: release-please bumps the manifest while the built artifact takes
its version from `git describe` independently. Rule 2 above ("release-please
is the only writer of the version field") is unsatisfiable when no version
field exists.

A **file-based** dynamic source is a narrower case:

```toml
[tool.hatch.version]
path = "src/<package>/__init__.py"
```

Here the version *is* in a file, and release-please already rewrites that file,
so it happens to work. It is still disallowed: `[project]` then carries no
version for a reader or tool to find, and the arrangement only functions
because two independent tools happen to agree on one path. Declare the literal
and let hatchling read it.

**Migrating off a VCS version:** replace `dynamic = ["version"]` with the
literal, drop `hatch-vcs` from `build-system.requires` and delete the
`[tool.hatch.version]` block. Choose the starting version deliberately — an
untagged repo has been building `0.x.dev<distance>+g<sha>` strings, which are
not a release history to continue from.

> **Failure mode.** A repo on `hatch-vcs` with no tags builds as
> `0.1.dev47+gf2a91c3`. Add release-please and it opens a release PR that bumps
> a manifest and nothing else; merging tags the commit, and only then does the
> package version change — via a completely different mechanism. Every
> subsequent release PR proposes a bump from a number the build does not use.
>
> Dropping the VCS source also removes a whole class of Docker failure: the
> `.git` directory is normally excluded from the build context, so a
> VCS-derived version cannot be computed there at all, and the build needs a
> `SETUPTOOLS_SCM_PRETEND_VERSION` escape hatch to work around its own
> versioning scheme.

### 4. Conventional commits are the single source of changelog content

**Rule:** Every PR that changes user-visible behaviour uses a conventional
commit prefix (`fix:`, `feat:`, or the `!` breaking marker). The commit
message body — what appears under the prefix — is the changelog entry. There
are no fragment files; `CHANGELOG.md` is written exclusively by release-please.

**Rationale:** Conventional commits eliminate the fragment-file overhead
(per-PR file creation, CI gate, skip-changelog label, fragment registration in
`modules.yaml`). The commit message is already written as part of the PR; using
it as the changelog entry removes a duplicate step.

This applies to **automation as much as to people**. Any tool that opens PRs
against a fleet repo must title them conventionally.

**Which subject release-please actually reads.** Every fleet repo sets
`squash_merge_commit_title = COMMIT_OR_PR_TITLE`. GitHub squashes a
**single-commit** PR under that commit's own subject, and a **multi-commit** PR
under the PR title. A tool that sets one but not the other therefore produces
parseable subjects only some of the time, depending on how many commits the
branch happened to end up with:

```bash
# What the repo will use as the squash subject
gh api repos/OWNER/REPO -q '.squash_merge_commit_title'
```

> **Failure mode — measured, not hypothetical (2026-08-09).** robotsix-mill
> titled every commit and PR `mill: <title> (<id>)`. `mill` is not a
> conventional type, so release-please discarded those commits: they landed on
> `main` but reached neither `CHANGELOG.md` nor any version bump. A fleet audit
> of the last 100 commits on each repo's `main` found **1055 of 1073**
> non-conventional subjects were mill's — between 56% and 93% per repo. The
> pipeline was working correctly over a stream where three of every four
> changes were silently dropped. Fixed in robotsix-mill#2802 by deriving the
> type from the changelog fragment the implement agent already writes.
>
> The lesson generalises: **a release pipeline that ignores unparsable commits
> fails silently.** Nothing goes red. Audit what fraction of your history is
> actually conventional before trusting an empty release PR to mean "no
> changes".

### 5. Versions stay 0.x until 1.0.0 is declared deliberately

**Rule:** Versions stay `0.x` under semver. Bumping to `1.0.0` is a human
decision — it is never automated. Under 0.x there is no compatibility promise,
which matches the stack's pre-release, clean-cutover stance.

**Rationale:** Semver `0.x` means "no stability guarantee" — the public API may
change at any minor bump. This is the correct posture for a stack under active
development where clean cutover is the default migration strategy. Automating a
`1.0.0` bump would make an unintended stability promise.

**How it is enforced:** `"bump-minor-pre-major": true` in
`release-please-config.json`. This rule is not self-enforcing — release-please
bumps the major on a `feat!:` / `fix!:` commit by default, so a repo that omits
the flag violates this rule the first time anyone lands a breaking change.

> **Failure mode.** A repo whose release-please workflow bumps to `1.0.0`
> automatically signals API stability that does not exist — consumers treat
> minor bumps as safe and are broken by a breaking change that arrived without
> a major-version signal.
>
> Observed 2026-08-08 on `robotsix-file-hub`: the first run after release-please
> was made functional proposed `chore(main): release 1.0.0`, because the config
> block above had been copied without the flag. Adding it produced the correct
> `0.2.0` — a minor bump that still recorded the breaking change in the
> changelog under **⚠ BREAKING CHANGES**, which is the intended behaviour: the
> break is documented, the stability promise is not made.

### 6. Config files are registered in docs/modules.yaml

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

## Traps

Three failure modes surfaced during the fleet-wide rollout. All three pass CI
on the PR that introduces them and only break later.

### `uv.lock` records the project's own version

A `uv` project pins itself in `uv.lock`. Release-please bumps
`[project].version` in `pyproject.toml` but knows nothing about the lock, so the
release commit leaves the two disagreeing and every subsequent
`uv sync --locked` fails — including in the Docker build, long after the release
PR merged.

`--frozen` does not check, so a repo using it will not notice until something
else does.

Do **not** try to fix this with release-please's `extra-files`: a lock entry
needs a jsonpath into an array whose index shifts with every dependency change.
Add a step to the release workflow instead, guarded on a release PR having been
opened:

```yaml
- name: Sync uv.lock to the released version
  if: steps.release.outputs.prs_created == 'true' || steps.release.outputs.pr != ''
  env:
    GH_TOKEN: ${{ steps.app-token.outputs.token }}
    BRANCH: release-please--branches--main
  run: |
    set -euo pipefail
    git fetch --depth=1 origin "$BRANCH"
    git checkout -B "$BRANCH" "origin/$BRANCH"
    uv lock
    git diff --quiet -- uv.lock && exit 0
    git config user.name "github-actions[bot]"
    git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
    git commit -m "chore: sync uv.lock to the released version" -- uv.lock
    git push "https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" "$BRANCH"
```

Set `enable-cache: false` on `setup-uv` here — this job holds `contents: write`,
and a poisoned cache in a write-privileged workflow is a supply-chain risk
(zizmor `cache-poisoning`).

### Markdownlint rejects the generated CHANGELOG

Release-please's output is not markdownlint-clean: it emits bare URLs, long
lines, and duplicate headings across versions. A repo that lints `**/*.md` goes
red on the release PR itself — the one PR nobody can hand-fix, because the file
is regenerated on every run.

Exclude the generated file rather than fighting it:

```yaml
# .markdownlint-cli2.yaml
ignores:
  - CHANGELOG.md   # generated by release-please; not hand-edited
```

### A release PR that never merges is usually a token problem

If a release PR opens but its required checks never report, the workflow is
using `GITHUB_TOKEN`. Events created by it deliberately do not trigger workflow
runs, so the checks never start and the PR cannot satisfy them. Mint a scoped
App token instead — see the workflow template above.

A release PR that never *opens* is the other half: check that the repo setting
in [Prerequisite](#prerequisite-let-actions-open-pull-requests) is enabled, and
that no `if:` gate references a secret that was never provisioned. A gate on a
missing secret makes the step **skip** while the job still reports success.

## Migration checklist

This is the step-by-step playbook for a fleet repo moving OFF
towncrier/hatch-vcs/auto-release.yml/changelog.d and ONTO release-please.
Each step is atomic and independently verifiable — run CI after each one
rather than stacking them into a single commit.

### 1. Delete the towncrier config

Remove the `[tool.towncrier]` block from `pyproject.toml`. If the repo has a
`towncrier.toml` or `towncrier.toml` at the repo root, delete that file too.

```bash
git rm pyproject.toml  # after editing out the block
# or
git rm towncrier.toml
```

> **Verification.** `grep -r towncrier pyproject.toml` returns nothing and CI
> passes (the baseline-check towncrier gate previously required this block;
> after step 9 it no longer does).

### 2. Remove the changelog fragment directory

Delete `changelog.d/` and all its contents. There is no seed step —
release-please generates release notes from commit messages, never from
fragment files.

```bash
git rm -r changelog.d/
```

If `.gitignore` lists `changelog.d/`, drop that line.

> **Verification.** `ls changelog.d/` fails with "No such file". CI passes
> (the baseline-check changelog gate previously required this directory; after
> step 9 it no longer does).

### 3. Remove the old auto-release workflow

Delete `.github/workflows/auto-release.yml`. This is the weekly towncrier
release workflow — release-please replaces it with an event-driven workflow
that opens a release PR on every push to the default branch.

```bash
git rm .github/workflows/auto-release.yml
```

> **Verification.** The file is gone. No CI step references it; if
> `ci.yml` or `docs.yml` called it, those references must also be removed.

### 4. Make the version static

If `pyproject.toml` uses `dynamic = ["version"]` with a VCS-derived source
(`hatch-vcs` or `setuptools_scm`):

1. Replace `dynamic = ["version"]` with `version = "X.Y.Z"` — choose the
   starting version deliberately (see step 7).
2. Drop `hatch-vcs` (or `setuptools_scm`) from `build-system.requires`.
3. Delete the `[tool.hatch.version]` (or `[tool.setuptools_scm]`) block.

A file-based dynamic source (`[tool.hatch.version] path = "src/.../__init__.py"`)
is also disallowed — move the literal into `[project]` and delete the block.

```toml
# Before (VCS-derived — disallowed)
[project]
dynamic = ["version"]

[build-system]
requires = ["hatchling", "hatch-vcs"]

[tool.hatch.version]
source = "vcs"

# After (static — required)
[project]
version = "0.1.0"

[build-system]
requires = ["hatchling"]
```

> **Verification.** `pyproject.toml` has a literal `version = "..."` under
> `[project]` with no `dynamic` key for version. `uv lock` succeeds.

### 5. Add the release-please config files

Create two files at the repo root:

**`release-please-config.json`** — copy from the [Configuration](#configuration)
section above.

**`.release-please-manifest.json`** — set the initial version to the current
`[project].version` (see step 7 for how to pick it):

```json
{
  ".": "0.1.0"
}
```

Register both paths in `docs/modules.yaml` under the appropriate module's
`paths` list.

> **Verification.** `cat .release-please-manifest.json` shows a version that
> matches `pyproject.toml` `[project].version`.

### 6. Add the release-please workflow

Copy the workflow template from the [Workflow file](#workflow-file) section
into `.github/workflows/release-please.yml`. Pin the action SHA — resolve it
with:

```bash
url=https://github.com/googleapis/release-please-action.git
git ls-remote "$url" "refs/tags/v5^{}" "refs/tags/v5" \
  | awk '/\^\{\}$/{c=$1} !/\^\{\}$/{p=$1} END{print (c!=""?c:p)}'
```

If the repo is not a `uv` project, omit the `uv.lock` sync step. If the repo
uses the shared reusable workflow from `robotsix-github-workflows`, use that
instead of inlining.

> **Verification.** The workflow file passes `zizmor` (or the fleet
> `lint-workflows` gate). The token step uses an App installation token, not
> `GITHUB_TOKEN`.

### 7. Seed the initial version

Release-please uses `.release-please-manifest.json` as the baseline — it
proposes a bump *from* that version. Pick the starting version:

- **If the repo already has tags:** set the manifest to the latest tag's
  version (without the `v` prefix). Release-please will propose the next bump.
- **If the repo has no tags (or only VCS-derived dev versions):** choose the
  version deliberately. An untagged repo on `hatch-vcs` has been building
  `0.x.dev<distance>+g<sha>` strings — those are not a release history.
  `0.1.0` is a reasonable starting point for a repo that has never been
  released; for a repo with existing releases made by hand, set it to the
  version already in `pyproject.toml`.

> **Verification.** The version in `.release-please-manifest.json` and
> `pyproject.toml` `[project].version` agree.

### 8. Preserve changelog history

Release-please prepends new release notes to `CHANGELOG.md`. Any existing
changelog content must be preserved below a marker so it is not lost:

1. If `CHANGELOG.md` already has a release-please header (`# Changelog`),
   the existing content is already in the right format — leave it.
2. If the changelog was towncrier-generated (starts with a towncrier header
   like `# Release Notes`), wrap the existing content under a
   `## Pre-release-please history` heading at the bottom of the file, and add
   a `# Changelog` heading at the top:

   ```markdown
   # Changelog

   ## Pre-release-please history

   (existing towncrier content here)
   ```

3. Exclude `CHANGELOG.md` from markdownlint — release-please output is not
   lint-clean. Add to `.markdownlint-cli2.yaml`:

   ```yaml
   ignores:
     - CHANGELOG.md
   ```

> **Verification.** `head -1 CHANGELOG.md` is `# Changelog`. The file passes
> CI (no markdownlint violations on it).

### 9. Bump the baseline-check caller

The fleet's `baseline-check.yml` reusable workflow at revisions before
`a6378ac` requires `changelog.d/` and `[tool.towncrier]` unconditionally.
Bump the caller in `.github/workflows/baseline-check.yml` (or wherever the
repo calls the shared workflow) to `a6378ac` or later:

```yaml
uses: damien-robotsix/robotsix-github-workflows/.github/workflows/baseline-check.yml@a6378accaf26c75b12fac324c3056255647c107b # main
```

> **Verification.** The baseline-check job passes after the towncrier +
> changelog.d removal. If it fails with "towncrier config not found" or
> "changelog.d directory is empty", the SHA is too old.

### 10. Enable Actions to create pull requests

Release-please's entire mechanism is opening a release PR. The repo setting
must allow this. Check and enable via the API (see
[Prerequisite](#prerequisite-let-actions-open-pull-requests)):

```bash
gh api -X PUT repos/damien-robotsix/<repo>/actions/permissions/workflow \
  -f default_workflow_permissions=read -F can_approve_pull_request_reviews=true
```

> **Verification.** The API returns `can_approve_pull_request_reviews: true`.
> Without this, the first push to `main` runs the workflow and it dies with
> `release-please failed: GitHub Actions is not permitted to create or approve
> pull requests`.

### 11. Verify end-to-end

Push a commit with a conventional subject (`fix:`, `feat:`) to the default
branch. Within a minute the release-please workflow runs and opens a release
PR. Merge it (if appropriate) or close it as a smoke test.

> **Verification.** A release PR exists, its checks pass, and merging it
> creates a tag and GitHub Release. The version in `pyproject.toml` has been
> bumped by release-please.

## Reference

- **release-please:** [https://github.com/googleapis/release-please](https://github.com/googleapis/release-please)
- **release-please-action:** [https://github.com/googleapis/release-please-action](https://github.com/googleapis/release-please-action)
- **Conventional Commits:** [https://www.conventionalcommits.org/](https://www.conventionalcommits.org/)
- **Python release-type:** release-please reads `[project].version` from
  `pyproject.toml` and writes the bumped version back to the same field.
