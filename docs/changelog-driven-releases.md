# Changelog & releases

> **Superseded:** [release-please](release-please.md) is the fleet-wide release
> automation. This page documents the prior towncrier convention, kept for
> historical reference.
>
> **Scope: every robotsix repository** — libraries and deployable components
> alike, in any language. This page codifies the fragment-driven release
> convention already in use across the fleet; it is *in addition to* the
> [repo baseline](repo-baseline.md).

Releases are driven by towncrier changelog fragments under `changelog.d/`,
compiled by the shared auto-release workflow — not by hand-maintaining a
Keep-a-Changelog file and manually creating tags.

For a library whose version is derived from git tags via hatch-vcs
(`[tool.hatch.version] source = "vcs"`), **creating an annotated git tag IS the
entire release process** — there is no package to publish. The reference
implementation lives in
[robotsix-github-workflows](https://github.com/damien-robotsix/robotsix-github-workflows)
(`auto-release.yml`).

## Why this convention

A repo that maintains a hand-edited `CHANGELOG.md` with no towncrier fragment
directory and no auto-release workflow accumulates completed entries under an
`## 0.0.0 (unreleased)` heading with no mechanism to ever become a release.
Because hatch-vcs derives the version from the tag, an untagged project can
literally never emit a clean release version to downstream `uv.sources`
consumers — they always resolve a dirty `0.x.dev<distance>+g<sha>` version
instead of the tagged `X.Y.Z` the library's own `pyproject.toml` declares.

Towncrier fragments solve the merge-conflict problem (parallel PRs each have
their own file — the changelog itself is never a conflict surface) and the
"what bump?" problem (the fragment type determines the semver bump).

## Rules

### 1. Every PR adds a newsfragment

**Rule:** Every PR that changes user-visible behaviour adds a file to
`changelog.d/` with one of these extensions: `.breaking.md`, `.feature.md`,
`.bugfix.md`, or `.misc.md`. The filename is the issue/PR identifier followed by
the extension (e.g. `changelog.d/123.bugfix.md`). A PR with no user-visible
effect (CI-only, test-only, tooling-internal) adds the `skip-changelog` label
instead.

**Rationale:** Per-PR fragment files eliminate changelog merge conflicts —
parallel PRs never touch the same file. The extension encodes the bump type so
the release workflow can compute the semver bump without a human classifying
every PR at release time.

> **Failure mode.** A repo without fragment enforcement accumulates unreleased
> changelog entries under `## 0.0.0 (unreleased)` that never become a release
> because the auto-release workflow sees an empty `changelog.d/` and does
> nothing. The downstream version stays dirty (`0.x.dev`) forever, and
> consumers pinning a git SHA never see a clean release version.

### 2. CI enforces the fragment requirement

**Rule:** Every repo's CI runs `towncrier check --compare-with origin/<base>`
as a blocking gate on PRs. A `skip-changelog` label exempts the PR from this
check.

**Rationale:** A fragment directory with no CI gate is a suggestion, not a rule
— contributors forget, and releases silently skip entries. The CI gate makes the
requirement mechanical: a PR that changes user-visible behaviour and lacks a
fragment is blocked until the fragment is added (or the label applied).

> **Failure mode.** Without CI enforcement, a multi-PR release cycle misses
> several PRs' changelog entries because no one noticed the fragments were never
> written. The compiled `CHANGELOG.md` is incomplete, and downstream consumers
> cannot audit what changed between two tagged versions.

### 3. CHANGELOG.md is written only by the release workflow

**Rule:** `CHANGELOG.md` is never edited by hand. The release workflow runs
`towncrier build` to regenerate it from `changelog.d/` fragments, producing
valid [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) output. The one
exception: a programmatic tool that fixes a bug in `CHANGELOG.md` itself
(e.g. an append/insert bug that would otherwise lose history) may write to it
directly, and only for that fix. The tool must not become a general-purpose
changelog writer — `changelog.d/` fragments remain the single source of truth
for content.

**Rationale:** A hand-edited changelog drifts from the fragments: one gets
updated, the other doesn't, and neither is reliable. The release workflow as
sole writer guarantees that `CHANGELOG.md` is always a faithful compilation of
the fragments that were present at release time.

> **Failure mode.** A contributor edits `CHANGELOG.md` directly to add an entry
> during a PR, then forgets the fragment. The next release rebuilds the
> changelog from fragments and silently drops the hand-edited entry — losing
> history with no warning.

### 4. Releases are automated

**Rule:** Every repo wires the shared auto-release workflow from
[robotsix-github-workflows](https://github.com/damien-robotsix/robotsix-github-workflows).
The workflow runs weekly (and on demand). It does nothing when `changelog.d/`
is empty; otherwise it:

- classifies fragments (any `breaking` or `feature` → minor bump, else patch);
- runs `towncrier build` to regenerate `CHANGELOG.md`;
- bumps the version in `pyproject.toml`;
- commits the changes;
- creates and pushes an annotated tag `vX.Y.Z`.

For a library, creating the annotated tag **is** the entire release — there is
no package to publish. For a deployable component, the `v*` tag in turn triggers
the Docker publish workflow (see [Docker build & release](docker-standard.md)).

**Rationale:** A shared workflow keeps every repo on the same release cadence,
deriving the semver bump from fragment types so no human classifies every PR at
release time. Weekly (or on-demand) releases keep the cadence regular — repos
don't drift months without a tag.

> **Failure mode.** A repo without the auto-release workflow never creates a
> release tag. The version stays `0.x.dev` forever — consumers pinning a git SHA
> cannot tell at a glance whether an upgrade is a patch or a breaking change,
> and there is no auditable history of what changed between consumer updates. A
> repo with a hand-rolled release workflow diverges from the fleet's shared
> mechanism; every new contributor must learn per-repo release procedures.

### 5. Versions stay 0.x until 1.0.0 is declared deliberately

**Rule:** Versions stay `0.x` under semver. Bumping to `1.0.0` is a human
decision — it is never automated. Under 0.x there is no compatibility promise,
which matches the stack's pre-release, clean-cutover stance.

**Rationale:** Semver `0.x` means "no stability guarantee" — the public API may
change at any minor bump. This is the correct posture for a stack under active
development where clean cutover is the default migration strategy. Automating a
`1.0.0` bump would make an unintended stability promise.

> **Failure mode.** A repo whose auto-release workflow bumps to `1.0.0`
> automatically signals API stability that does not exist — consumers treat
> minor bumps as safe and are broken by a breaking change that arrived without
> a major-version signal.

### 6. Fragment files are NOT registered in docs/modules.yaml

**Rule:** Do not add `changelog.d/` fragment paths to `docs/modules.yaml`. The
module taxonomy exempts them by default — see
[Module taxonomy scope](module-taxonomy-scope.md).

**Rationale:** towncrier writes one fragment file per pull request, so requiring
registration made every changelog entry a second, unrelated taxonomy edit. This
rule previously mandated exactly that, and its own rationale conceded it was "a
recurring friction point" — documenting the workaround instead of removing the
requirement.

> **Failure mode prevented.** A repo enumerates fragments in the taxonomy
> instead of relying on the exemption. Each PR then needs two edits, the
> enumeration drifts, and the bookkeeping becomes its own ticket class: one such
> ticket sat blocked for a week with a branch proposing 199 explicit fragment
> entries, none of which described a module.

## Reference

- **towncrier:** [https://towncrier.readthedocs.io](https://towncrier.readthedocs.io)
- **Keep a Changelog:** [https://keepachangelog.com/en/1.1.0/](https://keepachangelog.com/en/1.1.0/)
- **hatch-vcs:** [https://hatch.pypa.io/latest/config/metadata](https://hatch.pypa.io/latest/config/metadata)
- **Reference auto-release workflow:** [`robotsix-github-workflows/.github/workflows/auto-release.yml`](https://github.com/damien-robotsix/robotsix-github-workflows/blob/main/.github/workflows/auto-release.yml)
