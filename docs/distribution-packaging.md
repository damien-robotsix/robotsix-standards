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
pinned to a tag or commit SHA. No registry publish step is required.

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
robotsix-llmio = { git = "https://github.com/damien-robotsix/robotsix-llmio.git", rev = "abc123def456" }
```

Or a PEP 508 git URL in `[project] dependencies`:

```text
robotsix-llmio @ git+https://github.com/damien-robotsix/robotsix-llmio@abc123def456
```

**npm consumers** use a git URL:

```text
git+https://github.com/damien-robotsix/robotsix-ui#v0.4.0
```

### 2. Pin to a commit SHA, not a branch

**Rule:** Every first-party git source is pinned to a **commit SHA** (or an
annotated tag, which resolves to a SHA). Branch refs like `main` are disallowed.

**Rationale:** A branch ref drifts silently — a fresh lock (or any lock-refresh)
can pull in unrelated upstream changes with no PR, and a rename or breaking
change upstream then breaks resolution out of nowhere.

> **Failure mode.** A `pyproject.toml` that pins `robotsix-llmio` to `main`
> works today but breaks tomorrow when `main` receives a breaking change the
> consumer never reviewed. The failure lands in CI with no bisectable culprit
> commit in the consumer's repo — the root cause is an upstream change that
> arrived silently.

### 3. Versioning via git tags

**Rule:** Libraries version themselves with release-please, which bumps the
version, generates the changelog, and pushes a `v*` tag — the full mechanism is
documented in [release-please](release-please.md). The version is declared
statically in `pyproject.toml`; deriving it from git tags is disallowed
(release-please rule 3). Consumers pin to those tags (or the underlying SHA).

**Rationale:** Tags give consumers a human-readable version to pin against while
retaining the auditability of a git SHA. Release-please keeps every repo on the
same release mechanism rather than each repo inventing its own.

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

## Enforcement (future)

A standards CI lint that scans changed workflows, `package.json`, and
`pyproject.toml` for public-registry endpoints (`registry.npmjs.org`, public
PyPI) and fails the PR if found. This is tracked as a follow-up ticket.
