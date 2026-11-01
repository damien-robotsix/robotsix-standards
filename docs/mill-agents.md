# Mill agents on this repo

robotsix-standards is a mill-managed repo — the
[robotsix-mill](https://github.com/damien-robotsix/robotsix-mill) runs periodic
agents against it to keep the standards themselves healthy. These agents are
defined in `.robotsix-mill/agents/` and are picked up automatically by the mill
as bespoke per-repo passes.

## Security posture audit (`security-posture-audit`)

**Purpose:** Audit the security-related standards definitions for completeness,
internal consistency, currency against upstream best practices, and
enforceability.

**Scope:** The **standard definitions** themselves — the pages under `docs/`
and the config files under `.github/` that define what the fleet must do.
Downstream repos' compliance with these standards is the job of the general
audit process; this agent checks whether the standard is well-formed enough to
be auditable.

**What it checks:**

- **Completeness.** Every security area relevant to the fleet (Semgrep, secret
  scanning, push protection, dependency-review, SBOM, Dependabot ecosystems,
  SHA-pinned actions, least-privilege permissions, image scanning, etc.) must
  have a named, discoverable requirement in the standards.

- **Internal consistency.** Two standards pages must not conflict — a rule
  stated twice must agree both times.

- **Currency.** Each requirement should reflect current OWASP, OpenSSF
  Scorecard / Best Practices Badge, and SLSA guidance at the tier appropriate
  to the fleet.

- **Enforceability.** Every SHOULD/MUST requirement must be either
  machine-checkable (a CI gate, a Dependabot ecosystem, a reusable workflow)
  or covered by a periodic agent that verifies it. Requirements described as
  "report-only" with no automated check are aspirations, not standards.

**What it does NOT audit:**

- Downstream repos' compliance with these standards.
- The implementation of security tooling (robotsix-github-workflows,
  robotsix-mill agents) — those are separate repos.
- Non-security repo hygiene (changelog format, README skeleton, release-please).

**Output:** Draft tickets filed on the robotsix-standards board for gaps or
outdated requirements it finds. A clean pass with no findings is a valid
result — the agent does not invent gaps to fill a quota.

**Cadence:** Weekly (604800 seconds). The agent carries a memory ledger across
passes so it doesn't re-audit unchanged content and can defer long-running
investigations.

**Capability level:** 2 (intermediate reasoning). The audit requires comparing
standards text against upstream best-practice documents and cross-referencing
multiple standards pages — a level-1 agent doesn't have the context window or
reasoning depth for that.

**Web knowledge:** Enabled. The agent uses `ask_web_knowledge` to query current
OWASP Top 10, OpenSSF Scorecard checks, and SLSA level requirements when it
needs to verify currency.

**Tools:** Read-only — `read_file`, `list_dir`. The agent cannot modify
standards content; all findings go through the normal ticket pipeline so an
operator reviews every proposed change.

## Repo retirement check

**Agent:** `repo-retirement-check` (defined in
`.robotsix-mill/agents/repo-retirement-check.yaml`).

**Purpose:** Enforce the [repo-baseline](repo-baseline.md#retiring-a-repo)
retirement threshold — flag fleet repos that are past it and not yet retired.

**Threshold it enforces:** a repo is past the retirement threshold when it has
had no merged commit to its default branch for 12 consecutive months. Such a
repo must be retired or carry an explicit, dated maintenance declaration in
its README.

**What it does NOT do:** it never retires a repo. It measures each fleet
repo's last default-branch activity, flags repos past the threshold, and files
draft retirement tickets; the operator decides retire vs. redeclare
maintained.

**Output:** one draft ticket per repo past the threshold, naming the repo, its
last default-branch commit date, and the recommended action. A clean pass with
no findings is a valid result.

**Cadence:** monthly (2592000 seconds).

**Capability level:** 2 (intermediate reasoning — reading the fleet roster and
judging what counts as real activity requires more than a level-1 lookup).

**Web knowledge:** Disabled — the check is fleet-internal, not upstream-driven.

**Tools:** Read-only with respect to the fleet — reads `docs/fleet.md` for the
roster, queries last default-branch commit dates via the mill's GitHub access,
and files draft tickets. It cannot archive, privatize, or edit any repo; all
retirement actions flow through the normal ticket pipeline.

## Fleet compliance audit

**Agent:** `fleet-compliance-audit` (defined in
`.robotsix-mill/agents/fleet-compliance-audit.yaml`).

**Purpose:** Verify that fleet repositories actually *comply* with the
standards this repo documents — the loop that `security-posture-audit` (the
standard definitions themselves) leaves open. It implements the verification
[AGENT.md](https://github.com/damien-robotsix/robotsix-standards/blob/main/AGENT.md)
demands: check claims about fleet behavior against the actual repos instead
of trusting that documented standards are followed.

**What it checks:** for a rotating subset of non-archived fleet repos, the
standards that are verifiable mechanically from repo contents — REUSE/SPDX
compliance ([reuse-spdx-compliance](reuse-spdx-compliance.md)), CI gate
presence ([python-ci-workflow](python-ci-workflow.md)), config schema sync
([config-standard](config-standard.md)), Dockerfile pattern compliance
([docker-standard](docker-standard.md)), pre-commit configuration
([ci-lint-pinning](ci-lint-pinning.md)), and GitHub Actions security
([github-actions-security](github-actions-security.md)). A check that does
not apply to a repo is skipped, never flagged.

**Sampling:** it does not scan the whole fleet every run. Each pass picks a
rotation subset of roughly 25–33% of the repos — the least-recently-checked
ones per its memory ledger — so the fleet is covered over three to four
passes and drift stays visible without a full-fleet scan each month.

**What it does NOT do:** it never edits, opens PRs against, or remediates
another repo. It reads each sampled repo, records per-standard compliance,
and files draft tickets; the operator remediates.

**Output:** one draft ticket per repo with gaps, listing every failing
check, the standard it violates, observed vs. required, and a concrete
remediation. The memory ledger carries a per-standard compliance tally so
drift is visible across passes. A clean pass with no findings is a valid
result.

**Cadence:** monthly (2592000 seconds).

**Capability level:** 2 (intermediate reasoning — mapping repo contents
against several standards pages and judging applicability per repo requires
more than a level-1 lookup).

**Web knowledge:** Disabled — the check compares fleet repos against this
repo's own standards, not upstream sources.

**Tools:** Read-only with respect to the fleet — reads `docs/fleet.md` and
the standards pages for the requirements, inspects each sampled repo's
contents via the mill's GitHub access, and files draft tickets. It cannot
change any repo; all remediation flows through the normal ticket pipeline.

## Component security audit

**Agent:** `component-security-audit` (defined in
`.robotsix-mill/agents/component-security-audit.yaml`).

**Purpose:** Re-check fleet components against the **audit-only** security
criteria, which are design-level MUSTs that no CI gate can inspect. Without this
agent, those criteria would be checked once at code review and never again.
*Failure mode this prevents:* a security header, CORS allowlist, fetcher guard
or agent budget that drifts after merge goes unseen, because nothing re-checks
it (OWASP Top 10 A02:2025, Security Misconfiguration). A MUST with no recurring
check fails the enforceability rule the
[security posture audit](#security-posture-audit-security-posture-audit)
applies. `fleet-compliance-audit` covers only the mechanically verifiable
standards. This agent is the periodic check for the design-level ones.

**What it checks:** the "How this is enforced" criteria of each page below,
applied to the repos each page governs:

- [HTTP security headers](http-security-headers.md#how-this-is-enforced):
  deployable HTTP components.
- [CORS policy](cors-policy.md#how-this-is-enforced): deployable HTTP
  components.
- [SSE response headers](sse-response-headers.md#how-this-is-enforced):
  components that emit `text/event-stream`.
- [SSRF-hardened fetchers](ssrf-hardened-fetchers.md#how-this-is-enforced):
  every tool that fetches a caller- or model-influenced URL.
- [Chat access §5, chat observability](chat-access-standard.md#5-chat-observability):
  central-deploy.
- [Config standard §3, management-surface secrets](config-standard.md#how-this-is-enforced):
  central-deploy's config API and Configure UI, and every deployable
  component with a `/config` surface (`GET /config` goes through
  `robotsix_config.mask_secrets`, writes through `apply_update`, rollback
  through `rollback`, and `GET /config/versions` through `read_versions`
  with no secret value in its response; no hand-rolled config serializer;
  version history stores no secret values).
- [LLM security](component-standard.md#how-this-pages-security-rules-are-enforced)
  (including LLM05 and LLM06) and the
  [LLM & agentic security audit](security-posture.md#llm-agentic-security-audit)
  (LLM01/02/05/06/07/08/10, ASI01–ASI10): LLM repos.

A criterion that does not apply to a repo is skipped, never flagged. A
design-level criterion the agent cannot judge confidently from the source is
recorded as inconclusive in its ledger, not filed as a finding.

**Sampling:** each pass audits a rotation subset of roughly 25–33% of the
in-scope repos (deployable HTTP components, LLM repos, and central-deploy),
choosing the least-recently-audited ones per its memory ledger. Every in-scope
repo is covered over three to four passes.

**What it does NOT do:** it never edits, opens PRs against, or remediates
another repo. It does not repeat the mechanical checks that
`fleet-compliance-audit` already runs.

**Output:** one draft ticket per repo with gaps, filed on that repo's board.
Each ticket lists every failing criterion, the page and section it violates,
the evidence (file and line), observed vs. required, and a concrete
remediation. A clean pass with no findings is a valid result.

**Cadence:** monthly (2592000 seconds).

**Capability level:** 3. Most criteria are design-level: judging whether
untrusted data is delimited before prompt assembly, or whether the validated
address is the address connected to, means reading and reasoning about code
paths. Matching strings is not enough, so a level-2 agent is too shallow.

**Web knowledge:** Disabled. The agent compares fleet repos against this
repo's own criteria, not against upstream sources.

**Tools:** Read-only with respect to the fleet. It reads `docs/fleet.md` and
the standards pages, inspects each sampled repo's source through the mill's
GitHub access, and files draft tickets.

## Retired agents

- **`branch-protection-check`** — retirement decided 2026-10-22 by operator decision
  (ticket bd7e: "retire the check rather than provision a credential"); removed
  in 2026-10-26 (#434). It never had GitHub API access, so it never verified
  anything. Fleet branch-protection posture (incl. Actions PR approval) is **not**
  machine-verified — recorded as an accepted risk in
  [repo-baseline](repo-baseline.md#branch-protection). *Failure mode this
  note prevents:* readers trusting a watchdog that no longer runs.
