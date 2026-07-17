# robotsix-standards 0.1.3 (2026-07-13)

## Changed

- entrypoint-contract.md: mill example cites outdated root rationale (socket-group-join, not volume reconciliation) (20260711T070827Z-entrypoint-contract-md-mill-example-cite-93f5)
- CHANGELOG.md: stale duplicated '0.0.0 (unreleased)' block below released sections (20260711T070831Z-changelog-md-stale-duplicated-0-0-0-unre-fb58)
- chat-access-standard missing from 'Deployable components' tables in README.md and docs/index.md (20260711T070834Z-chat-access-standard-missing-from-deploy-bc35)
- ROS 2 practices page/template promised in repo-baseline.md but still absent (20260711T070838Z-ros-2-practices-page-template-promised-i-6e43)
- Reconcile documented claude-auth mount target (/home/app/.claude) vs central-deploy's actual injection (/root/.claude) (20260711T070842Z-reconcile-documented-claude-auth-mount-t-01c1)
- Remove Python-specific uv references from repo-baseline.md (uv belongs only in python.md); verify 'uv audit' is a real CVE gate (20260711T070846Z-remove-python-specific-uv-references-fro-30a6)
- docs: add exception for programmatic CHANGELOG.md fixes (changelog-bugfix carve-out) (20260712T175522Z-docs-add-exception-for-programmatic-chan-85f0)
- Derive a ROS 2 practices page for robotsix-standards from mill-ros2 (20260712T232045Z-derive-a-ros-2-practices-page-for-robots-d71c)


## 0.0.0 (unreleased)

- Enable three weekly mill periodic workflows: `audit` (doc completeness/structure), `copy_paste` (jscpd duplicate detection), and `repo_description_sync` (forge description sync, interval overridden to 1w).
- Filled in the ROS 2 practices page (`docs/ros2.md`): workspace-skeleton layout, vcs2l manifest, devcontainer conventions, supported distros, build & test pipeline, CI expectations, code style & linting, and interface design guidelines — all derived from `robotsix-mill-ros2`.
- Added explicit exception to the "CHANGELOG.md is written only by the release workflow" rule: a programmatic tool fixing a bug in CHANGELOG.md itself may write to it directly, and only for that fix.
- Clarify the `claude-auth` mount target in the docker standard: `/home/app/.claude` is the only valid target for standard `app`-user containers; there is no `/root/.claude` variant (containers run as uid 1000 with home `/home/app`, so `/root` is neither accessible nor meaningful).
- Removed all Python-specific `uv` references from the language-agnostic `repo-baseline.md`; consolidated `uv` Dependabot ecosystem and SHA-pin rules into `python.md`.
- Add chat-access standard to the deployable components tables in README.md and docs/index.md.
- Landed stub ROS 2 practices page (`docs/ros2.md`) and linked it from the repo baseline — resolves a dangling promise that had been "being derived" across several review rounds.
- entrypoint-contract: update mill example rationale from stale socket-group-join
  to volume-ownership reconciliation + ulimit raise; relabel socket-group-join
  as legacy direct-mount branch.
- Deploy contract: specify volume-ownership responsibility — deployer guarantee (writable-by-uid on first creation) and component obligation (no image-side mkdir/chown reliance; log persistence paths at startup).
- Switched docs deployment from `actions/deploy-pages` (Pages Actions API) to `peaceiris/actions-gh-pages` (branch-based) to work around persistent "Deployment failed, try again later" errors from the GitHub Pages API. Requires the repo's Pages source to be set to "Deploy from a branch" (branch: `gh-pages`).
- Revert docs deployment to self-contained workflow; the shared python-docs
  reusable workflow's deploy job, though correctly configured for Pages
  Actions, causes deploy-pages to return "Deployment failed, try again
  later" when called from this repo.
- New standard: [Chat access standard](docs/chat-access-standard.md) — how a fleet component makes itself operable by the chat agent (robotsix-chat) via `GET /chat-skill` + `robotsix.deploy.chat-access` label. Cross-linked from component-standard and integrating-a-service checklist.
- Document python-security.yml's actual gate contents (SBOM, TruffleHog) in the security gate list

# robotsix-standards 0.1.2 (2026-07-06)

## Changed

