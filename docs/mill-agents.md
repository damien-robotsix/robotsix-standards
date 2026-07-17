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

- **Completeness.** Every security area relevant to the fleet (CodeQL, secret
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
- Non-security repo hygiene (changelog format, README skeleton, towncrier).

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
