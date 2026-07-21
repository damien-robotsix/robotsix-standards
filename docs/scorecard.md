# OpenSSF Scorecard

> **Scope: deployable components only.** This is *in addition to* the
> [repo baseline](repo-baseline.md) and [security posture](security-posture.md),
> which every repo follows.

The [OpenSSF Scorecard](https://securityscorecards.dev/) independently audits
~20 supply-chain health checks — Dangerous-Workflow patterns, token permissions,
Branch-Protection, Code-Review, Signed-Releases, dependency update cadence,
fuzzing, and more — producing a single numeric score. Several of these checks
are not covered by the fleet's existing security stack (CodeQL, Bandit,
gitleaks, Trivy, trufflehog, pip-audit, dependency-review, zizmor, SBOM), so
Scorecard closes the last common gap in a mid-2025 Python security stack.

The fleet's other security gates (Semgrep, dependency-review, Dependabot,
workflow hardening, secret scanning, SBOM) are each verified independently by
the [security posture](security-posture.md) standard. Scorecard adds an
**independent, cross-check audit** — it verifies those gates from outside the
fleet's own tooling, catching drift that a per-gate self-audit would miss.

## The workflow

Every deployable component MUST include `.github/workflows/scorecard.yml` with
these properties:

### Schedule and trigger

- **Weekly cron** (e.g. `0 0 * * 0` — midnight Sunday UTC). The Scorecard
  checks evolve; a weekly run catches regressions without the noise of a
  per-commit gate.
- **Push to the default branch** (`push: branches: [main]`). A push to main
  re-runs the analysis immediately, so a fix or config change is reflected
  without waiting for the cron.

### Action pinning

The `ossf/scorecard-action` MUST be pinned to a full 40-character commit SHA,
with a trailing `# vX.Y.Z` version comment. This is the same SHA-pinning rule
that [security posture gate 4a](security-posture.md#4a-actions-pinned-to-commit-shas)
requires for every third-party action.

### SARIF upload

Results MUST be published to the repo's GitHub Security tab via
`github/codeql-action/upload-sarif`, also pinned to a full commit SHA. The
SARIF file is the Scorecard action's output; the upload makes results visible
in the repository's Security tab alongside CodeQL and secret-scanning findings.

### Permissions

The workflow MUST declare a top-level `permissions:` block with exactly these
scopes:

```yaml
permissions:
  security-events: write   # for uploading SARIF results
  id-token: write          # for publishing results to the OpenSSF REST API (optional but recommended)
  contents: read           # for checking out the repo
```

No other permissions. This follows the least-privilege rule in
[security posture gate 4c](security-posture.md#4c-least-privilege-permissions-blocks).

## Score target

The fleet targets a Scorecard score of **≥ 7/10** (out of 10). This is an
aspirational target, not a hard CI gate — Scorecard runs as an audit, not a
blocking check. A repo below 7/10 is non-compliant and must be remediated, but
the Scorecard workflow itself does not fail the build.

Individual checks that commonly drag the score below 7 in the fleet:

- **Branch-Protection** — requires `include_admins: true` and required status
  checks (already met by the [repo baseline](repo-baseline.md)).
- **Code-Review** — requires at least one approving review before merge
  (already met).
- **Token-Permissions** — requires `permissions: read-all` at the top level
  of every workflow (already met by gate 4c).
- **Dangerous-Workflow** — flagging untrusted `pull_request_target` usage
  (already caught by zizmor in gate 4b).
- **Signed-Releases** — requires signed release artifacts. Deferred: the
  fleet does not currently sign releases.

Checks that are *not* covered by existing fleet gates and represent new
surface:

- **Fuzzing** — the fleet does not currently require fuzzing. This is a known
  gap; the Scorecard result documents it without creating a per-repo mandate.
- **CII-Best-Practices** — the fleet does not currently require an OpenSSF
  Best Practices badge. Like fuzzing, this is documented by Scorecard but not
  mandated by this standard.

## How it fits with the security posture standard

The [security posture](security-posture.md) standard defines self-enforcing,
per-gate CI controls. Scorecard is an **independent audit** — it re-verifies
those controls from the outside:

- Gate 1 (Semgrep SAST) → Scorecard *SAST* check
- Gate 2 (dependency-review) → Scorecard *Dependency-Update-Tool* and *Vulnerabilities* checks
- Gate 3 (Dependabot) → Scorecard *Dependency-Update-Tool* check
- Gate 4a (SHA-pinned actions) → Scorecard *Pinned-Dependencies* check
- Gate 4b (workflow linting) → Scorecard *Token-Permissions* and *Dangerous-Workflow* checks
- Gate 4c (least-privilege permissions) → Scorecard *Token-Permissions* check
- Gate 6 (SBOM & vulnerability audit) → Scorecard *SBOM* and *Vulnerabilities* checks

A repo that passes every security-posture gate should score ≥ 7 on Scorecard.
If it doesn't, either a gate has drifted or Scorecard is checking something the
fleet doesn't yet cover — both are actionable findings.

## How to verify

- `.github/workflows/scorecard.yml` exists and matches the schedule, trigger,
  action pinning, SARIF upload, and permissions requirements above.
- The repo's Security tab shows Scorecard results under "Code scanning."
- The Scorecard badge in the repo README shows ≥ 7/10 (or an open ticket
  tracks the remediation).

## Failure prevented

A supply-chain weakness that every other fleet security gate misses — e.g. a
workflow that passes zizmor but still triggers a Scorecard *Dangerous-Workflow*
finding, or a dependency-update gap that Dependabot's config doesn't cover —
goes undetected indefinitely. Scorecard's outside-in audit catches the gaps
that self-audit inevitably misses.

## See also

- [Security posture](security-posture.md) — the per-gate security controls
  Scorecard cross-checks.
- [Repo baseline — CI and security gates](repo-baseline.md#ci-and-security-gates)
- [OpenSSF Scorecard](https://securityscorecards.dev/)
- [OpenSSF Scorecard GitHub Action](https://github.com/ossf/scorecard-action)
