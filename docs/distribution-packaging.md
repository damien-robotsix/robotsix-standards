# Distribution & Packaging

> **Scope: every robotsix repository** — libraries and deployable components
> alike. This standard codifies how robotsix-built code is distributed to
> consumers; it is *in addition to* the [repo baseline](repo-baseline.md).

The stack distributes first-party libraries **directly from git** — no package
index, no registry publish step. This is the same model
[`robotsix-llmio`](https://github.com/damien-robotsix/robotsix-llmio) already
uses: release-please bumps the version, generates the changelog, and pushes a
`v*` tag; consumers pull it from GitHub pinned to a commit SHA. Every robotsix
library follows the same path.

## Rules

### 1. Git-based consumption is the preferred path

**Rule:** robotsix libraries are consumed directly from their GitHub repository,
pinned to a full 40-character commit SHA (rule 2), optionally annotated with
the release version in a comment. No registry publish step is required.

**Rationale:** A single-org, first-party set of repositories does not benefit
from the overhead of a package index — publishing accounts, release machinery,
token rotation — when every consumer already has access to the source. Git-based
consumption is simpler, auditable, and removes an entire class of
supply-chain risk (registry-account compromise, dependency confusion).

> **Failure mode.** A library published to a public registry creates a
> supply-chain surface the org does not control: registry credentials must be
> provisioned, rotated, and protected; a compromised token lets an attacker
> publish malicious packages under the org's name. A registry also enables
> dependency confusion — an attacker publishing a same-named package to a public
> registry that a misconfigured resolver picks up instead of the org's internal
> one.

**Python consumers** use a git source in `pyproject.toml`:

```toml
[tool.uv.sources]
robotsix-llmio = { git = "https://github.com/damien-robotsix/robotsix-llmio.git", rev = "0123456789abcdef0123456789abcdef01234567" } # v0.4.0
```

Or a PEP 508 git URL in `[project] dependencies`:

```text
robotsix-llmio @ git+https://github.com/damien-robotsix/robotsix-llmio@0123456789abcdef0123456789abcdef01234567
```

**npm consumers** use a git URL with a SHA fragment (record the version in the
PR or lockfile — `package.json` has no comments):

```text
git+https://github.com/damien-robotsix/robotsix-ui#0123456789abcdef0123456789abcdef01234567
```

### 2. Pin to a commit SHA, not a branch or tag

**Rule:** Every first-party git source is pinned to a **full 40-character
commit SHA**, optionally followed by a version comment (e.g. `# v0.4.0`) where
the manifest format allows comments. Branch refs like `main` and tag refs
(lightweight or annotated) are disallowed as the pin itself.

**Rationale:** A branch ref drifts silently — a fresh lock (or any lock-refresh)
can pull in unrelated upstream changes with no PR, and a rename or breaking
change upstream then breaks resolution out of nowhere. A tag is no better as a
pin: any git tag, annotated or not, can be deleted and re-pushed at a different
commit, so a tag pin does not give the immutability this rule exists for. Only
a commit SHA is content-addressed (cf. OpenSSF Scorecard *Pinned-Dependencies*).

> **Failure mode.** A `pyproject.toml` that pins `robotsix-llmio` to `main`
> works today but breaks tomorrow when `main` receives a breaking change the
> consumer never reviewed. The failure lands in CI with no bisectable culprit
> commit in the consumer's repo — the root cause is an upstream change that
> arrived silently.

### 3. Versioning via git tags

**Rule:** Libraries version themselves with release-please, which bumps the
version, generates the changelog, and pushes a `v*` tag — the full mechanism is
documented in [release-please](release-please.md). The version source is
declared following the [single-source versioning](single-source-versioning.md)
convention; deriving it from git tags is disallowed (release-please rule 3).
Consumers pin to the commit SHA each tag resolves to (rule 2), using the tag
name only as the version comment.

**Rationale:** Tags give consumers a human-readable version to pin against while
retaining the auditability of a git SHA. Release-please keeps every repo on the
same release mechanism rather than each repo inventing its own. The single-source
convention prevents drift between `pyproject.toml` and the package's `__version__`.

> **Failure mode.** A repo without tagged releases forces consumers to pin to
> arbitrary SHAs with no semantic version signal — a consumer cannot tell at a
> glance whether an upgrade is a patch or a breaking change. A repo with
> hand-cut releases diverges from the fleet's shared release workflow, creating
> per-repo release procedures that new contributors must learn.

### 4. Public package indexes are disallowed

**Rule:** Publishing to public registries — `registry.npmjs.org`, public PyPI
(`pypi.org`), or any other public package index — is prohibited. Any exception
requires explicit written approval from the Platform Owner, documenting the
security and legal justification.

**Rationale:** Public registries expose the org to credential-theft risk,
dependency confusion, and accidental publication of internal code. The git-based
model already covers every legitimate consumption pattern without those risks.

> **Failure mode.** A CI workflow that publishes to public npm with an
> `NPM_TOKEN` secret creates a persistent credential target. If that token is
> leaked (log output, compromised runner, misconfigured secret), an attacker can
> publish packages under the org's npm scope — indistinguishable from legitimate
> releases to downstream consumers.

### 5. Internal registry is the only acceptable alternative

**Rule:** If a use case genuinely requires a registry (not just git
consumption), it MUST target an org-internal registry — e.g. GitHub Packages
under the `damien-robotsix` org. CI publish jobs must resolve their registry
environment variable or `publishConfig` to an approved internal domain; a
hard-coded public endpoint is never acceptable. Publish secrets must be
internal-registry credentials only.

**Rationale:** An internal registry keeps packages within the org boundary while
still providing the registry features (version ranges, discovery) that some
toolchains require. GitHub Packages is already available under the org's GitHub
plan and requires no additional infrastructure.

> **Failure mode.** A CI workflow that hard-codes `registry.npmjs.org` in a
> `publishConfig` or registry URL cannot be redirected to an internal registry
> without a code change — and by the time someone notices, packages may already
> be on the public registry.

### 6. Document the distribution method

**Rule:** Each library's README must state how it is distributed and show the
exact pin syntax consumers should use. The default is git-based; if an internal
registry is used, document that instead.

**Rationale:** A consumer reading a library's README should not have to guess or
search workflow files to determine how to depend on it. The pin syntax shown in
the README is the canonical, copy-pasteable instruction.

> **Failure mode.** A library README that omits distribution instructions forces
> every new consumer to discover the pin syntax by reading `pyproject.toml` or
> `package.json` of an existing consumer — a wasteful and error-prone process
> that leads to consumers pinning to `main` or guessing at the syntax.

## Enforcement

Rules 4 and 5 are enforced by a **public-registry check**
(`scripts/check-public-registry.py`, run as the `public-registry-check` job in
`baseline-check.yml`). This section is the check's specification; the script
implements it and does not redefine it.

**Status:** implemented, warning-first (see *Rollout* below). Reviewers still
check changes to workflows, `package.json`, `.npmrc` and `pyproject.toml`
against the patterns below during code review (see the
*Distribution / registry* row in the
[security posture audit table](security-posture.md#audit)).

**Scope.** The check scans every file matching `.github/workflows/*.yml` /
`*.yaml`, `package.json`, `.npmrc`, and `pyproject.toml` on each PR and push to
`main` — at minimum every changed file of that kind. The job runs the script
with no arguments, scanning every in-scope file in the repo (a superset of the
changed files); given file paths, the script scans only those.

**It flags:**

| Pattern | Where | Why |
|---|---|---|
| `registry.npmjs.org` | workflows, `package.json` `publishConfig.registry`, `.npmrc` | Public npm publish target (rule 4) |
| `upload.pypi.org`, `pypi.org/legacy`, `test.pypi.org` | workflows, `pyproject.toml` (`[[tool.uv.index]]` `publish-url`) | Public PyPI upload endpoint (rule 4) |
| `npm publish` with no `--registry` pointing at an approved internal domain | workflows | Falls back to the public default registry (rule 5) |
| `twine upload` / `uv publish` with no `--repository-url` / `--publish-url` pointing at an approved internal domain | workflows | Falls back to public PyPI (rule 5) |
| `pypa/gh-action-pypi-publish` | workflows | Action whose default target is public PyPI (rule 4) |
| `secrets.NPM_TOKEN`, `secrets.PYPI_TOKEN`, `secrets.PYPI_API_TOKEN` | workflows | Public-registry credentials in CI (rules 4–5) |

The approved internal domain is `npm.pkg.github.com` (GitHub Packages under
the `damien-robotsix` org); any other domain needs Platform Owner approval and is added to the check's
allow-list in the same change. A Platform Owner–approved exception (rule 4) is
recorded as a per-repo allow-list entry naming the approval, never as an inline
suppression: one line per exception in `.public-registry-allowlist` at the repo
root, `<path> <rule-id> <approval reference>`; an entry without the approval
reference is ignored.

**Rollout.** The check is **warning-first**: it emits `::warning::`
annotations and does not fail the build, so existing repos can converge. It
flips to **blocking** (exit 1) on **2027-01-31**; from that date a match fails
CI.

> **Failure mode.** Without a mechanical gate, rules 4–5 are an aspiration: a
> PR that adds `npm publish` with an `NPM_TOKEN` secret, or a `uv publish` to
> public PyPI, merges on review alone — and the first sign of the breach is the
> package appearing on the public index under the org's name, after which it
> cannot be fully retracted (mirrors and caches keep it). Alignment:
> [SLSA v1.0 Build track](https://slsa.dev/spec/v1.0/levels) (controlled
> distribution), [OWASP Top 10:2025](https://owasp.org/Top10/2025/)
> [A03:2025 Software Supply Chain Failures](https://owasp.org/Top10/2025/A03_2025-Software_Supply_Chain_Failures/)
> (dependency confusion, credential-theft publishing) and
> [A08:2025 Software or Data Integrity Failures](https://owasp.org/Top10/2025/A08_2025-Software_or_Data_Integrity_Failures/).
