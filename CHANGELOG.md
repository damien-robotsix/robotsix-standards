<!-- towncrier release notes start -->

## 0.0.0 (unreleased)

- New standard: [HTTP error envelope](docs/http-error-envelope.md) — every deployable component with an HTTP API returns errors through one consistent RFC 9457 `application/problem+json` envelope registered via centralized exception handlers.
- **Python CI:** require `enable-cache: true` and `cache-dependency-glob` on `astral-sh/setup-uv` v6+ in every CI job that calls it.  Release/deploy workflows may opt out.  Pre-commit jobs additionally cache `~/.cache/pre-commit` via `actions/cache@v4`.
- Amend config standard with management-surface secret-handling rules:
  redact `writeOnly` fields on read, merge-on-write for partial updates,
  and masked UI inputs with set/unset badge.
- Gate 3 verification text in `security-posture.md` now references the
  language-specific Dependabot ecosystem (`uv` for Python repos) alongside
  `npm`, matching the `repo-baseline.md` table.
- Clarify content-only repo secret-protection scope: push-protection + detect-secrets required, TruffleHog full-history scan exempt (consistent with the zizmor exemption rationale)
- Add `.markdownlint.yaml` config relaxing MD013 (line-length), MD060
  (compact tables), MD004 (ul-style false-positive), and MD046
  (code-block-style vs MkDocs admonitions) to match existing doc conventions,
  plus fix 7 true violations: MD028 (blank line inside blockquote) in
  `deploy-contract.md`, MD051 (link fragment) in `repo-baseline.md`, and
  MD031/MD040 (fence language / trailing content) in `ros2.md`.
- Add Docstring convention and Security posture to the README "Every repository" table,
  and Docstring convention to the docs/index.md TOC.
- Ignore self-referencing `damien-robotsix.github.io/*` URLs in htmlproofer to prevent CI failures from 504 responses during docs build.
- Add docstring convention standard (`docs/docstrings.md`) mandating Google-style docstrings fleet-wide, with ruff pydocstyle rule list (`D100`, `D101`, `D103`, `D400`, `D412`, `D413`, `D414`, `D417`) and `convention = "google"`, backed by a rationale documenting mkdocstrings' silent-drop failure mode on NumPy-style docstrings.
- Add `https://owasp.org/*` to htmlproofer ignore_urls in mkdocs.yml to
  prevent transient OWASP server timeouts from failing CI builds.
- Add "Required approving review" to the branch-protection baseline in `docs/repo-baseline.md`.
- Branch protection standard now requires **Include administrators** (`enforce_admins: true`) and documents the emergency bypass process.
- `repo-baseline.md`: mention `uv audit` alongside `pip-audit` in the CVE audit bullet, matching the two-pass description in `python.md`.
- Content-only repos are now exempt from the zizmor workflow audit (gate 4b), in addition to the existing code-analysis exemptions. SHA-pinning and least-privilege permissions still apply.
- Acknowledge content-only repo pre-commit hook subset in `docs/python.md`. Content-only repos may omit ruff, ruff-format, mypy, vulture, and hadolint; the standard set is for repos that ship Python packages.
- Require `SECURITY.md` in the repo baseline with vulnerability disclosure policy (contact method, response time, coordinated disclosure). Add a reference implementation to this repo and an audit row to the security posture table.
- Add OWASP Top 10 for LLM Applications security guidance to the LLM usage section in `component-standard.md`: prompt injection defences (LLM01), excessive-agency least-privilege rules (LLM06), output sanitisation requirements (LLM02), and forward guidance for LLM08/LLM09.
- Added zizmor workflow audit to the canonical security gate list in `repo-baseline.md`.
- `security-posture.md`: add exemption for content-only repos (no `src/`, no container image) from code-analysis gates (CodeQL, dependency-review, SBOM, CVE audit). Workflow-hardening, secret-protection, and Dependabot gates still apply.
- Added CodeQL reference to `python.md` "Lint, types, and security lint" section, so Python developers see the required SAST gate alongside ruff, bandit, and uv audit. (mill: python.md: reference CodeQL as a required security gate (20260718T000301Z-python-md-reference-codeql-as-a-required-8501))
- Added [security posture](docs/security-posture.md) standard — a consolidated, auditable checklist of self-enforcing security gates (CodeQL, dependency review, Dependabot, workflow hardening, secret push protection, SBOM) replacing the per-repo periodic security audit agent.
- Add bespoke security-posture-audit mill agent that audits the standards'
  security definitions for completeness, internal consistency, currency
  against OWASP/OpenSSF/SLSA, and enforceability. Document the agent in
  `docs/mill-agents.md`.
- Add `.robotsix-mill/config.yaml` with `languages: [markdown]` to activate the periodic mill agents for this docs repo.
- Fixed 17 broken external URLs across the fleet table, deploy-contract page, integrating-a-service guide, and ROS 2 practices page; replaced unresolvable docs-site links and custom-domain URLs with GitHub repository links that resolve correctly.
- Add `mkdocs-htmlproofer-plugin` to validate external links during the docs build. Broken external URLs now fail the build (via `--strict`), with `localhost` and GitHub raw URLs excluded from checking.
- CHANGELOG.md: remove stale duplicated '0.0.0 (unreleased)' block between 0.1.3 and 0.1.2 sections; add towncrier `start_string` marker to prevent recurrence. (20260717T173132Z-changelog-md-remove-stale-0-0-0-unreleas-8151)
- README: add direct link to the published docs site (`damien-robotsix.github.io/robotsix-standards`). (20260717T173132Z-readme-add-the-required-docs-site-link-p-164f)

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


