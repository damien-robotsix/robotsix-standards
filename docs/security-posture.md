# Security posture

> **Scope: every robotsix repository** — libraries and deployable components
> alike. This is *in addition to* the [repo baseline](repo-baseline.md), which
> every repo follows.

**Content-only repos** — repos that contain only documentation, standards, or
static content (no `src/` directory, no container image) — are exempt from
code-analysis gates (CodeQL, dependency-review, SBOM, CVE audit) and from the
zizmor workflow audit (gate 4b). The zizmor checks (script injection via
`${{ }}`, untrusted `pull_request_target` checkout, overly broad permissions)
are lower-risk for a repo with no deployable artifacts and few, simple
workflows. Content-only repos must still meet SHA-pinning (4a), least-privilege
permissions (4c), secret-protection, and Dependabot gates.

The fleet's security requirements are organizational policy, not repo-specific
technical gaps. They are defined once here, checked at repo onboarding and
on-demand via audit, rather than re-audited weekly per repo by a periodic agent.
Every gate is **self-enforcing** — implemented in CI or GitHub settings, not
dependent on human review or dashboard monitoring — so an audit pass can verify
compliance mechanically.

## Why a dedicated security standard

Before this page, security gates lived scattered across several standards
([repo baseline](repo-baseline.md), [Python practices](python.md),
[Docker build & release](docker-standard.md)) and the shared-workflow
implementation. That made a compliance audit a multi-document hunt. A single,
checklist-shaped standard gives auditors one page to read and gives repo authors
one page to confirm during onboarding.

## The gates

Each gate below is a **required, self-enforcing** control. A repo that ships a
container image additionally meets the **container-image** gates.

### 1. SAST — CodeQL

CodeQL analysis runs on every PR and every push to `main`, via the shared
security workflow from robotsix-github-workflows. Results are uploaded as SARIF
to GitHub Code Scanning.

- **How to verify:** the repo's CI workflow calls the shared CodeQL workflow.
  The Code Scanning tab shows recent analyses for the default branch.
- **Failure prevented:** a vulnerability that a static-analysis rule would
  catch (SQL injection, path traversal, hardcoded credentials) merges and
  ships.
- **Alignment:** [OWASP SAST](https://owasp.org/www-community/Source_Code_Analysis_Tools),
  OpenSSF Scorecard *SAST* check.

### 2. Dependency review — PR gate

The `dependency-review` action gates every PR, failing on `moderate`-severity
or higher findings. It catches a dependency change that introduces a known
vulnerable package before the PR merges.

- **Prerequisite:** the repo's **Dependency graph** must be enabled (a GitHub
  setting, not a workflow — enable Dependabot alerts or automated security
  fixes, which turn it on). Without it the action errors and the gate can
  never go green.
- **How to verify:** the repo's PR CI calls the shared `dependency-review`
  workflow. Opening a PR that adds a vulnerable dependency fails the check.
- **Failure prevented:** a lockfile bump silently pulls in a package with a
  published CVE.
- **Alignment:** OpenSSF Scorecard *Dependency-Update-Tool* and
  *Vulnerabilities* checks.

### 3. Automated dependency updates — Dependabot

Every pin the standards mandate has exactly one named bumper. Dependabot covers
third-party packages, GitHub Actions SHAs, base-image digests, pre-commit hook
versions, and npm packages. `.github/dependabot.yml` declares the required
ecosystems, and the baseline-check gate verifies it is present and complete.
Dependabot PRs auto-merge once required checks pass.

- **How to verify:** `.github/dependabot.yml` exists and covers
  `github-actions` and `pre-commit` in every repo, plus `docker` in
  image-shipping repos and `npm` in repos with `package.json`. The Dependabot
  tab shows recent update PRs.
- **Failure prevented:** a pinned digest (base image, action SHA) rots silently
  — the image stops receiving base-OS security patches, an action runs an
  unmaintained version — with no alert.
