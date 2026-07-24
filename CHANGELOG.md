<!-- towncrier release notes start -->
<!-- markdownlint-disable MD013 MD025 MD024 -->

# robotsix-standards 0.1.4 (2026-07-20)

## Changed

- security-posture.md: add exemption for content-only / docs-only repos (20260718T000300Z-security-posture-md-add-exemption-for-co-60f0)
- component-standard.md: address OWASP Top 10 for LLM Applications (20260718T000301Z-component-standard-md-address-owasp-top-ff59)
- python.md: reference CodeQL as a required security gate (20260718T000301Z-python-md-reference-codeql-as-a-required-8501)
- repo-baseline.md: add zizmor to the canonical security gate list (20260718T000301Z-repo-baseline-md-add-zizmor-to-the-canon-20d0)
- Standards: require a vulnerability disclosure policy (SECURITY.md) (20260718T000301Z-standards-require-a-vulnerability-disclo-a0bb)
- Standardize: Python coverage CI configuration (20260720T004009Z-standardize-python-coverage-ci-configura-6da8)
- python.md: acknowledge content-only pre-commit subset or cross-reference exemption (20260718T070514Z-python-md-acknowledge-content-only-pre-c-4450)
- repo-baseline.md: mention `uv audit` alongside `pip-audit` in the CVE audit line (20260718T070514Z-repo-baseline-md-mention-uv-audit-alongs-bdbd)
- security-posture.md: clarify whether zizmor (gate 4b) applies to content-only repos (20260718T070514Z-security-posture-md-clarify-whether-zizm-f0ff)
- repo-baseline.md: require approving PR review before merge (OpenSSF Scorecard Code-Review) (20260718T073149Z-repo-baseline-md-require-approving-pr-re-3beb)
- repo-baseline.md: require branch protection to include administrators (OpenSSF Scorecard Branch-Protection) (20260718T073150Z-repo-baseline-md-require-branch-protecti-618e)
- component-standard.md: address OWASP Top 10:2025 A10 — Mishandling of Exceptional Conditions (20260720T084744Z-component-standard-md-address-owasp-top-47a6)
- dependabot-auto-merge.yml: add top-level `permissions:` block (gate 4c) (20260718T113441Z-dependabot-auto-merge-yml-add-top-level-acbc)
- Standardize: consistent JSON error envelope (RFC 9457 problem+json) for HTTP services (20260719T140417Z-standardize-consistent-json-error-envelo-25c1)
- Codify Google-style docstrings + pydocstyle ruff enforcement as a fleet standard (20260718T144633Z-codify-google-style-docstrings-pydocstyl-6008)
- ci_fix: out-of-scope CI failure — htmlproofer (mkdocs build --strict) in Either add the OWASP URL to the ignore_urls list in mkdocs.yml under the htmlproofer plugin config, or replace the link with a working alternative. (20260718T145428Z-ci-fix-out-of-scope-ci-failure-htmlproof-4015)
- CI failure: CI on main (20260718T154018Z-ci-failure-ci-on-main-e8d2)
- Standardize: Hypothesis property-based testing profile convention (20260719T161521Z-standardize-hypothesis-property-based-te-bfaf)
- Enable weekly mill periodics: audit, copy_paste, repo_description_sync (20260717T172503Z-enable-weekly-mill-periodics-audit-copy-cbec)
- CHANGELOG.md: remove stale `0.0.0 (unreleased)` block duplicated below 0.1.3 (20260717T173132Z-changelog-md-remove-stale-0-0-0-unreleas-8151)
- CI: add an external link checker to the docs build gate (20260717T173132Z-ci-add-an-external-link-checker-to-the-d-7d54)
- README: add the required docs-site link per the repo-baseline README skeleton (20260717T173132Z-readme-add-the-required-docs-site-link-p-164f)
- pre-commit: add markdownlint and codespell for the docs-only repo (20260718T173718Z-pre-commit-add-markdownlint-and-codespel-07ef)
- README + index: add Docstring convention page to the 'Every repo' TOC listings (20260718T173719Z-readme-index-add-docstring-convention-pa-35e6)
- README: add missing Hypothesis testing and HTTP error envelope to TOC tables (20260719T174239Z-readme-add-missing-hypothesis-testing-an-be2a)
- ci_fix: out-of-scope CI failure — docs / Lint markdown (markdownlint-cli2) in docs/*.md and README.md — fix pre-existing markdownlint violations or adjust .markdownlint.yaml to match existing doc conventions (20260718T174618Z-ci-fix-out-of-scope-ci-failure-docs-lint-2806)
- ci_fix: out-of-scope CI failure — htmlproofer (external link checker in mkdocs build) in docs/deploy-contract.md, docs/fleet.md, docs/integrating-a-service.md, docs/ros2.md — fix or remove the 13 broken external URLs (20260717T174800Z-ci-fix-out-of-scope-ci-failure-htmlproof-6c0a)
- robotsix-standards: Create .robotsix-mill/config.yaml to activate existing periodic agents (20260717T191557Z-robotsix-standards-create-robotsix-mill-ce12)
- Standard: deployment engine code must be repo-agnostic; service definitions are declarative data (20260719T191817Z-standard-deployment-engine-code-must-be-fa2b)
- security-posture.md: clarify whether content-only repos must run TruffleHog (20260718T212027Z-security-posture-md-clarify-whether-cont-3cca)
- security-posture.md: gate 3 verification text omits `uv` ecosystem (20260718T212027Z-security-posture-md-gate-3-verification-d480)
- Amend config-standard.md: secrets as SecretStr in single config.json with redact-on-read / merge-on-write semantics (20260718T213116Z-amend-config-standard-md-secrets-as-secr-3f9f)
- component-standard.md: update OWASP LLM Top 10 numbering to v2.0 and address new entries (20260719T224559Z-component-standard-md-update-owasp-llm-t-e608)
- security-posture.md: update SLSA reference from v1.0 to v1.2 and address Source Track (20260719T224559Z-security-posture-md-update-slsa-referenc-d9bf)
- Define security posture requirements as an auditable standard (20260717T233031Z-define-security-posture-requirements-as-590f)
- Add custom audit agent for security aspects of the standards definitions (20260717T233343Z-add-custom-audit-agent-for-security-aspe-7ef2)
- Standardize: enable uv cache in all CI jobs using astral-sh/setup-uv (20260718T235556Z-standardize-enable-uv-cache-in-all-ci-jo-9993)

## 0.0.0 (unreleased)

- Enable `health` periodic workflow for inspecting repository health across eight dimensions (staleness, label hygiene, CI health, dependency freshness, etc.)
- Add `docstring_coverage` periodic workflow to scan Python source modules for missing docstrings and propose draft tickets.
- **Resolved secret-handling contradiction** between `config-standard.md` and `config-ownership.md`. Secrets follow the one-file convention (`SecretStr` in `config.json`) defined in the config standard; `config-ownership.md` now defers to it with an explicit cross-reference.
- Fix capitalization of "TruffleHog" in `docs/scorecard.md` intro paragraph.
- Updated `docs/scorecard.md` to replace stale security-tool references: "CodeQL" → "Semgrep" (fleet SAST standard) and "gitleaks" → "detect-secrets" (fleet secret-scanning pre-commit), and reworded the SARIF-upload sentence to avoid implying CodeQL is an active fleet tool.
- Add `@pytest.mark.parametrize` standard to `docs/python.md` Tests section: prefer parametrized tests over N separate test functions when testing a single function with multiple input/output variants.
- Add `https://genai.owasp.org/*` to htmlproofer `ignore_urls` in `mkdocs.yml`, extending the existing OWASP timeout workaround to cover the `genai.owasp.org` subdomain (OWASP Top 10 for LLM & Agentic Applications pages).
- New [config ownership](docs/config-ownership.md) standard: draws a hard line between deploy-plane config (central-deploy UI — image, volumes, ports, secrets, restart, resource limits, `ROBOTSIX_CONFIG_FILE`) and component-owned config (the component's own `config/config.json` and HTTP surface). Defines the standard config HTTP surface every component MUST implement: `GET /config`, `PUT /config`, `GET /config/versions`, `POST /config/rollback` — with typed request/response shapes, secret masking, and validation rules. UI-bearing components MUST additionally provide a Settings/Config panel built on that surface.
- **Python standard:** `strict_markers = true` is now mandatory in `[tool.pytest.ini_options]` — catches misspelled markers as hard errors instead of silent no-ops.
- New standard: [HTTP security response headers](docs/http-security-headers.md) — every deployable component that serves HTTP must emit the OWASP security headers via the `secure` library's `SecureASGIMiddleware` (Preset.BALANCED baseline), replacing hand-rolled per-service headers.
- Added "Coverage artifact upload" rule to the CI and security gates section of the repo baseline: any reusable workflow that runs pytest with `--cov` must upload `coverage.xml` and `.coverage` as a `coverage-data` artifact, so consuming workflows can generate coverage diff commentary without re-running tests.
- Add "Mypy: type-check tests" section to the Python practices standard, requiring CI to run mypy on both `src/` and `tests/` with a `module = "tests.*"` override that relaxes `disallow_untyped_defs` while keeping `check_untyped_defs`, and mandating `tests/__init__.py` so the override matches.
- Fixed `docs/scorecard.md` intro paragraph: replaced CodeQL with Semgrep and removed gitleaks from the parenthetical tool list, matching the actual fleet security stack documented in `security-posture.md`.
- New [Ruff lint rules](docs/ruff-lint-rules.md) standard: Tier 2 rule families (ARG, C4, PERF, PT) for every Python repo, with per-file ignores and the PT006 exclusion.
- Add CI gate (`scripts/check-toc-sync.py`) that verifies mkdocs.yml nav pages
  appear in README.md and docs/index.md, preventing TOC drift.
- Added **Changelog nav page** rule to [MkDocs build integrity](docs/mkdocs-build.md): every fleet repo that publishes an MkDocs site and maintains a `CHANGELOG.md` must surface it in the docs `nav` via a symlink or build-time copy hook — no committed duplicate copy.
  This repo now follows the rule: `docs/hooks.py` copies and link-rewrites the root `CHANGELOG.md` at build time, and `mkdocs.yml` lists it under a top-level **Changelog** nav entry.
- **Docstring convention:** corrected the D105/D107 suppression rationales (D105 is magic methods, D107 is `__init__`), and replaced the `docs/**` per-file-ignore with `*__init__.py` = ["D104"] so package docstrings are per-file suppressed instead of blanket-ignoring docs prose.
- OpenSSF Scorecard standard: every deployable component must publish a
  Scorecard workflow (weekly cron + push-to-main, SARIF upload, minimal
  permissions), targeting ≥ 7/10. Closes the gap between per-gate security
  posture checks and an independent outside-in supply-chain audit.
- README "Every repository" table: added rows for Markdown linting and MkDocs build integrity standards, bringing the table into sync with `mkdocs.yml` and `docs/index.md`.
- New [MkDocs build integrity](docs/mkdocs-build.md) standard: every fleet repo that publishes an MkDocs site must build with `--strict` and include a `validation:` block that promotes link and anchor checks to errors. Documents the known limitation with mkdocstrings autorefs.
- Add `advanced` boolean flag to the config schema standard — a per-setting annotation
  (default `false`) that lets the deploy UI hide rarely-changed settings behind a
  "Show advanced settings" toggle. The flag is purely presentational and backward
  compatible: schemas without it render identically to before.
- Updated [docstring convention](docs/docstrings.md) enforcement section to use `extend-select = ["D"]` (full pydocstyle rule set), added standard ignore list (`D105`, `D107`, `D205`, `D415`), and added per-file-ignores for `tests/` and `docs/` — matching the pattern already proven in pydantic.
- .github/dependabot.yml: removed duplicate old Dependabot entries so the file contains only the three standardized grouped configurations
- Added **Agentic Applications** security subsection to `docs/component-standard.md`, mapping the fleet's existing controls to the [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) and explicitly addressing agent-to-agent propagation, unbounded agentic consumption, and over-reliance on agentic decisions.
- Add "Exception hierarchy" convention to Python standard: every package
  defines a root `<Package>Error` base class, all domain exceptions
  subclass it, and the root is importable from the top-level namespace.
- Updated SAST tooling example in `docs/security-posture.md` from CodeQL to Semgrep to match the fleet's current standard (PR #83).
- Replace GitHub Code Scanning (proprietary CodeQL) with open-source Semgrep as the fleet SAST standard. Findings are published as workflow artifacts and surfaced through the fleet dashboard — no dependency on the GitHub Security tab or `security-events: write` permission. Updates docs/security-posture.md, docs/docker-standard.md, docs/python.md, docs/repo-baseline.md, docs/mill-agents.md, and the security-posture-audit agent.
- Codified open-source-preferred tooling policy in security posture standard — fleet actively prefers OSS security tools (auditability, no license keys, reproducibility) over proprietary alternatives.
  Selected `detect-secrets` (pre-commit) + `TruffleHog` (CI) as the fleet-wide secret-scanning stack with documented rationale; Gitleaks Enterprise/licensed path explicitly rejected.
- Add [Markdown linting](docs/markdown-linting.md) standard: markdownlint-cli2 and codespell
  pre-commit hooks for every Python repo that publishes MkDocs documentation,
  with recommended `.markdownlint-cli2.yaml` and `[tool.codespell]` configs.
- Remove archived `robotsix-board-agent` from the fleet Deployable components table in `docs/fleet.md`.
- Add content-only repo exemption notes to the security-posture audit table, so readers who consult only the table see which gates apply to docs-only repos.
- Add **Error handling** section to the component standard, addressing OWASP A10:2025 (Mishandling of Exceptional Conditions). Requires a `debug` boolean config flag (default `false`) to control verbose error output, mandates framework debug mode be driven from config, and requires exception-message sanitisation for both HTTP responses and LLM model prompts.
- Standardise Python coverage configuration: codify the full `[tool.coverage]` block (`source = ["src"]`, `branch = true`, `relative_files = true`, `parallel = true`, `fail_under = 80`, `show_missing = true`, `[tool.coverage.paths]`) in `docs/python.md`.  Codecov upload is documented as an optional enhancement; the fleet default is terminal + artifact reporting.
- Add SLSA v1.2 Source Track posture to `docs/security-posture.md`: Source L1 and L3 are met, L2 (signed source provenance) is a gap, L4 (two-person review) is deferred. Also updates the gate-6 SLSA link from v1.0 to v1.2.
- Update LLM security section to OWASP Top 10 for LLM Applications v2.0 (v2025): rename LLM02→LLM05 (Improper Output Handling), add LLM02 (Sensitive Information Disclosure), LLM03 (Supply Chain), and LLM07 (System Prompt Leakage) entries.
- Codify "deployment engine code must be repo-agnostic" in `docs/deployment-system.md`:
  service definitions belong in declarative data (onboarding API, config dicts,
  per-component flags), never in engine code. Updated `AGENT.md` with the rule.
- Add missing Hypothesis testing and HTTP error envelope entries to the README tables so they stay in sync with the `mkdocs.yml` nav and `docs/index.md` TOC.
- New [Hypothesis testing](docs/hypothesis.md) standard — property-based testing
  profiles (CI vs dev), shared strategies module, and CI workflow integration
  for fleet repos that use Hypothesis.
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
- Add `markdownlint-cli2` and `codespell` pre-commit hooks and CI gates to
  lint and spell-check all Markdown documentation.
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
