# Security posture

> **Scope: every robotsix repository** — libraries and deployable components
> alike. This is *in addition to* the [repo baseline](repo-baseline.md), which
> every repo follows.

**Content-only repos** — repos that contain only documentation, standards, or
static content (no `src/` directory, no container image) — are exempt from
code-analysis gates (Semgrep, dependency-review, SBOM, CVE audit) and from the
zizmor workflow audit (gate 4b). The zizmor checks (script injection via
`${{ }}`, untrusted `pull_request_target` checkout, overly broad permissions)
are lower-risk for a repo with no deployable artifacts and few, simple
workflows. Content-only repos must still meet SHA-pinning (4a), least-privilege
permissions (4c), push-protection + detect-secrets (the commit-time and
push-time parts of gate 5), and Dependabot gates. The TruffleHog full-history
scan is exempt — a docs-only repo with no deployable artifacts and few
contributors has minimal secret-exposure surface beyond what push protection
and detect-secrets already catch.

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

## Tooling policy: open-source preferred

The fleet actively prefers open-source security tooling over proprietary or
licensed solutions. This is an intentional policy choice, not a default or
cost-saving measure:

- **Auditability.** Open-source tools ship their detection rules in the clear.
  A false positive can be traced to a specific rule and suppressed or fixed; a
  missed pattern can be contributed upstream. Proprietary scanners are a black
  box — the fleet depends on the vendor's rule-writing priorities and
  release cadence, with no recourse.
- **No license keys in CI.** A licensed tool requires a license key provisioned
  in every repo's secrets, rotated on expiry, and gated on billing. Every key
  is a secret that must itself be protected — a self-referential failure mode.
  An OSS tool needs no key and has no expiry.
- **Reproducibility.** A contributor can run the same scan locally (pre-commit
  or a one-shot CLI invocation) that CI runs — same version, same rules, same
  result. Licensed scanners that gate features behind a key break this: CI sees
  rules the developer cannot reproduce, so a CI-only failure is a mystery.
- **Fleet consistency.** An OSS scanner rolls out by updating one shared
  workflow and one pre-commit config. A licensed scanner gatekeeps fleet-wide
  rollout behind procurement, license provisioning, and per-repo secret
  management — the opposite of the self-enforcing principle.

This policy applies to every security gate: SAST (Semgrep, itself open-source),
secret scanning (detect-secrets + TruffleHog, see gate 5), dependency auditing
(`uv audit`, `pip-audit`), and container image scanning (Trivy). A future gate
that genuinely requires a proprietary tool must justify the exception in the
standard that introduces it — stating what an OSS alternative was evaluated
and why it was insufficient.

## OpenSSF Scorecard — not a fleet gate