- **Alignment:** OpenSSF Scorecard *Dependency-Update-Tool* check.
- **Detail:** [repo baseline — automated dependency updates](repo-baseline.md#automated-dependency-updates).

### 4. Workflow hardening

#### 4a. Actions pinned to commit SHAs

Every third-party action (`uses:` referencing an action outside the
robotsix-github-workflows org) is pinned to its full 40-character commit SHA,
with a trailing `# vX.Y.Z` version comment. A tag or branch ref drifts silently
when the publisher moves it; a SHA is immutable.

- **How to verify:** `grep -r 'uses:' .github/workflows/` produces no
  `@main`, `@master`, `@v1`, or other mutable refs on third-party actions.
  (Reusable workflows from robotsix-github-workflows use the full commit SHA
  of that repo's HEAD.)
- **Failure prevented:** a compromised or broken action release replaces a
  trusted tag, and every CI run pulls the replacement with no review.
- **Alignment:** OpenSSF Scorecard *Pinned-Dependencies* check, SLSA
  *Build L3* requirement.

#### 4b. Workflow linting — actionlint + zizmor

Every workflow file is linted at commit time (`actionlint` in
`.pre-commit-config.yaml`) and at CI time (`actionlint` in the shared CI
workflow). `zizmor` audits workflow definitions for security anti-patterns
(script injection via `${{ }}` in `run:` steps, overly broad `permissions:`,
untrusted checkout of `pull_request_target` events) and gates in CI.

- **How to verify:** `.pre-commit-config.yaml` includes `actionlint`. CI
  calls the shared workflow that runs `zizmor` on `.github/workflows/`.
- **Failure prevented:** a workflow with a shell-injection vector (a
  `${{ github.event.issue.title }}` interpolated into a `run:` script) merges
  and executes attacker-controlled code in the CI context.
- **Alignment:** OpenSSF Scorecard *Token-Permissions* and
  *Dangerous-Workflow* checks.

#### 4c. Least-privilege `permissions:` blocks

Every workflow declares a top-level `permissions:` block that grants only the
permissions that workflow genuinely needs. The default (`write-all` for every
scope) gives a compromised action or workflow step full run of the repo; a
`read-all` top-level default with job-level write grants where needed limits
blast radius to the minimum.

- **The shared caller pattern achieves this automatically** — the reusable
  workflow declares its own `permissions:`, and the caller workflow needs
  only `contents: read` (or `contents: write` when the workflow creates
  releases). A hand-rolled workflow must declare its own `permissions:` block
  and justify every `write` scope.
- **How to verify:** `grep -A5 'permissions:' .github/workflows/*.yml` —
  every file has one, and no file uses `write-all`. `zizmor` flags missing or
  overly broad blocks.
- **Failure prevented:** a compromised third-party action in a workflow with
  `write-all` can push to `main`, exfiltrate secrets, or modify releases with
  no audit trail.
- **Alignment:** OpenSSF Scorecard *Token-Permissions* check, SLSA
  *Build L3* requirement, [GitHub's own guidance](https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication#permissions-for-the-github_token).

### 5. Secret push protection

GitHub secret scanning with **push protection** is enabled on every repo. Push
protection blocks a commit that contains a detected secret *before* it reaches
the remote — the secret never lands in the commit history. This is complemented
by:

- **`detect-secrets` pre-commit hook** with a committed `.secrets.baseline` —
  catches credentials at commit time, before the push.
- **TruffleHog** in the shared security workflow — scans the PR diff and the
  full repo history for secrets that slipped past push protection (e.g. a
  custom pattern GitHub doesn't recognize).

- **How to verify:** the repo's Security / Secret scanning settings show "Push
  protection" as enabled. `.pre-commit-config.yaml` includes `detect-secrets`.
  CI calls the shared TruffleHog workflow.
- **Failure prevented:** a credential (API key, token, private key) is
  committed and pushed; even if the commit is later reverted or force-pushed,
  the secret existed in the history and must be assumed compromised.
- **Alignment:** OpenSSF Scorecard *Token-Permissions* check, OWASP
  *Secret Management*.

### 6. SBOM & vulnerability audit

Every repo produces a machine-readable software bill of materials and runs a
dependency vulnerability audit on every CI run.

- **CycloneDX SBOM** generated and uploaded as a workflow artifact (via the
  shared security workflow). The upload step uses `if: always()` so a failed
  scan never silently drops the artifact.
- **Dependency CVE audit** — `uv audit` (or `pip-audit`) gates in CI, blocking
  on known vulnerabilities in the dependency tree.
- **Container image scan** *(image-shipping repos only)* — Trivy scans the
  built image on every PR and on every publish, blocking on fixable
  CRITICAL/HIGH findings. A `.trivyignore` with commented entries suppresses
  findings that genuinely don't apply. A weekly scheduled rescan of the
  published `:main` image catches CVEs disclosed after the image was built.

- **How to verify:** CI uploads a CycloneDX SBOM artifact. `uv audit` (or
  `pip-audit`) passes in the latest CI run. Image-shipping repos: the PR-scan
  and publish workflows both call the Trivy reusable workflow.
- **Failure prevented:** a dependency with a published, fixable CVE ships in
  production with no one aware.
- **Alignment:** OpenSSF Scorecard *SBOM* and *Vulnerabilities* checks,
  [SLSA *Build L2+*](https://slsa.dev/spec/v1.0/requirements) provenance
  requirement.
- **Detail:** [Docker build & release — CI-time image scan](docker-standard.md#ci-time-image-scan).

## How the gates are delivered

The gates are **not implemented per-repo** — they are delivered through shared
reusable workflows in
[robotsix-github-workflows](https://github.com/damien-robotsix/robotsix-github-workflows).
A repo calls the shared workflow for each gate; adding a new gate to the fleet
is one PR in robotsix-github-workflows, not N PRs across every repo. The
copy-paste caller template for each workflow lives in that repo's README.

The [repo baseline](repo-baseline.md#ci-and-security-gates) lists the standard
gate set; this page adds the *why* for each security-specific gate and the audit
criteria.

## Audit

An audit pass verifies every gate mechanically — no manual review, no
dashboard-watching:

| Gate | Check |
|---|---|
| CodeQL | CI calls shared CodeQL workflow; Code Scanning tab has recent analyses |
| Dependency review | CI calls shared `dependency-review` workflow; Dependency graph enabled |
| Dependabot | `.github/dependabot.yml` covers required ecosystems; recent update PRs |
| SHA-pinned actions | `grep -r 'uses:' .github/workflows/` — no mutable refs on third-party actions |
| Workflow linting | `.pre-commit-config.yaml` includes `actionlint`; CI runs `zizmor` |
| Least-privilege permissions | Every workflow has `permissions:` block; `zizmor` reports clean |
| Secret push protection | Push protection enabled in repo Security settings; `detect-secrets` in pre-commit; CI runs TruffleHog |
| SBOM | CI uploads CycloneDX artifact |
| CVE audit | `uv audit` / `pip-audit` passes in CI |
| Container image scan | Trivy PR-scan and publish workflows present and passing (image-shipping repos only) |
| Vulnerability disclosure | `SECURITY.md` present at repo root with contact method, response-time expectation, and coordinated-disclosure statement |

A repo that fails any gate is non-compliant; the fix is always the same — call
the shared workflow, or enable the GitHub setting.

## See also

- [Repo baseline — CI and security gates](repo-baseline.md#ci-and-security-gates)
- [Repo baseline — automated dependency updates](repo-baseline.md#automated-dependency-updates)
- [Python practices — lint, types, and security lint](python.md#lint-types-and-security-lint)
- [Docker build & release — CI-time image scan](docker-standard.md#ci-time-image-scan)
- [OpenSSF Scorecard](https://securityscorecards.dev/)
- [SLSA Supply-chain Levels for Software Artifacts](https://slsa.dev/)
- [OWASP Top 10 CI/CD Security Risks](https://owasp.org/www-project-top-10-ci-cd-security-risks/)