- Baseline self-conformance sweep: standard pre-commit set (docs-repo
  subset), shared baseline-check and dependabot-auto-merge callers, docs
  deploy via the shared python-docs workflow (stale gh-deploy justification
  removed), and a towncrier-ignored `.gitkeep` so `changelog.d/` survives
  releases that consume every fragment. (20260704T000500Z-baseline-conformance-sweep)
- chat-access standard: /chat-skill endpoint, chat-access label, roster trust model (20260704T001648Z-chat-access-standard-chat-skill-endpoint-e0a5)
- CI failure: Docs on main (20260704T083125Z-ci-failure-docs-on-main-668e, 20260704T093015Z-ci-failure-docs-on-main-9c8e, 20260703T234007Z-ci-failure-docs-on-main-1baa)
- Update stale comment in ci.yml: deployment no longer uses shared python-docs workflow (20260704T090010Z-update-stale-comment-in-ci-yml-deploymen-1de6)
- dependency-review gate: align the documented `fail-on-severity` to `moderate`
  (what the fleet's strictest deployment, robotsix-chat, already enforces) —
  supersedes the previous `high`. (20260704T091500Z-dependency-review-severity-moderate)
- fleet page: robotsix-chat one-liner aligned with its README ("Browser + SSE
  chat server exposing an LLM agent to human users") per the README-skeleton
  agreement rule. (20260704T093000Z-fleet-chat-oneliner)
- deploy contract: specify named-volume ownership guarantee (deployer chowns to runtime uid on creation) (20260704T131022Z-deploy-contract-specify-named-volume-own-2def)
- CI failure: Auto Release on main (20260703T234004Z-ci-failure-auto-release-on-main-2aa9)


# robotsix-standards 0.1.1 (2026-07-03)

## Changed

- Third standards-review round: one fleet-wide coverage floor (80, shared-workflow-enforced, fleet-wide raises only), branch-protection standard, `robotsix-template-python` starting point, gate-completeness principle, `robotsix.deploy.stateful` flag removed (backups are the operator's concern), modules.yaml scoped to mill-managed repos, config-standard YAML transition notes closed (clean cutover, old YAML paths deleted), repo self-conformance (dependabot, towncrier, `requires-python >=3.14`). (20260703T120000Z-third-review-round)
- Fourth standards-review round: one health endpoint (`GET /health`, liveness only), `/data` as the fleet data mount, Python project-layout section, docs publishing declarative + fleet index page, `<name>_url` service-wiring convention, volumes-only rule (no host bind mounts; claude auth via the managed `claude-auth` volume with dashboard login — closes the host-`~/.claude` design after the 2026-07-03 outage), broker (agent-comm) deprecated fleet-wide. (20260703T130000Z-fourth-review-round)
- Fifth standards-review round: host-wide container log rotation (json-file max-size/max-file, central-deploy host setup), default memory limits for managed components, offline-by-default tests with the `live` marker convention, sibling-resilience rules (start without dependencies, fail per-operation), and a consistency sweep (APP_UID override vestige removed, stale vitest-ratchet wording, fleet page linked from README/index). (20260703T140000Z-fifth-review-round)
- Sixth standards-review round: standards evolution goes through the mill (robotsix-standards board registered), "Retiring a repo" process codified from the broker decommission, README skeleton, UTC-everywhere timestamps, LLM usage standard (llmio capability levels as config fields, fleet-global level-to-model tier mapping via central-deploy), ROS 2 practices page commissioned, audit-gap tickets (robotsix-config alignment, board-agent dependabot). (20260703T150000Z-sixth-review-round)
- Tracing: one Langfuse project per repo/function — main function traces to `<repo>`, each LLM-generating subsystem to its own `<repo>-<function>` project with its own `SecretStr` credentials; every project's keys registered in cost-monitor's `projects.yaml` alongside the OpenRouter key that funds it (closes #15). (20260703T160000Z-langfuse-project-per-function)
- Document python-security.yml's actual gate contents (SBOM, TruffleHog) in the security gate list (20260703T223709Z-document-python-security-yml-s-actual-ga-5938)
- Wire this repo to its own release standard: call the shared auto-release
  workflow (weekly + on-demand) and the shared changelog-check gate in CI. (20260703T231741Z-wire-auto-release-and-changelog-gate)


