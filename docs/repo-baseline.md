# Repo baseline

> **Scope: every robotsix repository** — libraries and deployable components
> alike, in any language. Language-specific practices live on their own page
> ([Python](python.md)); deployable components additionally follow the
> [component standard](component-standard.md).

Conventions every repository shares, so tooling, CI, and contributor workflow
are the same everywhere.

## Distribution tier is explicit

A repo is **either** a library **or** a deployable component — decide and be
consistent. The tier determines which standards apply and how the package is
distributed.

| Tier | What it is | Ships as | How consumers/operators get it |
|---|---|---|---|
| **Library** | Imported by other packages; no runnable service | Source in its git repository | Depend on it from git — no package index |
| **Deployable component** | Ships a runnable service | Container image | Run the container, or install from a checkout |

(The one exception is the deployment system itself — see the
[bootstrap tier](deployment-system.md).) Packaging specifics per language:
[Python](python.md).

### No package index — consume libraries from git

**The stack does not publish to any package index (no PyPI, no npm, etc.).** It
is a single, first-party set of repositories; publishing and index accounts add
release machinery no one asked for. First-party libraries are consumed **directly
from their git repositories**, using the language's native git-dependency
support — for Python, uv's `[tool.uv.sources]`.

Repos therefore carry **no index-publish workflow** (no `pypi-publish`,
release-please, or index token). A library that later needs genuine public
distribution can add publishing back deliberately — but that is the exception,
not the default. (Repos *do* release — versions, tags, a compiled changelog —
via the shared auto-release workflow; see
[changelog & releases](#changelog-releases). A release publishes nothing to
any package index.)

#### Pin to a commit SHA, not a branch

Every first-party git source is pinned to a **commit SHA**, never a branch ref
like `main`. A branch ref drifts silently — a fresh `uv lock` (or any
lock-refresh) can pull in unrelated upstream changes with no PR, and a rename or
breaking change upstream then breaks resolution out of nowhere.

```toml
[tool.uv.sources]
# Pinned — reproducible, updated only via a reviewed bump.
robotsix-config = { git = "https://github.com/damien-robotsix/robotsix-config.git", rev = "6f2a1c9e…" }
# NOT this — a moving target:
# robotsix-config = { git = "…", rev = "main" }
```

#### Auto-bump workflow keeps pins current

Because pins are SHAs, they need an automated bump so they don't rot. A
**scheduled pin-bump workflow** walks each repo's `[tool.uv.sources]`, resolves
the latest commit on each dependency's default branch, and opens a PR that
updates the `rev` and re-locks — updates land **deliberately, through green CI
and review**, never silently. A **coherent-set resolver** keeps a dependency
that several repos share pinned to the *same* SHA across the stack, so the fleet
doesn't split-brain on transitive versions. (Third-party deps use the usual
Dependabot/Renovate auto-merge path; this workflow is for the first-party git
sources.)

## Language practices

- **[Python](python.md)** — uv, hatchling, `requires-python` policy, console
  scripts, lint/type/security gates, test layout, pre-commit hooks.
- **[JavaScript](javascript.md)** — vanilla frontend JS as static assets,
  lockfile discipline, vitest coverage floor, eslint/stylelint.

New languages get their own page here before the first repo lands
(`robotsix-mill-ros2` predates this rule; its conventions are being extracted
into the **[ROS 2 practices](ros2.md)** page — started solid, adapted as it
goes). Generic
language conventions live **only** on these pages — agent systems (the mill's
implement/refine/review agents) point here rather than carrying their own
copies, and repo AGENT.mds link rather than restate.

## Changelog & releases

