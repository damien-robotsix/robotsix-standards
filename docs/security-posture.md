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
permissions (4c) — both enforced by the
[workflow-permissions audit](#workflow-permissions-audit) — plus
push-protection + detect-secrets (the commit-time and push-time parts of gate
5), and Dependabot gates. The TruffleHog full-history
scan is exempt — a docs-only repo with no deployable artifacts and few
contributors has minimal secret-exposure surface beyond what push protection
and detect-secrets already catch.

The fleet's security requirements are organizational policy, not repo-specific
technical gaps. They are defined once here, checked at repo onboarding and
on-demand via audit, rather than re-audited weekly per repo by a periodic agent.
Every gate is **self-enforcing** — implemented in CI or GitHub settings, not
dependent on human review or dashboard monitoring — so an audit pass can verify
compliance mechanically.

OWASP Top 10 citations across the standards refer to the
[2025 edition](https://owasp.org/Top10/2025/) (e.g. `A09:2025`); OWASP LLM
and Agentic citations refer to the 2026 editions.

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
[workflow-permissions audit](security-posture.md#workflow-permissions-audit),
Dependabot/`uv audit` (dependency CVEs), and Trivy (container CVEs). The
Scorecard *Security-Policy* check is replaced by the
[baseline gate's `SECURITY.md` check](repo-baseline.md#ci-and-security-gates),
which is **fail-closed** — it fails CI (exit 1) when a repo lacks a root
`SECURITY.md` carrying the three required elements (see the
[Vulnerability disclosure row](#audit) below). See
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
- **Alignment:** OpenSSF Scorecard *Vulnerabilities* check,
  [OpenSSF OSPS Baseline](https://baseline.openssf.org/) *OSPS-VM-05*
  (dependency vulnerability management). Scorecard *Dependency-Update-Tool*
  measures only the automated update tooling of gate 3, not a PR-time block.

### 3. Automated dependency updates — Renovate + Dependabot

Every pin the standards mandate has exactly one named bumper. Renovate covers
Python/uv lockfiles; Dependabot covers GitHub Actions SHAs, base-image and
uv-image digests, pre-commit hook versions, and npm packages. Dependabot only
sees an image pin written literally on a `FROM` line — a digest held in an
`ARG` or an image pulled inline with `COPY --from=<image>` is never bumped, so
the Dockerfile must use the
[Dependabot-readable shape](docker-standard.md#build-the-dockerfile) (literal
`@sha256` on every `FROM`, uv as a digest-pinned named stage). `renovate.json` declares the `uv`
manager in every Python repo, and `.github/dependabot.yml` declares the
remaining ecosystems; the baseline-check gate verifies both are present and
complete. Dependabot and Renovate PRs auto-merge once required checks pass —
restricted to `minor`/`patch` updates, with the `docker` and `pre-commit`
ecosystems excluded from auto-merge (those PRs always require human review);
see [Dependabot auto-merge](dependabot-auto-merge.md). An auto-merged update
must also wait out a **3-day release-age cooldown** (Renovate
`minimumReleaseAge` + `internalChecksFilter: strict`, Dependabot
`cooldown: default-days: 3` on every auto-merge-eligible ecosystem). Security
updates and first-party `damien-robotsix/*` packages are exempt — see
[repo baseline — release-age cooldown](repo-baseline.md#release-age-cooldown).

- **How to verify:** `renovate.json` exists in every Python repo (covering the
  `uv` manager); `.github/dependabot.yml` exists and covers `github-actions`
  and `pre-commit` in every repo, plus `npm` in repos with `package.json` and
  `docker` in image-shipping repos, and every image-shipping repo's
  `Dockerfile` has no `FROM …@${…}` line and no `COPY --from=<registry image>`
  (every external image is a literal `FROM <image>:<tag>@sha256:<digest>`).
  The Dependabot and Renovate dashboards
  show recent update PRs. The `dependency-cooldown-check` job
  (`scripts/check-dependency-cooldown.py` in `baseline-check.yml`) finds a
  cooldown of at least 3 days on every auto-merge path, or an accepted-risk
  entry in `.dependency-cooldown-allowlist` — warning-first, blocking from
  2027-01-31.
- **Failure prevented:** a pinned digest (base image, action SHA) rots silently
  — the image stops receiving base-OS security patches, an action runs an
  unmaintained version — with no alert; this includes a digest that looks
  pinned and "covered" but sits where Dependabot cannot read it (an `ARG`, a
  `COPY --from=<image>`). The cooldown prevents a second
  failure: a freshly published malicious release passes CI and is
  auto-merged within hours, before it can be yanked.
- **Alignment:** OpenSSF Scorecard *Dependency-Update-Tool* check; OWASP Top
  10:2025 *A03 Software Supply Chain Failures*;
  [OWASP Top 10 CI/CD Security Risks](https://owasp.org/www-project-top-10-ci-cd-security-risks/)
  *CICD-SEC-3 Dependency Chain Abuse*.
- **Detail:** [repo baseline — automated dependency updates](repo-baseline.md#automated-dependency-updates).

### 4. Workflow hardening

#### 4a. Actions pinned to commit SHAs

Every `uses:` reference — third-party actions and first-party reusable
workflows from robotsix-github-workflows alike — is pinned to its full
40-character commit SHA, with a trailing `# vX.Y.Z` version comment. A tag or branch ref drifts silently
when the publisher moves it; a SHA is immutable.

- **How to verify:** the [workflow-permissions audit](#workflow-permissions-audit)
  — `scripts/check-workflow-security.py`, run in CI — enforces this
  mechanically: every `uses:` (step-level and job-level reusable-workflow
  callers) must be pinned to a full 40-character commit SHA with a trailing
  `# <version>` comment. (Reusable workflows from robotsix-github-workflows
  use the full commit SHA of that repo's HEAD.) `grep -r 'uses:' .github/workflows/`
  additionally produces no `@main`, `@master`, `@v1`, or other mutable refs on
  third-party actions.
- **Failure prevented:** a compromised or broken action release replaces a
  trusted tag, and every CI run pulls the replacement with no review.
- **Alignment:** OpenSSF Scorecard *Pinned-Dependencies* check. This is not
  a SLSA requirement (SLSA v1.x Build L3 requires a hardened build platform,
  not pinned build dependencies); pinning hardens the build inputs that the
  separately attested provenance describes.

#### 4b. Workflow linting — actionlint + zizmor

Every workflow file is linted at commit time (`actionlint` in
`.pre-commit-config.yaml`) and at CI time (`actionlint` in the shared CI
workflow). `zizmor` audits workflow definitions for security anti-patterns
(script injection via `${{ }}` in `run:` steps, overly broad `permissions:`,
untrusted checkout of `pull_request_target` events). zizmor **blocks** only
on `robotsix-github-workflows` and on repos that opted in with
`fail-on-finding: true`; on every other repo it is **warning-only
(Phase 2)** — findings are CI annotations, not a gate. This is a dated
accepted risk (review 2027-01-31); see
[GitHub Actions security — accepted risk](github-actions-security.md#accepted-risk-warning-mode-zizmor).

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
- **How to verify:** the [workflow-permissions audit](#workflow-permissions-audit)
  — `scripts/check-workflow-security.py`, run in CI — enforces this
  mechanically: every workflow file must declare a top-level `permissions:`
  block, and no `permissions: write-all` may appear at workflow or job level.
  `grep -A5 'permissions:' .github/workflows/*.yml` additionally confirms every
  file has one with no `write-all`; `zizmor` flags missing or overly broad
  blocks for code repos.
- **Failure prevented:** a compromised third-party action in a workflow with
  `write-all` can push to `main`, exfiltrate secrets, or modify releases with
  no audit trail.
- **Alignment:** OpenSSF Scorecard *Token-Permissions* check,
  [GitHub's own guidance](https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication#permissions-for-the-github_token).

#### 4d. Runner isolation

A **public** repository never runs a job on a self-hosted runner. A
**private** repository runs on the self-hosted runner, and that runner is
hardened as described in
[repo baseline — self-hosted runner hardening](repo-baseline.md#self-hosted-runner-hardening):
ephemeral or JIT, registered only to the named private repos,
fork-PR workflows off, a visibility-change procedure, and host and network
isolation. The rule itself is set out in
[repo baseline — runner choice follows repository visibility](repo-baseline.md#runner-choice-follows-repository-visibility).

- **How to verify:** `scripts/check-runner-visibility.py` runs as the
  `runner-visibility-check` job in `baseline-check.yml`. It is
  **fail-closed from day one**, with no warning-first period. It fails
  when the repo is public and any job's `runs-on`, or a reusable-workflow
  caller's `runs-on` input, targets `self-hosted`. It also fails when
  visibility is unknown. The runner-registration and fork-PR settings are not in
  the repo, so they are checked by hand, as the [Audit](#audit) row says.
  zizmor's `self-hosted-runner` audit runs only in the *auditor* persona,
  so the fleet's pedantic zizmor invocation (gate 4b) does **not** catch
  this. The script is the gate.
- **Failure prevented:** a self-hosted runner on a public repository runs
  code from any fork pull request on the host. That gives an outsider code
  execution inside the home network, the highest-impact CI risk in these
  standards. A persistent runner shared across private repos also lets one
  compromised build poison or read another.
- **Alignment:** GitHub's
  [hardening for self-hosted runners](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions#hardening-for-self-hosted-runners)
  ("self-hosted runners should almost never be used for public
  repositories"), OpenSSF Scorecard *Dangerous-Workflow*, SLSA Build L3
  *isolated*, and OWASP CICD-SEC-4 / CICD-SEC-7.

#### Workflow-permissions audit

The **workflow-permissions audit** is the concrete, repo-local enforcement
mechanism that makes gates 4a and 4c self-enforcing — including for
**content-only repos**, which are exempt from the zizmor workflow audit (gate
4b) but must still meet 4a and 4c. For code repos, zizmor also flags both
properties, but it is warning-only (Phase 2) outside
`robotsix-github-workflows` and opted-in repos, so this script is the
blocking 4a/4c gate for every repo — code and content-only alike — and every
repo's 4a/4c requirement stays checkable without human review.

It is implemented as `scripts/check-workflow-security.py`, run in CI on every
PR (see `.github/workflows/ci.yml` and `.github/workflows/baseline-check.yml`),
and enforced on this repo as its reference implementation. It scans every
`.github/workflows/*.yml` / `*.yaml` file and fails (exit 1) on any violation:

- **4a — SHA-pinned `uses:`:** every `uses:` value (step-level and job-level
  reusable-workflow callers) must be pinned to a full 40-character commit SHA
  and carry a trailing `# <version>` comment. Local refs starting with `./`
  are exempt; `docker://` refs must pin `@sha256:<digest>` (a mutable tag
  fails). First-party robotsix reusable workflows use the full commit SHA of
  that repo's HEAD, so they must be pinned too.
- **4c — least-privilege `permissions:`:** every workflow file must declare a
  top-level `permissions:` block, and no `permissions: write-all` may appear
  at workflow or job level.

This is the mechanism referenced whenever the "workflow-permissions audit" is
cited as an existing control (e.g. [scorecard.md](scorecard.md), this page).

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
- **Alignment:** [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html),
  [OpenSSF OSPS Baseline](https://baseline.openssf.org/) *OSPS-BR-07*
  (prevent storage of unencrypted secrets in the repository). OpenSSF
  Scorecard has no secret-scanning check — its *Token-Permissions* check
  covers workflow `GITHUB_TOKEN` scope (gate 4c), not committed secrets.

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

- **How to verify:** `git ls-files` lists no credential or secret file; the
  `.gitignore` deny-list coverage is checked mechanically by
  `scripts/check-gitignore-denylist.py` (run from `baseline-check.yml`), which
  reports any missing pattern and honors per-repo negating exceptions —
  warning-first today, blocking (CI fails) from 2027-01-31; the deploy
  workflow reads secrets from `${{ secrets.* }}` and writes them via a
  transport with no delete-ordering.
- **Failure prevented:** a credential file is committed and tracked. Once in
  history it survives every later removal — deleting the file (or adding the
  `.gitignore` entry later) does not purge it from past commits, and the only
  remediation is a full history rewrite (the robotsix-mill `wp-config.php`
  incident). A deploy sync with a delete-ordering silently deletes a
  server-side secret absent from the committed tree, taking the protected
  service down (the robotsix-mill `lftp mirror --delete` trap).
- **Alignment:** [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html),
  [OpenSSF OSPS Baseline](https://baseline.openssf.org/) *OSPS-BR-07*
  (prevent storage of unencrypted secrets in the repository). OpenSSF
  Scorecard has no matching check.

**Full details:** [secret files are never tracked (dedicated doc)](secret-files-are-never-tracked.md)
— `.secrets-patterns-excluded` format, scanner integration, and the separation
from `.gitignore`.

### 6. SBOM & vulnerability audit

Every repo produces a machine-readable software bill of materials and runs a
dependency vulnerability audit on every CI run.

- **CycloneDX SBOM** generated and uploaded as a workflow artifact on every
  CI run (via the shared security workflow). The SBOM MUST be a
  standards-conformant CycloneDX document generated **natively by `uv export`
  from the lockfile** — the exact command, rationale, and artifact naming are
  defined in [CycloneDX SBOM via `uv export`](sbom-cyclonedx-uv.md), which is
  the single source of truth for lockfile-based SBOMs and must not be
  duplicated here. The upload step uses `if: always()` so a failed scan never
  silently drops the artifact.
- **`uv audit` output is not an SBOM.** `uv audit --preview-features
  audit-command,json-output --output-format json` (or `pip-audit`) emits a
  vulnerability/advisory report — OSV matches, severities, affected/fixed
  ranges — that contains no component inventory.
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
  on known vulnerabilities in the dependency tree. `uv audit` is a
  **preview-only** command (introduced in preview in uv 0.10.10, still
  preview through at least uv 0.12.8): it MUST be invoked as
  `uv audit --preview-features audit-command` — never as bare `uv audit`,
  whose availability, flags and behaviour change per release — and JSON
  output additionally requires the `json-output` preview feature
  (`uv audit --preview-features audit-command,json-output --output-format json`;
  the JSON schema is explicitly versioned `preview`). Running the gate also
  requires a pinned uv version floor: `[tool.uv] required-version =
  ">=0.12.8"` (or the `version:` input on `astral-sh/setup-uv`, which honors
  `required-version` automatically). Re-verify the flags whenever the pin is
  bumped — preview status and flag names change per release.
  **Failure prevented:** a fleet repo or a copied gate cannot run the CVE
  gate from the standard as written — bare `uv audit` is not a valid
  invocation on current uv and an unpinned uv changes the preview surface
  mid-lifecycle, silently weakening or reddening the gate per environment.
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
  bundle). `uv audit --preview-features audit-command` (or `pip-audit`)
  passes in the latest CI run.
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
  *Vulnerabilities* checks, [OpenSSF OSPS Baseline](https://baseline.openssf.org/)
  *OSPS-QA-02* (SBOM for released assets) and the *OSPS-VM* vulnerability
  management controls. SLSA Build-track provenance is a separate control
  (SLSA v1.x requires neither an SBOM nor a CVE audit) and is covered by
  [SLSA Build Track](#slsa-build-track) below.
- **Detail:** [Docker build & release — CI-time image scan](docker-standard.md#ci-time-image-scan).

## SLSA Build Track

The [SLSA v1.x Build track](https://slsa.dev/spec/v1.0/levels#build-track)
applies to the artifacts the fleet releases — the container images published by
the shared `docker-release.yml` reusable workflow (see
[Docker build & release](docker-standard.md#publish-one-reusable-workflow-the-single-method)).
Build levels are cumulative, and producing provenance is only half the control:
SLSA makes **verifying** it a separate consumer duty
([Verifying artifacts](https://slsa.dev/spec/v1.0/verifying-artifacts)). The
fleet's posture against each Build level.

The reachable Build level depends on the **runner class** the build runs on.
[Runner choice follows repository visibility](repo-baseline.md#runner-choice-follows-repository-visibility):
a **public** repository calls `docker-release.yml` on a GitHub-hosted runner,
while a **private** repository (e.g. `robotsix-invest`) passes `self-hosted` as
its `runs-on` input, so its images are built — and, once signing lands, signed —
on the fleet's persistent self-hosted runner. That runner is shared across
repositories and reused between jobs, so it does not give the run isolation SLSA
Build L3 requires ("the build platform ensures runs cannot influence one
another"): an earlier job on the host can tamper with the build cache, BuildKit
state or the toolchain. The provenance `builder.id` and runner environment also
differ from the GitHub-hosted case.

The signing mechanism also depends on **repository visibility**. GitHub
artifact attestations (`actions/attest-build-provenance`, `gh attestation
verify`) are available on GitHub Free, Pro and Team plans **only for public
repositories**; private or internal repositories require GitHub Enterprise
Cloud (per the `actions/attest-build-provenance` README, checked 2026-10-29).
The fleet does not buy Enterprise Cloud
([free-tier-only rule 3](free-tier-only.md#rules)), so private-repo images
cannot use GitHub attestations at all. They are signed instead with a
**cosign keypair** that the fleet controls (see Build L2 below). Keyless
cosign against the public Sigstore instance was rejected for private repos:
the Fulcio certificate and the Rekor entry would publish the private repo and
workflow identity to a public log. Per runner class:

| Runner class | Now | After signing lands |
| --- | --- | --- |
| Public repo, GitHub-hosted (ephemeral) | Build L1 | Build L3 (`actions/attest-build-provenance` from the isolated reusable workflow) |
| Private repo, persistent self-hosted | at most Build L1 | at most Build L2 (key-based `cosign attest`), and only once the signing key is kept off the shared runner (see Build L2); L3 only if the runner becomes ephemeral/JIT and isolated per job |

The levels below describe the GitHub-hosted case; the self-hosted caps are
stated inline.

- **Build L1 (provenance exists):** met — `docker-release.yml` builds with
  `docker buildx build --provenance mode=max --sbom true` on GitHub-hosted
  runners (public repos) or the self-hosted runner (private repos). BuildKit
  attaches an in-toto SLSA provenance statement and an SBOM to the pushed
  image index on either runner class.
- **Build L2 (hosted platform, signed provenance):** not met — the BuildKit
  provenance is an **unsigned** in-toto statement. The workflow grants
  `id-token: write` and `attestations: write`, but no step signs the
  provenance: no `actions/attest-build-provenance`, no cosign and no
  `slsa-github-generator`. Anyone who can push to the image can replace an
  unsigned statement. **Target, per repository visibility:**
  - **Public repos:** add `actions/attest-build-provenance` (Sigstore keyless
    signing via the GitHub OIDC token, stored in the GitHub attestations API)
    to the publish job, with `subject-digest` set to the pushed index digest.
  - **Private repos:** GitHub attestations need Enterprise Cloud (see above),
    so the publish job would sign the provenance with key-based cosign:
    `cosign attest --key env://COSIGN_PRIVATE_KEY --type slsaprovenance1 --predicate <provenance.json> --tlog-upload=false ghcr.io/<owner>/<repo>@<digest>`.
    **Flags checked against cosign v2.6.5** (`cosign attest --help`; the release
    binary's SHA-256 matched the release's `cosign_checksums.txt`). `--key`
    accepts `env://<VAR>` (the PEM is read from that environment variable),
    `--predicate`, `--type` (`slsaprovenance1` is in the accepted list) and
    `--tlog-upload=false` all exist. The command has not been run against a
    registry. Two constraints from the help run: cosign rejects a
    `slsaprovenance1` predicate that lacks the SLSA v1 `buildDefinition` and
    `runDetails` fields before it signs anything, and the encrypted key's
    password must come from `COSIGN_PASSWORD`, because an interactive prompt
    fails in CI. No cosign version is pinned in the fleet yet: the pin must be
    v2.6.5, or the flags must be rechecked with `cosign attest --help` for the
    version that is pinned, before the signing step lands.
    The attestation is stored in GHCR next to the image. `--tlog-upload=false`
    keeps the private provenance out of the public Rekor log. The fleet
    signing keypair's master copy lives in the self-hosted Vaultwarden. The
    private key and its password would reach the publish job as Actions
    secrets (`COSIGN_PRIVATE_KEY`, `COSIGN_PASSWORD`), which are free on private
    repositories. The deployment system holds only the public key.

    **Co-tenant exposure (blocks the L2 claim on the shared runner):** the
    self-hosted runner is shared across repositories and reused between jobs,
    and its jobs are not isolated from one another. An Actions secret is
    delivered into the environment of any job that references it, and a
    different job on the same host can reach that environment or the job
    workspace. A co-tenant job can therefore read `COSIGN_PRIVATE_KEY` and
    `COSIGN_PASSWORD`, sign a forged provenance statement for any digest, and
    publish it to GHCR next to a real image. A signature by that key proves
    only that someone holding the key signed it, not that the reusable workflow
    built the image. The key must be kept where no other job on the shared
    runner can read it (for example a signing step on an ephemeral/JIT runner
    used only for that job, or signing outside the runner host). Until then a
    private-repo image is not at Build L2 and the claim stays at Build L1.

  On the self-hosted runner the "hosted build platform" property is weaker:
  the platform is an operator-managed host, not GitHub's, so signing there
  yields at most L2, and only under the key-isolation condition above.
- **Build L3 (hardened platform, unforgeable provenance):** not met — L2 is a
  prerequisite. Once the attestation step above lands, L3 is reached **for
  public-repo images built on GitHub-hosted runners** because the signing runs
  inside the shared reusable workflow on an ephemeral runner. A caller cannot
  run its own steps in that job, and the signing identity is the reusable
  workflow's ref, not the caller's. This matches GitHub's guidance that
  artifact attestations from an isolated reusable workflow meet Build L3 —
  guidance that assumes GitHub-hosted, ephemeral runners. **Private-repo
  images built on the persistent self-hosted runner do not reach L3**: the
  reusable-workflow signing identity is the same, but the runs are not
  isolated. L3 for them requires an ephemeral/JIT runner that is isolated per
  job.
- **Verification (consumer side):** not in place. **Requirement:** before the
  deployment system rolls out an image, it verifies the image digest's
  provenance and refuses the rollout on failure, with a policy per runner
  class:
  - **Public-repo images** are verified with
    `gh attestation verify oci://ghcr.io/<owner>/<repo>@<digest> --owner <owner> --deny-self-hosted-runners`
    (or the equivalent `cosign verify-attestation` with the reusable
    workflow's certificate identity and a runner-environment check). The
    `--deny-self-hosted-runners` flag matters: the signing identity is the
    reusable workflow's ref on either runner class, so without a
    runner-environment check `gh attestation verify` passes for a
    self-hosted build too and a consumer cannot tell an L3 build from a
    self-hosted one.
  - **Private-repo images** cannot be verified with `gh attestation verify`:
    no GitHub attestation exists for them on the free plan, so that check
    would either block every private-repo rollout or be skipped silently.
    They would be verified with the fleet public key instead:
    `cosign verify-attestation --key <cosign.pub> --type slsaprovenance1 --insecure-ignore-tlog=true ghcr.io/<owner>/<repo>@<digest>`.
    The flags were checked against cosign v2.6.5 (`cosign verify-attestation
    --help`): `--key`, `--type` and `--insecure-ignore-tlog` exist under these
    names. Recheck them against the cosign version the fleet pins before this
    check is enforced.
    `--insecure-ignore-tlog=true` matches the signing side's
    `--tlog-upload=false`; the key signature is still checked. Accepting
    self-hosted, key-signed provenance for private-repo images is a dated
    **accepted risk** (accepted 2026-10-29, review 2027-01-31). The risk has
    two parts. First, the signing runner is not isolated per job, so the
    provenance is at most Build L2 and the claim is Build L1 while the key is
    reachable from co-tenant jobs. Second, a co-tenant job that reads the
    private key can forge a statement this check accepts, so a passing
    private-repo check does not show that the reusable workflow built the
    image. The risk is lifted only when the signing key is unreachable from
    every other job and the runner is ephemeral/JIT and isolated per job.
    Holding a long-lived signing key also carries a risk: anyone who steals it
    can sign a forged image. Rotate the key on any suspected exposure, on
    every review date, and whenever a repository sharing the runner is
    compromised.

  Until the signing steps above exist there is nothing signed to verify,
  so verification itself is a dated **accepted risk** (accepted 2026-10-28,
  review 2027-01-31). Both accepted risks are tracked in the [Audit](#audit)
  table and referenced from the
  [deployment system](deployment-system.md#provenance-verification-before-rollout).

**Failure prevented:** without signed and verified provenance, an image
tampered with after the build (a stolen GHCR token, a compromised push from
outside the reusable workflow) deploys exactly like a genuine one. Unsigned
provenance can be forged along with the image, and provenance that nobody
verifies blocks nothing. A Build level stated without its mechanism cannot be
audited. A Build level stated without its runner class overclaims: a
private-repo image built on the shared self-hosted runner passes the same
`gh attestation verify` check as an isolated GitHub-hosted build, so an L3
claim that ignores the runner hides a build that an earlier job on the host
could have tampered with. A signing mechanism stated without the plan it
needs overclaims too. GitHub attestations on private repos need a paid plan,
so a private-repo `gh attestation verify` check has nothing to verify. It
either blocks every rollout or is skipped quietly, and the images stay at
unsigned Build L1.

**Alignment:** OWASP Top 10:2025 *A03 Software Supply Chain Failures* and *A08
Software or Data Integrity Failures* (signing plus integrity verification), and
OpenSSF Scorecard *Signed-Releases*.

## SLSA Source Track

The [SLSA v1.2 source track](https://slsa.dev/spec/v1.2/source-requirements)
defines four cumulative levels (Source L1–L4) that apply to the change history
of the source itself, alongside the existing Build track. SLSA levels are
cumulative: a level counts as met only when every lower level is also met. The
fleet's posture against each Source level:

- **Source L1 (version controlled):** met — all source lives in GitHub, and
  every dependency is referenced by an immutable commit SHA.
- **Source L2 (history & provenance):** gap — SLSA Source L2 requires verified,
  hosted change history and contemporaneous, tamper-resistant source provenance
  attestations. Releases do not yet produce signed source provenance
  attestations; adoption is deferred pending tooling maturity and upstream
  ecosystem support.
- **Source L3 (continuous technical controls):** not met — branch protection
  with `enforce_admins: true` is configured to enforce required status checks
  on every commit to `main`, but it is **configured, not continuously
  verified**: the apply-script runs only when triggered and no automated check
  re-reads the protection settings. This is a dated **accepted risk**
  (accepted 2026-10-22, re-stated 2026-10-26, review 2027-01-26; see
  [repo baseline](repo-baseline.md#branch-protection)). Source L3 requires
  continuously enforced technical controls, so it is not reached on two
  counts: SLSA levels are cumulative and Source L2 remains a gap, and the
  branch-protection control itself is unverified.
- **Source L4 (two-party review):** not met — SLSA Source L4 requires an
  informed review by two distinct trusted persons on every change to a
  protected branch. The fleet's branch-protection rule mandates one required
  approving review. Requiring two reviewers on every PR is impractical for a
  small team and is a deliberate, documented tradeoff.

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
| Dependabot + Renovate | `.github/dependabot.yml` covers non-uv ecosystems; `renovate.json` present in Python repos; recent update PRs; 3-day release-age cooldown on every auto-merge path, verified by `scripts/check-dependency-cooldown.py` in `baseline-check.yml` (warning-first, blocking from 2027-01-31) |
| SHA-pinned actions | `grep -r 'uses:' .github/workflows/` — no mutable refs on third-party actions; `scripts/check-workflow-security.py` passes in CI |
| Workflow linting | `.pre-commit-config.yaml` includes `actionlint`; CI runs `zizmor` (content-only repos exempt from `zizmor`) |
| Least-privilege permissions | Every workflow has `permissions:` block; `scripts/check-workflow-security.py` passes in CI; `zizmor` reports clean (code repos) |
| Runner isolation | Public repos target no self-hosted runner: `scripts/check-runner-visibility.py` (`runner-visibility-check` job in `baseline-check.yml`) passes. It is fail-closed, and private repos on GitHub-hosted runners only warn. By hand: `gh api repos/<owner>/<repo>/actions/runners` shows no runner registered to any public repo (personal account, so no runner groups); for private repos, "Run workflows from fork pull requests" is off; the runner is ephemeral/JIT — per [repo baseline](repo-baseline.md#self-hosted-runner-hardening) |
| Actions PR approval disabled | `gh api repos/<owner>/<repo>/actions/permissions/workflow -q .can_approve_pull_request_reviews` returns `false`, so `GITHUB_TOKEN` cannot satisfy the required approving review — per [repo baseline](repo-baseline.md#branch-protection); set by the robotsix-github-workflows apply-script; not machine-verified since the watchdog's [retirement](mill-agents.md#retired-agents) — check by hand |
| Secret push protection | Push protection enabled in repo Security settings; `detect-secrets` in pre-commit; CI runs TruffleHog (content-only repos exempt from TruffleHog) |
| Credential-file deny list | `.gitignore` covers `.htpasswd`, `.env`/`.env.*`, `wp-config*.php`, `*.pem`, `*.key`, `*secret*`, `*.p12` — verified by `scripts/check-gitignore-denylist.py` in `baseline-check.yml` (warning-first, blocking from 2027-01-31; honors per-repo negating exceptions) — and `.secrets-patterns-excluded` presence and wiring by `scripts/check-secrets-patterns-excluded.py` (same dates) |
| SBOM* | CI uploads CycloneDX artifact |
| CVE audit* | `uv audit --preview-features audit-command` at the pinned uv version / `pip-audit` passes in CI |
| Distribution / registry | No publish to a public package index and no public-registry credentials, per [distribution & packaging rules 4–5](distribution-packaging.md#enforcement). Verified by the `public-registry-check` job (`scripts/check-public-registry.py` in `baseline-check.yml`), which finds no `registry.npmjs.org` / `upload.pypi.org` / `pypi.org/legacy` endpoint, no `npm publish` / `twine upload` / `uv publish` without an approved internal registry, and no `NPM_TOKEN` / `PYPI_TOKEN` secret in workflows, `package.json` `publishConfig`, `.npmrc` or `pyproject.toml` — warning-first, blocking from 2027-01-31 |
| SLSA Build provenance | Image-shipping repos: the published image index carries BuildKit provenance (`docker buildx imagetools inspect ghcr.io/<owner>/<repo>@<digest> --format '{{ json .Provenance }}'` is non-empty) — Build L1 on either runner class. Once `docker-release.yml` signs it, the deployment system verifies before rollout: public-repo (GitHub-hosted) images with `gh attestation verify oci://ghcr.io/<owner>/<repo>@<digest> --owner <owner> --deny-self-hosted-runners` (Build L3); private-repo (self-hosted) images — which cannot use GitHub attestations on the free plan — with the fleet cosign public key, once the pinned cosign version is confirmed to accept these flags (v2.6.5 does): `cosign verify-attestation --key <cosign.pub> --type slsaprovenance1 --insecure-ignore-tlog=true ghcr.io/<owner>/<repo>@<digest>` (at most Build L2, and Build L1 while the signing key is reachable from co-tenant jobs on the shared runner; self-hosted, key-signed provenance is a dated accepted risk, accepted 2026-10-29, review 2027-01-31, until the key is isolated and the runner is ephemeral/JIT and isolated per job). Signing and verification are a dated accepted risk until then (review 2027-01-31) — per [SLSA Build Track](#slsa-build-track) |
| Container image scan | Trivy PR-scan and publish workflows present and passing (image-shipping repos only) |
| Vulnerability disclosure | `SECURITY.md` present at repo root with contact method, response-time expectation, and coordinated-disclosure statement — fail-closed: `security-md-check` in `baseline-check.yml` fails CI (exit 1) when it is missing or incomplete |
| Config API secret redaction | Deployment system / management surfaces: central-deploy config-read endpoints (`GET /config`, version-history reads, audit-log serialization) route through `mask_secrets()` before serialization; config writes use `apply_update()` merge-on-write; version history stores no secret values — audited per [config standard §3](config-standard.md#how-this-is-enforced) |
| Config secrets typed SecretStr | Repos with a pydantic config model: `.pre-commit-config.yaml` includes the remote `check-secret-str` hook (`repo: https://github.com/damien-robotsix/robotsix-standards`) at a pinned `rev:`, and `config/config.schema.json` marks every secret-named field (`api_key`, `token`, `password`, `secret`, ...) `writeOnly: true`. The second check is a fallback you can grep without running the hook. Per [config standard §3](config-standard.md#3-one-secret-convention) |
| Config history contains no secret values | Components with a `/config` surface: the `<config>.versions` sidecar's `data` snapshots carry only a set/unset marker for each `SecretStr` / `writeOnly` field, per [config ownership](config-ownership.md#where-the-history-lives-and-who-implements-it). Until the planned `robotsix_config.history` unit test (write a secret, rotate it, assert the old value is absent from `<config>.versions`) exists, audit this by code review of the sidecar writer; the test is not yet in place (CWE-312, CWE-226) |
| Log hygiene | Deployable HTTP components: a test sends a request carrying `Authorization: Bearer <sentinel>` and asserts the sentinel string is absent from captured log output; a grep/Semgrep rule finds no logging call that passes `request.headers` or `request.url` (e.g. `logger\..*\(.*request\.headers` and `logger\..*\(.*request\.url\b(?!\.path)`); a structlog redaction processor sits at the start of the chain; any per-request DEBUG override accepts only authenticated operator or internal callers — per [logging rule 6](logging.md#6-never-log-sensitive-data) (CWE-532, OWASP A09:2025) |
| LLM & agentic security | Repos whose core function involves LLM agents: `robotsix-llmio` pinned to a commit SHA in `pyproject.toml`; llmio level/model selection is an explicit config field (not hard-coded, not env); tracing/provider credentials are `SecretStr` in the canonical `langfuse`/`openrouter` config blocks; destructive git ops default to dry-run; scoped single-repo token (no org/admin scopes). Non-mechanical controls (LLM01/02/05/06/07/08/10, ASI01–ASI10) are covered by the periodic standards-audit agent — see below |

*Content-only repos are exempt per the preamble above.

A repo that fails any gate is non-compliant; the fix is always the same — call
the shared workflow, or enable the GitHub setting.

### LLM & agentic security audit

This governs repos whose core function involves LLM agents — the fleet's
implement/refine agents, `robotsix-chat`, and any component that calls a model
through `robotsix-llmio`. The requirements live in the
[component standard's LLM security section](component-standard.md#llm-security)
and its [Agentic Applications mapping](component-standard.md#agentic-applications).
Most of its MUST/MUST NOT controls are design-level rules with no CI gate, so
enforcement is by **audit** — checked at component code review and by the
periodic standards-audit agent — against the criteria below, mirroring the
pattern in [HTTP security headers](http-security-headers.md#how-this-is-enforced),
[SSE response headers](sse-response-headers.md#how-this-is-enforced), and
[SSRF-hardened fetchers](ssrf-hardened-fetchers.md#how-this-is-enforced).

**Mechanically verifiable subset** — checked by the SHA-pin, config-schema, and
code-review gates already in this standard:

| Control | Audit criterion |
|---|---|
| LLM04 — supply chain | `robotsix-llmio` is pinned to a full commit SHA (not a branch or tag) in `pyproject.toml`; llmio level/model selection is an explicit config field, not hard-coded in code or read from env. |
| LLM02/03/08 — secrets & least privilege | Tracing/provider credentials are `SecretStr` fields in the canonical `langfuse`/`openrouter` config blocks; destructive git operations (`push`, `force-push`, branch deletion) default to dry-run; git uses a scoped single-repo token with no org/admin scopes. |

**Periodic standards-audit-agent checks** — design-level controls an auditor
reads against the criteria below:

| Rule | Audit criterion |
|---|---|
| LLM01 — prompt injection | Every path where untrusted data (ticket bodies, PR diffs, chat messages) reaches a prompt delimits or parameterises it; model output is never concatenated into a new prompt without sanitisation. |
| LLM02 — sensitive information | PII/secrets are scrubbed or tokenised before prompt assembly; raw model context is never logged. |
| LLM05 — data & model poisoning | RAG/context sources (ticket bodies, PR diffs, chat history) are the untrusted-input set delimited under LLM01, so LLM05 is satisfied by the LLM01 criterion while the fleet does not fine-tune. No fine-tuning or training pipeline exists; a repo that adds one must cite a dataset integrity check (source pinning plus a checksum or known-good-baseline comparison) before the data is used. |
| LLM06 — unbounded consumption | Every agent entry point declares a finite request/token budget in its config — a concrete number, never unlimited, `None` or `0`-as-unlimited (e.g. the robotsix-mill implement agent's ~200-request cap and sub-agents' ~30-request cap); the auditor greps the agent config for the budget field and confirms every entry point sets one. Every run is wrapped in a wall-clock timeout: Actions-hosted runs carry `timeout-minutes` on each job (machine-checked by `scripts/check-workflow-timeouts.py`); runs outside Actions (e.g. a long-running mill service) must show an equivalent per-run timeout in code or config. `spawn_subtask` (or any child-agent spawner) enforces a maximum depth or count, so a child cannot spawn without bound. |
| LLM07 — misinformation | Output a human would rely on carries a provenance tag; output that commits a side-effect is verified by a secondary system or human before it lands. |
| LLM08 — hidden context | System prompts contain no operational secrets (stored in `SecretStr` config instead); embedded instructions and metadata fields are reviewed for disclosure risk. |
| LLM10 — improper output handling | Model output rendered to a user or fed into an action is validated/sanitised before use. |
| ASI01–ASI10 | Each agentic control maps to the fleet control it relies on (LLM01–LLM10, scoped tokens, dry-run gates, ephemeral job identity) as documented in the component standard. |

A repo whose core function involves LLM agents that fails any criterion is
non-compliant.

## See also

- [Repo baseline — CI and security gates](repo-baseline.md#ci-and-security-gates)
- [Repo baseline — automated dependency updates](repo-baseline.md#automated-dependency-updates)
- [Python practices — lint, types, and security lint](python.md#lint-types-and-security-lint)
- [Docker build & release — CI-time image scan](docker-standard.md#ci-time-image-scan)
- [OpenSSF Scorecard](https://securityscorecards.dev/)
- [SLSA Supply-chain Levels for Software Artifacts](https://slsa.dev/)
- [OWASP Top 10 CI/CD Security Risks](https://owasp.org/www-project-top-10-ci-cd-security-risks/)
- [Component standard — LLM security](component-standard.md#llm-security)
- [Component standard — Agentic Applications](component-standard.md#agentic-applications)
- [Config standard — Langfuse configuration](config-standard.md#7-langfuse-configuration)
