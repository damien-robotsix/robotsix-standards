# Free-tier-only (no paid services)

The fleet runs on **free and open-source tooling only**. No repo may depend on
a paid or metered third-party service for its build, test, release, deploy, or
runtime path. The single, deliberate exception is **LLM agent inference**
(OpenRouter / Anthropic / other model providers) — the fleet is agent-driven
and model calls are a paid necessity. Everything else must be free-tier or
self-hosted.

The point is resilience as much as cost: a metered service that runs out of
credits **silently stops** — CI won't run, images won't pull, deploys stall —
and the fleet has no way to top it up. Free tiers and self-hosted
infrastructure don't have that failure mode.

## Rules

1. **CI/CD runs on a free tier.** GitHub Actions is free and unlimited on
   **public** repositories using GitHub-hosted runners; it is **metered
   (paid minutes)** on private repositories. Therefore:
   - A repo that runs Actions is either **public**, or runs its Actions on a
     **self-hosted runner** (`runs-on: self-hosted`). Private + GitHub-hosted
     is not allowed — it burns paid minutes.
2. **Container images are free to store and pull.** GHCR is free for **public**
   packages; **private** packages are metered (storage + egress) and the deploy
   server pulls images constantly. Fleet images are therefore **public
   packages** (or served from a self-hosted registry). Package visibility is
   independent of repo visibility — a public repo can still publish a *private*
   package, so this must be set explicitly.
3. **No paid GitHub features.** GitHub Advanced Security on private repos,
   larger/GPU hosted runners, Copilot in CI, and GitHub Models are all off the
   table. CodeQL is free on public repos — keep it there.
4. **No paid SaaS in the critical path.** Observability, registries, secret
   stores, error tracking, and similar must be self-hosted or free-tier. (The
   fleet already self-hosts Langfuse and Vaultwarden — keep that pattern.)
5. **Licences.** Third-party code and container base images must carry an
   OSI-approved / permissive licence. No source-available-but-commercial,
   no "free for non-commercial only" terms.
6. **Exception.** LLM inference for agents (model API credits) is the only
   permitted paid dependency. If any other paid dependency is genuinely
   unavoidable, it must be raised with the operator and recorded here before
   adoption — never introduced silently.

## Enforcement

- New/changed repos: a repo that adds a workflow must satisfy rule 1 (public
  **or** `runs-on: self-hosted`) and rule 2 (public package or self-hosted
  registry) before the workflow is enabled.
- Periodic audit: enumerate private repos with Actions workflows and private
  GHCR packages; each must have a remediation (make public, or move to a
  self-hosted runner/registry) or an explicit, recorded exception.

## Audit — 2026-07-24

Snapshot at the time this standard was written. The **core deployable fleet is
already compliant**; the outstanding items are private repos and (pending
verification) private packages.

**Compliant (public → free Actions + CodeQL):** `robotsix-central-deploy`,
`robotsix-chat`, `robotsix-mill`, `robotsix-llmio`, `robotsix-standards`, and
the other public repos. Their CI is free and does not stop when credits run
out.

**Non-compliant — private repos running paid Actions** (private + GitHub-hosted
= paid minutes). Actively consuming minutes (ran on 2026-07-24):

| Repo | Workflows | Last run | Remediation |
|---|---|---|---|
| `robotsix-invest` | 3 (incl. `ci.yml`, `docker-release.yml`) | 2026-07-24 | Make public, **or** `runs-on: self-hosted`; make its GHCR image public |
| `robotsix-website` | 4 | 2026-07-24 | Make public, or self-hosted runner |
| `hexarchy` | 3 | 2026-07-24 | Make public, or self-hosted runner |

Dormant private repos with workflows (not currently burning minutes, but would
if reactivated): `robotsix-agent-comm` (last 2026-07-04), `robotsix-project`
(2026-05-17), `robotsix-cai` (2026-05-05), `claude-auto-tune-hub`,
`claude_auto_tune`, `ls2n_ros2_ws` (all ~2026-04). Remediate before reuse.

**Private GHCR packages (to verify + fix).** central-deploy added authenticated
pulls for *private* images (PR #549), so at least one fleet image is a private
(metered) package. Private-package egress is billed and the deploy server pulls
on every release. Action: set the fleet's container packages to **public**
visibility (repo Settings → Packages), or stand up a self-hosted registry.
Auditing exact package visibility needs a token with `read:packages`.

**Recommended free replacements**

- **Private-repo CI → self-hosted GitHub Actions runner** on the fleet server:
  unlimited free minutes while the repos stay private. Lowest-friction, no
  visibility change.
- **Or make the repos public** where the code can be public → free Actions +
  CodeQL + public GHCR, nothing to maintain.
- **Private images → public packages** (free pulls, no egress metering).