One mechanism, fleet-wide: **[towncrier](https://towncrier.readthedocs.io)
newsfragments, compiled by the shared auto-release workflow.**

- **Every PR adds a newsfragment** in `changelog.d/` (`.breaking.md`,
  `.feature.md`, `.bugfix.md`, `.misc.md`); CI enforces it via `towncrier
  check --compare-with origin/<base>` (a `skip-changelog` PR label exempts
  changes with nothing to record). Fragments are per-PR files, so parallel
  PRs never conflict on the changelog.
- **`CHANGELOG.md` is written only by the release workflow** — never by hand.
  It stays in [Keep a Changelog](https://keepachangelog.com) form.
- **Releases are automated.** The shared auto-release workflow (in
  [robotsix-github-workflows](https://github.com/damien-robotsix/robotsix-github-workflows);
  runs weekly plus on demand) does nothing when `changelog.d/` is empty;
  otherwise it derives the bump from the fragment types (any `breaking` or
  `feature` → minor, else patch), runs `towncrier build`, bumps the version in
  `pyproject.toml`, commits, and tags `v0.X.Y`. For deployable components the
  `v*` tag in turn publishes the `X.Y.Z` image tag (see
  [Docker build & release](docker-standard.md)).
- **Versions stay `0.x`** until a repo deliberately declares `1.0.0` — that is
  a human statement about stability, never automated. Under semver 0.x there
  is no compatibility promise, which matches the stack's pre-release,
  clean-cutover stance.

## Repo hygiene

- **Module registration** *(mill-managed repos — those with a board; a repo
  nothing consumes the registry from, e.g. a docs-only repo, is exempt)*.
  `docs/modules.yaml` is the repo's machine-readable
  module map, consumed by
  [robotsix-modules](https://github.com/damien-robotsix/robotsix-modules):
  the CI drift gate, the mill's module-scoped agent workflows, and agents
  navigating the repo (read the map first instead of exploring). Each module
  declares an **id**, a required **one-to-two-line description** (what it
  does, when to look there — the part that beats `ls`), and root globs that
  default to the standard layout (`src/<pkg>/<module>/**`,
  `tests/<module>/**`, `docs/<module>/**`) — a conventional module needs no
  explicit paths; only out-of-convention files are listed. The drift check
  fails CI when a file matches **no** module's globs, so nothing is invisible
  to module-scoped tooling.
- **README skeleton.** Five required elements, prose not ceremony: what the
  repo is (one paragraph — the same one-liner the [fleet page](fleet.md)
  carries; they must agree), its tier (linking the standards), a quickstart
  (the 3-5 commands that actually work), the docs-site link, and the
  standards link. Anything deeper belongs in the docs site or AGENT.md.
- **Truthful docs.** README / AGENT.md describe what the code actually does;
  don't let removed commands, renamed paths, or old version claims linger.
- **Point at the standards.** Every repo's `README.md` and `AGENT.md` link to
  [`robotsix-standards`](https://github.com/damien-robotsix/robotsix-standards)
  so contributors find the shared conventions from any repo.
- **License.** MIT, as a `LICENSE` file at the repo root.

## AGENT.md

Every repo ships an `AGENT.md`: the accumulated, repo-specific working
knowledge for agents and contributors.

- **Skeleton:** an opening line linking robotsix-standards, one paragraph
  stating what the repo is and its tier (library / deployable component /
  bootstrap), then rule sections.
- **Format:** each entry is a **Rule** (imperative, checkable) followed by its
  **Rationale** — the failure it prevents, with the incident/PR/ticket
  reference when one exists. A rule whose failure mode can't be stated
  probably isn't one.
- **Scope: repo-specific knowledge only.** Anything true fleet-wide belongs in
  robotsix-standards, linked rather than restated — a copied rule silently
  drifts the moment the standard changes. The test: *would this rule apply in
  a sibling repo?* Then it goes upstream.
- Truthfulness applies as to the README: prune rules whose code is gone.

## CI and security gates

**The standards hold the rules; the gates live in
[robotsix-github-workflows](https://github.com/damien-robotsix/robotsix-github-workflows).**
Repos **call the shared reusable workflows** for the standard gate set — this
is a rule, not a preference: a gate added to the fleet (a new check, a policy
change) must reach every repo without N re-implementations, and a hand-rolled
copy silently misses every improvement after the day it was written. A
hand-rolled gate is the exception and carries a comment justifying it, same
as a lint suppression. The copy-paste caller template for each workflow lives
in the robotsix-github-workflows README — standards pages don't embed
workflow YAML, so templates version with the workflows they call. Pin every
third-party action to a commit SHA (with a `# vX.Y.Z` comment). The standard
gate set:

- **Lint & types:** the language page's linters and type checker, as blocking
  gates ([Python](python.md): ruff, mypy strict, deptry).
- **Tests & coverage:** the test suite with **one fleet-wide coverage floor
  (80%)**, enforced by the shared workflow so it lives in exactly one place.
  No per-repo thresholds; the floor is raised fleet-wide, deliberately, when
  every repo already clears the new value (see [Tests](python.md#tests)).
- **Docs:** a strict docs build (`mkdocs build --strict`) when the repo
  publishes a docs site.
- **Security:** CodeQL (SAST), GitHub secret scanning + push protection
  (complemented by TruffleHog for PR-diff and full-repo scans in the shared
  security workflow), a dependency CVE audit (`pip-audit` in the security
  workflow, `uv audit` in CI), `dependency-review` on PRs (`fail-on-severity:
  moderate`), and a CycloneDX SBOM generated and uploaded as a workflow
  artifact.
- **Container image:** repos that ship an image also scan it in CI — see
  [Docker build & release](docker-standard.md).
- **Baseline conformance:** the shared baseline-check workflow verifies the
  mechanical rules of this page — `AGENT.md` present and linking the
  standards, `dependabot.yml` covering the
  [required ecosystems](#automated-dependency-updates).
- **Required-artifact uploads use `if: always()`.** A step that uploads an
  artifact the gate depends on (SBOM, coverage report) must run even when an
  earlier step failed — otherwise the failure skips the upload and the
  `if-no-files-found: error` backstop never fires, silently dropping the
  artifact (a real incident in robotsix-llmio). The CycloneDX SBOM generated
  by `python-security.yml` follows this pattern: the upload step uses
  `if: always()` and `if-no-files-found: error`, so a failed scan step never
  silently drops the SBOM artifact.

**Completeness principle:** a gate in this list exists as (part of) a shared
reusable workflow — if it can't be called from robotsix-github-workflows, it
isn't a standard gate yet. Gates adopted à la carte drift à la carte: before
this rule, CodeQL ran in 4 of 13 repos and the weekly image rescan in 3 of 8,
each a hand-copied workflow file.

## Branch protection

`main` is protected identically in every repo — several standards are
silently vacuous without it (auto-merge merges instantly, direct pushes
bypass every gate, the changelog check never runs):

- **PRs only** — no direct pushes to `main`.
- **Required status checks** — the shared-workflow gates above.
- **Squash merge**, force-push disabled.

GitHub settings can't live in the repo, so uniformity comes from the
idempotent apply-script in robotsix-github-workflows (`gh api` loop over the
fleet) — run it when a repo is created or the required-check set changes.

## Starting a new repo

New repos start from the language's template repository —
**`robotsix-template-python`** (a GitHub template) carries the full baseline
pre-assembled: pyproject skeleton, `dependabot.yml`, the standard pre-commit
set, shared-workflow callers, towncrier config, `AGENT.md` skeleton,
`docs/modules.yaml`, LICENSE — plus a component overlay (Dockerfile, the two
composes, `config/` scaffolding) for deployable services. The template is a
fleet member like any other: the baseline-check gates it, dependabot bumps
it, standards changes land there as tickets — so it cannot rot. Templates
are per-language, parallel to the language pages: a new language earns a
standards page *and* a template before its first repo lands.

## Retiring a repo

The mirror image, exercised by the broker decommission (2026-07-03):

1. **Deprecate first.** File removal tickets in every consumer — find them
   by sweeping the fleet's `[tool.uv.sources]` for the repo. Removals are
   clean cutover, per house rule.
2. **Gate the archive on the removals** (the mill's `unblocks` mechanism).
   **Never privatize or archive while any git pin still points at the
   repo** — consumers resolve first-party deps from git, so flipping
   visibility first breaks every dependent's CI at once.
3. **Then retire:** visibility → private, *then* archive (order matters —
   archived repos can't be edited); remove the mill board registration, any
   deployment, and the [fleet page](fleet.md) row.
4. **Recovery is cheap:** unarchive — nothing is deleted.

> **Dependency-review needs the Dependency graph enabled.** The
> `dependency-review` action errors with *"Dependency review is not supported
> on this repository"* until the repo's **Dependency graph** is turned on
> (enable Dependabot alerts / automated security fixes, which turn it on).
> Enable it once per repo — a GitHub setting no workflow can automate — or the
> gate can never go green.

## Automated dependency updates

Every pin the standards mandate has exactly one named bumper — a pin without a
bumper is a slow leak (a frozen base-image digest, for instance, stops
receiving security patches until someone moves it):

| Pin | Bumper |
|---|---|
| First-party `[tool.uv.sources]` SHAs | the scheduled pin-bump workflow (above) |
| Third-party packages (`uv.lock`) | Dependabot `uv` ecosystem |
| GitHub Actions SHAs | Dependabot `github-actions` ecosystem |
| Base-image digests + the uv `COPY --from` pin | Dependabot `docker` ecosystem |
| Pre-commit hook versions | Dependabot `pre-commit` ecosystem |
| npm packages (`package-lock.json`) | Dependabot `npm` ecosystem |

`.github/dependabot.yml` therefore covers **`uv`, `github-actions`, and
`pre-commit`** in every repo, plus **`docker`** in repos that ship an image
and **`npm`** in repos with a `package.json`
(GitHub only reads the file per-repo — it cannot be centralized, so the
baseline-check gate verifies its contents instead). Dependabot PRs auto-merge
once required checks pass, via the shared `dependabot-auto-merge.yml` caller
from robotsix-github-workflows.
