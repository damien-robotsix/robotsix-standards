# GitHub Actions security (zizmor)

> **Scope: every robotsix repository with GitHub Actions workflows.**
> This is *in addition to* the [repo baseline](repo-baseline.md) and
> [security posture](security-posture.md), which every repo follows.
> Content-only repos (documentation, standards, static content — no
> `src/` directory, no container image) are exempt from the zizmor
> audit, as documented in the security posture preamble.

[zizmor](https://github.com/woodruffw/zizmor) is a static-security
auditor for GitHub Actions workflows by Trail of Bits. It catches
workflow-level vulnerabilities that generic linters and human review
miss: template-injection via `${{ }}` in `run:` blocks,
overly broad `permissions:` on `GITHUB_TOKEN`, bot-condition spoofing
(`github.actor` checks without verifying the trigger), unpinned actions,
credential persistence, and artifact poisoning.

The fleet's automation workflows — App-token minting, deps-bump,
pin-bump, auto-release, docker-release — handle untrusted PR input
and hold write permissions or secrets. A single uncaught injection
in one of these workflows compromises the entire repo's CI surface
and potentially the fleet's shared secrets.

## The rule

**zizmor is a required CI gate for every `robotsix-` fleet repo
with GitHub Actions workflows.** Every workflow file (`.github/workflows/*.yml`)
must pass zizmor's audit at the configured minimum severity. The gate is
delivered through a shared reusable workflow in
[robotsix-github-workflows](https://github.com/damien-robotsix/robotsix-github-workflows)
so that one workflow definition protects the entire fleet — no per-repo
copy-paste, no per-repo version skew.

## Canonical invocation

The shared reusable workflow runs zizmor with these parameters:

```bash
zizmor --pedantic --min-severity medium .github/workflows/
```

- **`--pedantic`** — enables every audit check, including informational and
  experimental rules. An injection vector that a non-pedantic run would skip
  is still a vulnerability; the pedantic flag closes that gap.
- **`--min-severity medium`** — findings at `medium` severity or higher fail the
  gate. Low-severity and informational findings surface as annotations
  (warning mode) but do not block.

The full audit catalog is documented upstream:
[zizmor audits](https://woodruffw.github.io/zizmor/audits/).

### In pre-commit

zizmor is also available as a pre-commit hook — `pre-commit run zizmor`
runs the same audit locally before the push. Repos SHOULD add it to
`.pre-commit-config.yaml` so that workflow-authors catch findings at
commit time rather than waiting for CI. The pre-commit hook version must
match the CI version, following the
[CI lint tool pinning](ci-lint-pinning.md) rule.

## Phased rollout

zizmor is rolled out fleet-wide in three phases. No repo moves to a
later phase before it is demonstrably clean at the current phase.

### Phase 1 — error gate on `robotsix-github-workflows` (active)

The highest-leverage placement is the shared-workflow repo itself.
`robotsix-github-workflows` houses the reusable workflows that every fleet
repo calls. A vulnerability in a shared workflow propagates to every
downstream caller — one injection in the shared Python CI workflow,
and every Python repo's CI is compromised.

zizmor runs as a **fail-closed CI gate** on `robotsix-github-workflows`
(already active as of August 2025). Every PR that touches a workflow file
must pass `zizmor --pedantic` with zero findings at any severity. This
gate protects the fleet's highest-value workflow surface.

### Phase 2 — warning mode fleet-wide (current)

Every other fleet repo with GitHub Actions workflows runs zizmor in
**warning mode**: findings are published as CI annotations and surfaced
in the fleet dashboard, but do not block the PR or the merge. No repo
is blocked before it has had a chance to clean up existing findings.

The shared reusable workflow accepts a `fail-on-finding` input (default
`false` in Phase 2). A repo that is already clean can opt in to
fail-closed early by setting `fail-on-finding: true` — but the fleet-wide
default remains warning-only until Phase 3.

### Phase 3 — per-repo fail-closed (tracked)

Each repo is promoted to fail-closed individually once it demonstrates
a clean zizmor run (zero findings at `--min-severity medium`) on its
default branch. Promotion is tracked in the fleet dashboard; remaining
warning-mode repos are tracked until the fleet is fully migrated.

Once a repo is fail-closed, zizmor becomes a blocking CI gate — every PR
that introduces a new finding at `medium` or higher severity is rejected
until the finding is fixed or suppressed with a documented rationale.

## How to verify

- The repo's CI workflow calls the shared zizmor reusable workflow from
  `robotsix-github-workflows`.
- For fail-closed repos: the latest CI run on the default branch shows
  a passing zizmor gate with zero findings.
- For warning-mode repos: the latest CI run shows zizmor annotations
  but the gate does not block.
- Content-only repos are exempt — see the scope block above.

## Failure modes prevented

- **Template injection via `${{ }}` in `run:` blocks.** A workflow that
  interpolates `${{ github.event.issue.title }}` or
  `${{ github.event.pull_request.body }}` directly into a shell step
  executes attacker-controlled code in the CI context — with access to
  every secret and write permission that workflow holds. zizmor's
  [template-injection](https://woodruffw.github.io/zizmor/audits/#template-injection)
  audit catches this.
- **Overly broad `permissions:` on `GITHUB_TOKEN`.** A workflow without
  a top-level `permissions:` block defaults to `write-all` — a
  compromised action or step can push to `main`, exfiltrate secrets,
  or modify releases. zizmor's
  [excessive-permissions](https://woodruffw.github.io/zizmor/audits/#excessive-permissions)
  audit flags missing or over-broad blocks.
- **Untrusted checkout of `pull_request_target` events.** The
  `pull_request_target` trigger runs in the *target* repo's context
  with full write access, but checks out the *fork's* code. Checking
  out and executing untrusted PR code in this context is a known
  escalation path. zizmor's
  [untrusted-checkout](https://woodruffw.github.io/zizmor/audits/#untrusted-checkout)
  audit catches it.
- **Artifact poisoning.** A workflow that uploads an artifact from an
  untrusted PR context and later downloads it in a privileged context
  (e.g. a release workflow) allows an attacker to inject malicious
  content into a trusted pipeline stage. zizmor's
  [artifact-poisoning](https://woodruffw.github.io/zizmor/audits/#artifact-poisoning)
  audit catches the cross-workflow pattern.
- **Credential persistence.** A workflow that writes secrets or tokens
  to a file or environment variable that persists across steps risks
  leaking them to a later, less-trusted step. zizmor's
  [credential-persistence](https://woodruffw.github.io/zizmor/audits/#credential-persistence)
  audit flags this.
- **Known-vulnerable actions.** A workflow that uses an action at a
  version with a published security advisory runs known-exploitable
  code in CI. zizmor's
  [known-vulnerable-actions](https://woodruffw.github.io/zizmor/audits/#known-vulnerable-actions)
  audit catches this.

## Relationship to other standards

- **[Security posture — gate 4b](security-posture.md#4b-workflow-linting-actionlint-zizmor)**
  already lists zizmor as a required workflow-linting gate. This page
  expands the gate into a standalone standard with canonical invocation,
  severity policy, and phased rollout. The rule text lives here; the
  security posture page cross-references it.
- **[CI lint tool pinning](ci-lint-pinning.md)** — the version of zizmor
  run in CI must match the version in `.pre-commit-config.yaml`. The
  shared reusable workflow pins zizmor's version; downstream repos
  consume it by reference rather than installing it directly.
- **[Repo baseline — CI and security gates](repo-baseline.md#ci-and-security-gates)**
  lists zizmor as part of the standard gate set.
- **[OpenSSF Scorecard](scorecard.md)** — not used. Scorecard's
  *Token-Permissions* and *Dangerous-Workflow* checks overlap with zizmor's
  audit surface, so the fleet dropped Scorecard (operator decision,
  2026-08-13) and gates those properties with zizmor instead. See
  [OpenSSF Scorecard (not used)](scorecard.md) for the rationale.

## See also

- [zizmor — GitHub Actions static-security auditor](https://github.com/woodruffw/zizmor)
- [zizmor audit catalog](https://woodruffw.github.io/zizmor/audits/)
- [Security posture — workflow hardening](security-posture.md#4-workflow-hardening)
- [GitHub Actions security hardening](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)
- [OWASP Top 10 CI/CD Security Risks](https://owasp.org/www-project-top-10-ci-cd-security-risks/)