robotsix repos **do not** run
[OpenSSF Scorecard](https://securityscorecards.dev/) and must not add
`.github/workflows/scorecard.yml` to a repo or to the repo-scaffold
templates (operator decision, 2026-08-13). The supply-chain properties
Scorecard would score are gated instead by
[zizmor](github-actions-security.md) (workflow security),
[actionlint](security-posture.md#4b-workflow-linting-actionlint-zizmor)
(workflow syntax), the
[workflow-permissions audit](security-posture.md#4c-least-privilege-permissions-blocks),
Dependabot/`uv audit` (dependency CVEs), and Trivy (container CVEs). See
[OpenSSF Scorecard (not used)](scorecard.md) for the full rationale.

## The gates

Each gate below is a **required, self-enforcing** control. A repo that ships a
container image additionally meets the **container-image** gates.

### 1. SAST — Semgrep

Semgrep analysis runs on every PR and every push to `main`, via the shared
security workflow from robotsix-github-workflows. Findings are published as a
workflow artifact and surfaced through the fleet dashboard — there is no
dependency on GitHub Code Scanning or the GitHub Security tab.

Bandit (Python-specific SAST) runs as a complementary layer via the shared
`python-ci.yml` workflow in every Python repo — see
[Python practices](python.md#lint-types-and-security-lint).

- **How to verify:** the repo's CI workflow calls the shared Semgrep workflow.
  The latest CI run on the default branch uploads a Semgrep findings artifact.
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

### 3. Automated dependency updates — Renovate + Dependabot

Every pin the standards mandate has exactly one named bumper. Renovate covers
Python/uv lockfiles; Dependabot covers GitHub Actions SHAs, base-image digests,
pre-commit hook versions, and npm packages. `renovate.json` declares the `uv`
manager in every Python repo, and `.github/dependabot.yml` declares the
remaining ecosystems; the baseline-check gate verifies both are present and
complete. Dependabot and Renovate PRs auto-merge once required checks pass.

- **How to verify:** `renovate.json` exists in every Python repo (covering the
  `uv` manager); `.github/dependabot.yml` exists and covers `github-actions`
  and `pre-commit` in every repo, plus `npm` in repos with `package.json` and
  `docker` in image-shipping repos. The Dependabot and Renovate dashboards
  show recent update PRs.
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
by an open-source, layered secret-scanning stack:

- **`detect-secrets` pre-commit hook** ([Yelp/detect-secrets](https://github.com/Yelp/detect-secrets),
  Apache-2.0) with a committed `.secrets.baseline` — catches credentials at
  commit time, before the push.
- **TruffleHog** ([trufflesecurity/trufflehog](https://github.com/trufflesecurity/trufflehog),
  AGPL-3.0) in the shared security workflow — scans the PR diff and the full
  repo history for secrets that slipped past push protection (e.g. a custom
  pattern GitHub doesn't recognize, or a secret committed before push
  protection was enabled).

#### Why this stack

The fleet evaluated three open-source secret scanners for fleet-wide adoption:

| Scanner | License | Strengths | Why chosen / not |
|---|---|---|---|
| **detect-secrets** | Apache-2.0 | Pre-commit native; plugin architecture; committed baseline suppresses known false positives; mature (Yelp, 2017–present). | **Chosen** for the pre-commit layer. No license key needed; the baseline file is version-controlled and reviewable. |
| **TruffleHog** | AGPL-3.0 | Full git-history scanning; verifies detected credentials against live APIs; high-entropy string detection; PR-diff mode for CI. | **Chosen** for the CI layer. Complements detect-secrets by catching secrets that predate the pre-commit hook or bypass it. |
| **Gitleaks CLI** | MIT | Fast; simple rule set; single-binary deployment. | **Not chosen.** The CLI itself is MIT and unencumbered, but the fleet's evaluation (ticket 1740) found that the features needed for CI integration (action, enterprise rule packs) require a license key — the very pattern this standard rejects (see [tooling policy](#tooling-policy-open-source-preferred)). The unlicensed CLI alone cannot match the combined coverage of detect-secrets + TruffleHog. |

**Rationale for two tools over one.** A single scanner cannot cover both the
pre-commit and CI surfaces equally well:

- A pre-commit hook must be fast (sub-second on changed files) and must not
  require network access. TruffleHog's live credential verification is
  powerful in CI but too slow and network-dependent for a pre-commit hook.
- A CI scanner must cover the full git history — commits that predate the
  pre-commit hook, force-push artifacts, merge-commit blobs.
  `detect-secrets` only sees the working tree at commit time; it cannot
  retroactively scan history.

The two tools are not redundant — they are complementary layers in a defense
that spans commit-time, push-time, and CI-time.

#### No licensed secret scanner

No standard mandates or recommends a licensed or proprietary secret-scanning
tool. The Gitleaks Enterprise/licensed path was evaluated and explicitly
rejected (ticket 1740) — provisioning a `GITLEAKS_LICENSE` key across the
fleet would violate the [open-source preferred policy](#tooling-policy-open-source-preferred)
and add a self-referential secret-management burden. The OSS stack above
(detect-secrets + TruffleHog) is the single fleet-wide secret-scanning path.

- **How to verify:** the repo's Security / Secret scanning settings show "Push
  protection" as enabled. `.pre-commit-config.yaml` includes `detect-secrets`.
  CI calls the shared TruffleHog workflow.
- **Failure prevented:** a credential (API key, token, private key) is
  committed and pushed; even if the commit is later reverted or force-pushed,
  the secret existed in the history and must be assumed compromised.
- **Alignment:** OpenSSF Scorecard *Token-Permissions* check, OWASP
  *Secret Management*.

#### Credential and secret files are never tracked

Secret scanning (above) catches *detected* secrets — API keys, tokens,
high-entropy strings — but not credential **files**: an `.htpasswd` holds a
bcrypt hash (no cleartext pattern for a scanner to match), a `wp-config.php`
may template its credentials, and private-key files only match when the
scanner knows the format. The defense for these is a deny list, not a
detector.

**Every repo's `.gitignore` covers, at minimum:**

- `.htpasswd`
- `.env` and `.env.*`
- `wp-config.php` and `wp-config*.php`
- `*.pem`, `*.key`, and other private-key files
- `*secret*`
- `*.p12`

Patterns are scoped per repo; a repo that deliberately tracks a file matched
by one of them (e.g. a public certificate, not a private key) adds a negating
exception with a comment stating why.

**Out-of-band secret transport.** A secret that must exist on a deploy target
(an `.htpasswd` protecting an admin area, a `wp-config.php` with production
credentials) is pushed **out-of-band**, never via the committed tree: read the
value from a CI/CD secret (`${{ secrets.* }}`) and write it to the server with
a dedicated transport. The transport must not use a delete-ordering that
would wipe the file — e.g. `lftp mirror --delete` (or `rsync --delete`) over a
tree that does not contain the secret deletes it on the target — use a
non-delete invocation or a dedicated file transfer instead.

- **How to verify:** `git ls-files` lists no credential or secret file;
  `.gitignore` covers the deny list above; the deploy workflow reads secrets
  from `${{ secrets.* }}` and writes them via a transport with no
  delete-ordering.
- **Failure prevented:** a credential file is committed and tracked. Once in
  history it survives every later removal — deleting the file (or adding the
  `.gitignore` entry later) does not purge it from past commits, and the only
  remediation is a full history rewrite (the robotsix-mill `wp-config.php`
  incident). A deploy sync with a delete-ordering silently deletes a
  server-side secret absent from the committed tree, taking the protected
  service down (the robotsix-mill `lftp mirror --delete` trap).
- **Alignment:** OWASP *Secret Management*, OpenSSF Scorecard
  *Token-Permissions* check.

### 6. SBOM & vulnerability audit

Every repo produces a machine-readable software bill of materials and runs a
dependency vulnerability audit on every CI run.

- **CycloneDX SBOM** generated and uploaded as a workflow artifact on every
  CI run (via the shared security workflow). The SBOM MUST be a
  standards-conformant CycloneDX document generated **natively by `uv export`
  from the lockfile**:

  ```bash
  uv export --frozen --format cyclonedx1.5 --no-emit-project -o sbom.cdx.json
  ```

  `uv export` reads `uv.lock` and emits the component inventory in
  CycloneDX 1.5 JSON (see the
  [uv docs](https://docs.astral.sh/uv/concepts/projects/export/#cyclonedx-sbom-format));
  no extra tool (cyclonedx-py, syft, trivy) is required. The upload step uses
  `if: always()` so a failed scan never silently drops the artifact.
- **`uv audit` output is not an SBOM.** `uv audit --output-format json`
  (or `pip-audit`) emits a vulnerability/advisory report — OSV matches,
  severities, affected/fixed ranges — that contains no component inventory.
  It is **not** a Software Bill of Materials and MUST NOT be uploaded under
  the `sbom` artifact name or fed to SBOM consumers. The CVE audit report and
  the CycloneDX SBOM are distinct artifacts with distinct names (e.g.
  `audit-report.json` for the audit output, `sbom.cdx.json` for the SBOM);
  conflating them under the `sbom` name silently breaks SBOM-dependent
  tooling and compliance workflows.
- **Release asset.** The auto-release workflow MUST attach the CycloneDX SBOM
  as a GitHub Release asset (filename `sbom.cyclonedx.json`, per the
  [OSSF "SBOM Everywhere" naming convention](https://github.com/ossf/scorecard/blob/main/docs/checks.md#sbom)).
  A Sigstore attestation via `actions/attest` on the SBOM is recommended but
  optional. The release-time asset is what raises the Scorecard *SBOM* check
  from 5/10 (SBOM present somewhere in the pipeline) to 10/10 (SBOM published
  as a release artifact).
- **Dependency CVE audit** — `uv audit` (or `pip-audit`) gates in CI, blocking
  on known vulnerabilities in the dependency tree.
- **Container image scan** *(image-shipping repos only)* — Trivy scans the
  built image on every PR and on every publish, blocking on fixable
  CRITICAL/HIGH findings. A `.trivyignore` with commented entries suppresses
  findings that genuinely don't apply. A weekly scheduled rescan of the
  published `:main` image catches CVEs disclosed after the image was built.

- **How to verify:** CI uploads a CycloneDX SBOM artifact (parseable
  CycloneDX JSON generated by `uv export`, not `uv audit` output) and,
  where the audit output is uploaded, a separately named vulnerability audit
  artifact (`audit-report.json`). The latest GitHub Release includes
  `sbom.cyclonedx.json` as an asset (and optionally a Sigstore attestation
  bundle). `uv audit` (or `pip-audit`) passes in the latest CI run.
  Image-shipping repos: the PR-scan and publish workflows both call the Trivy
  reusable workflow.
- **Failure prevented:** a dependency with a published, fixable CVE ships in
  production with no one aware. An SBOM that exists only as a CI artifact is
  invisible to downstream consumers and supply-chain auditors — the release
  asset makes it discoverable. Uploading `uv audit` output as the SBOM
  artifact leaves SBOM tooling (Dependency-Track, GitHub dependency graph,
  grype, VEX pipelines) with no parseable component inventory — the artifact
  fails schema validation or is silently ignored, while no real SBOM is ever
  produced.
- **Alignment:** OpenSSF Scorecard *SBOM* (10/10 with release asset) and
  *Vulnerabilities* checks,
  [SLSA *Build L2+*](https://slsa.dev/spec/v1.2/requirements) provenance
  requirement.
- **Detail:** [Docker build & release — CI-time image scan](docker-standard.md#ci-time-image-scan).

## SLSA Source Track

[SLSA v1.2](https://slsa.dev/spec/v1.2/) introduces a **Source Track**
(Source L1–L4) alongside the existing Build Track. The fleet's posture against
each Source level:

- **Source L1 (version-controlled source):** met — all source lives in GitHub,
  and every dependency is referenced by an immutable commit SHA.
- **Source L2 (signed source provenance):** gap — releases do not yet produce
  signed source provenance attestations. Adoption is deferred pending tooling
  maturity and upstream ecosystem support.
- **Source L3 (continuous enforcement of branch protection):** met — branch
  protection with `include_admins: true` enforces required status checks on
  every commit to `main`. No commit merges without passing CI.
- **Source L4 (two-person review):** deferred — SLSA Source L4 requires an
  informed two-person review on every change. The fleet's branch-protection
  rule mandates one required approving review. Requiring two reviewers on
  every PR is impractical for a small team and is a deliberate, documented
  tradeoff.

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
| Semgrep* | CI calls shared Semgrep workflow; latest CI run uploads Semgrep findings artifact |
| Dependency review* | CI calls shared `dependency-review` workflow; Dependency graph enabled |
| Dependabot + Renovate | `.github/dependabot.yml` covers non-uv ecosystems; `renovate.json` present in Python repos; recent update PRs |
| SHA-pinned actions | `grep -r 'uses:' .github/workflows/` — no mutable refs on third-party actions |
| Workflow linting | `.pre-commit-config.yaml` includes `actionlint`; CI runs `zizmor` (content-only repos exempt from `zizmor`) |
| Least-privilege permissions | Every workflow has `permissions:` block; `zizmor` reports clean |
| Secret push protection | Push protection enabled in repo Security settings; `detect-secrets` in pre-commit; CI runs TruffleHog (content-only repos exempt from TruffleHog) |
| SBOM* | CI uploads CycloneDX artifact |
| CVE audit* | `uv audit` / `pip-audit` passes in CI |
| Container image scan | Trivy PR-scan and publish workflows present and passing (image-shipping repos only) |
| Vulnerability disclosure | `SECURITY.md` present at repo root with contact method, response-time expectation, and coordinated-disclosure statement |

*Content-only repos are exempt per the preamble above.

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
