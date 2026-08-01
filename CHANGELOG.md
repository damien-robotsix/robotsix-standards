
<!-- towncrier release notes start -->

# robotsix-standards 0.2.0 (2026-07-27)

## Added

- Add the **Free-tier-only (no paid services)** standard: the fleet runs on free/OSS
  tooling only — the sole permitted paid dependency is LLM agent inference. Codifies
  that Actions must run on a free tier (public repo or self-hosted runner, never
  private + GitHub-hosted paid minutes), container images must be public packages or
  self-hosted, and no paid GitHub features (Advanced Security on private, larger
  runners, Copilot, Models). Includes a 2026-07-24 audit: the core deployable fleet
  is compliant; private repos `robotsix-invest`/`robotsix-website`/`hexarchy` run
  paid Actions and need remediation. (20260724T152735Z-add-free-tier-only-standard)

## Changed

- Standardize: Ruff high-signal lint rules (SIM, C4, LOG, G, ERA, PGH, RUF, selective PT) (20260725T001924Z-standardize-ruff-high-signal-lint-rules-9975)
- docs/security-posture.md: update CodeQL→Semgrep in tooling-policy parenthetical (line 60) (20260721T002037Z-docs-security-posture-md-update-codeql-s-d6c9)
- Standardize: each robotsix package exposes a single root exception base class (20260721T002604Z-standardize-each-robotsix-package-expose-aad0)
- Fleet-wide config-ownership audit: classify every component's settings (deploy-plane vs component-owned) and file per-component remediation tickets (20260727T002909Z-fleet-wide-config-ownership-audit-classi-1494)
- component-standard.md: address OWASP Top 10 for Agentic Applications 2026 (20260721T003222Z-component-standard-md-address-owasp-top-04df)
- Standard + fleet audit: no paid/licensed or GitHub-billed CI workflows in the fleet (20260725T011049Z-standard-fleet-audit-no-paid-licensed-or-d15b)
- Standardize: Dependabot configuration for Python/uv repos (20260721T012858Z-standardize-dependabot-configuration-for-1d99)
- Standardize: reusable CI workflows MUST upload coverage artifacts for downstream consumption (20260723T013124Z-standardize-reusable-ci-workflows-must-u-94ad)
- Standardize: surface CHANGELOG.md as a Changelog page in the MkDocs docs nav (20260722T020728Z-standardize-surface-changelog-md-as-a-ch-7a3b)
- config-standard.md and config-ownership.md conflict on secret handling model (20260724T021917Z-config-standard-md-and-config-ownership-2afb)
- robotsix-standards: Enable survey periodic workflow (20260725T022915Z-robotsix-standards-enable-survey-periodi-edac)
- Standardize: type-check Python tests in CI with relaxed mypy per-module overrides (20260723T025656Z-standardize-type-check-python-tests-in-c-901c)
- robotsix-standards: Enable health periodic workflow (20260724T031444Z-robotsix-standards-enable-health-periodi-35bd)
- Adopt Vale prose linting with write-good style and custom robotsix vocabulary (20260725T040731Z-adopt-vale-prose-linting-in-robotsix-sta-4a1d)
- Standardize: Prose linting with Vale for all MkDocs documentation repos (20260725T040731Z-standardize-prose-linting-with-vale-for-d8a7)
- Add Prose linting to mkdocs.yml nav (20260725T041837Z-add-prose-linting-to-mkdocs-yml-nav-bc15)
- Add Vale hooks to .pre-commit-config.yaml (20260725T043020Z-add-vale-hooks-to-pre-commit-config-yaml-95fd)
- Standardize: pass --show-diff-on-failure to pre-commit in CI (20260724T044007Z-standardize-pass-show-diff-on-failure-to-4eef)
- Make two settings-ownership rules explicit invariants in config-ownership.md (20260726T094105Z-make-two-settings-ownership-rules-explic-982a)
- Standardize: Google-style docstrings with ruff D (pydocstyle) rule enforcement (20260721T101529Z-standardize-google-style-docstrings-with-9ac1)
- Add "advanced" flag to component JSON config schema to hide advanced settings behind a UI toggle (20260721T114015Z-add-advanced-flag-to-component-json-conf-dc7f)
- Standardize: generate and publish a CycloneDX SBOM on every fleet release (20260724T122420Z-standardize-generate-and-publish-a-cyclo-047e)
- scorecard.md: intro paragraph misattributes CodeQL and gitleaks to fleet security stack (20260723T124003Z-scorecard-md-intro-paragraph-misattribut-b21d, 20260723T222550Z-scorecard-md-intro-paragraph-misattribut-8ba4)
- Define config-ownership standard: deploy-plane vs component-owned configuration (20260723T125618Z-define-config-ownership-standard-deploy-e8df)
- Standardize: OS test matrix + POSIX-call guards for fleet libraries doing filesystem I/O (20260725T130720Z-standardize-os-test-matrix-posix-call-gu-8472)
- Standardize: HTTP security response headers for web/HTTP-serving services (20260723T131505Z-standardize-http-security-response-heade-9cf5)
- Standardize the default-config location convention for deployable repos (20260724T132832Z-standardize-the-default-config-location-774c)
- security-posture.md: Gate 1 (SAST) omits Bandit — the Python SAST layer (20260724T134050Z-security-posture-md-gate-1-sast-omits-ba-4b84)
- Standardize: pytest strictness config (filterwarnings=error, --strict-markers/--strict-config, xfail_strict) for Python repos (20260724T142408Z-standardize-pytest-strictness-config-fil-0886)
- robotsix-standards: Enable completeness_check periodic workflow (20260724T144020Z-robotsix-standards-enable-completeness-c-2b7a)
- Add config-ownership.md to mkdocs.yml navigation sidebar (20260724T160746Z-add-config-ownership-md-to-mkdocs-yml-na-9564)
- Standardize: async SQLAlchemy three-layer test fixture pattern (engine → connection → db_session) (20260724T161109Z-standardize-async-sqlalchemy-three-layer-9f96)
- ci_fix: out-of-scope CI failure — htmlproofer external URL check (HTTP 504)
  in docs/fleet.md, docs/repo-baseline.md, docs/security-posture.md
  (or htmlproofer config in mkdocs.yml) — all outside this ticket's diff
  (20260724T163347Z-ci-fix-out-of-scope-ci-failure-htmlproof-c9a1)
- Standardize: MkDocs docs builds run in strict mode with a validation block across fleet repos (20260721T164456Z-standardize-mkdocs-docs-builds-run-in-st-c2eb)
- fleet.md: remove archived `robotsix-board-agent` row from the fleet table (20260720T174834Z-fleet-md-remove-archived-robotsix-board-34ae)
- security-posture.md: add content-only exemption notes to the audit table (20260720T174834Z-security-posture-md-add-content-only-exe-8b6e)
- README: add missing Markdown linting and MkDocs build integrity to 'Every repository' table (20260721T175939Z-readme-add-missing-markdown-linting-and-ddc5)
- CI: add a TOC synchronization gate to catch README/index drift from mkdocs.yml nav (20260721T175940Z-ci-add-a-toc-synchronization-gate-to-cat-9cc1)
- scorecard.md: update stale security-tool references (CodeQL → Semgrep, gitleaks → detect-secrets) (20260722T180054Z-scorecard-md-update-stale-security-tool-1032)
- mkdocs.yml: add genai.owasp.org to htmlproofer ignore_urls to prevent transient OWASP subdomain timeouts from breaking CI (20260723T180844Z-mkdocs-yml-add-genai-owasp-org-to-htmlpr-f9b1)
- Remove docstring_coverage periodic agent from markdown-only repo (20260724T181101Z-remove-docstring-coverage-periodic-agent-306a)
- Re-remove docstring_coverage periodic agent after accidental re-creation (20260725T181536Z-re-remove-docstring-coverage-periodic-ag-4c0d)
- Remove test_gap periodic agent from markdown-only repo (20260725T181536Z-remove-test-gap-periodic-agent-from-mark-1600)
- Standardize: Enable pytest strict_markers = true across all Python repos (20260722T183017Z-standardize-enable-pytest-strict-markers-38ad)
- Standardize: derive package `__version__` from importlib.metadata (single version source, no hard-coded constant) (20260724T185848Z-standardize-derive-package-version-from-672d)
- Standardize: Tier 2 ruff lint rules (ARG, C4, PERF, PT) for all Python repos (20260723T191839Z-standardize-tier-2-ruff-lint-rules-arg-c-7625)
- Standardize: prefer @pytest.mark.parametrize for input/output variation tests (20260723T192932Z-standardize-prefer-pytest-mark-parametri-0c74)
- Standardize: Python Makefile convention for uv projects (20260724T200729Z-standardize-python-makefile-convention-f-919d)
- Propose new rule: deployable components must publish an OpenSSF Scorecard (20260721T210415Z-propose-new-rule-deployable-components-m-ea4b)
- Standardize: pre-commit hook baseline for Python repos (20260724T213908Z-standardize-pre-commit-hook-baseline-for-bd41)
- Standardize: markdownlint-cli2 + codespell in pre-commit for fleet MkDocs repos (20260720T214243Z-standardize-markdownlint-cli2-codespell-f6e0)
- Standardize: Ruff D (pydocstyle) rules with Google convention for Python repos (20260721T220722Z-standardize-ruff-d-pydocstyle-rules-with-0c73)
- robotsix-standards: Enable changelog_autofill periodic workflow (20260723T232803Z-robotsix-standards-enable-changelog-auto-1e57)
- Adopt open-source SAST standard; remove GitHub Code Scanning fleet-wide (20260720T233047Z-adopt-open-source-sast-standard-remove-g-65f3)
- Adopt open-source secret scanning; codify OSS-preferred tooling policy (drop licensed Gitleaks) (20260720T234819Z-adopt-open-source-secret-scanning-codify-8ee9)

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

- Re-add `.robotsix-mill/periodic/docstring_coverage.yaml` periodic config (regression from PR #164).
- Add mkdocs.yml nav registration rule to AGENT.md — new standards pages must be
  registered in the `mkdocs.yml` nav in the same change that adds them, not
  just in README/index TOC entries (the TOC-sync gate is one-directional).
- Remove docstring_coverage and test_gap periodic agents from this markdown-only repo (they were incorrectly re-added by PRs #162/#164)
- Fixed three changelog fragments that were truncated mid-sentence with a literal ellipsis (…), copied from clipped ticket titles. The fragments now end with complete sentences so `towncrier build` will emit valid release notes.
- Fix Dependabot pre-commit update failure: correct `markdownlint-cli2` repo URL from `igorshubovych/markdownlint-cli2` (404) to `DavidAnson/markdownlint-cli2`.
- Make the TOC-sync gate bidirectional: `scripts/check-toc-sync.py` now also
  extracts page references from `README.md` and `docs/index.md` and asserts
  each one is present in the corresponding `mkdocs.yml` nav section. A page
  registered in README + index but absent from the nav now fails CI instead of
  silently dropping out of the built docs site.
- Add "no duplicate rules across standards pages" rule to AGENT.md, requiring cross-links instead of restating rule text in multiple pages.
- Added Docker Compose smoke test requirement to the Docker build & release standard: every deployable component must run a CI job that validates `docker-compose up` succeeds (container starts, health check passes, core endpoint responds) on the `deploy/docker-compose.yml`. Catches compose-file breakage before deploy.
- Added Rule 4 to the MkDocs build integrity standard: new standards pages
  must be registered in `mkdocs.yml` `nav` in the same change that adds the
  page — a `README.md`/`docs/index.md` TOC entry alone leaves the page
  unbuilt.
- Register `fastapi-pydantic-field-descriptions.md` in the mkdocs.yml nav under Deployable components so the page is no longer orphaned from the site build.
- Register `docs/mypy.md` in the mkdocs.yml nav (`Every repo` section) so the Mypy strictness page is reachable from the published docs sidebar.
- Register `fastapi-pydantic-field-descriptions.md` in mkdocs.yml nav under Deployable components.
- Replace redundant CI-invocation rule text in `docs/markdown-linting.md` with a pointer to the canonical `docs/ci-lint-pinning.md`, keeping the two concrete `pre-commit run --all-files` commands as the markdownlint/codespell example.
- New standard: [Mypy strictness as a hard CI gate](docs/mypy.md) — mypy runs as a gate (not advisory), baseline snapshots are a bootstrapping scaffold with a defined exit, and new code must be type-clean under strict mode.
- Added the [FastAPI Pydantic field descriptions](docs/fastapi-pydantic-field-descriptions.md) standard — every public request/response Pydantic model field must carry `Field(description=...)` so the generated OpenAPI schema is self-documenting.
- Codify in `docs/markdown-linting.md` that CI must run markdownlint-cli2 and codespell through the same pinned pre-commit hooks as local development, never via a separate unpinned `npx`/`uv run --with` invocation.
- Standardize: CI lint jobs must run the same version-pinned tools as `.pre-commit-config.yaml` — the pre-commit `rev:` field is the single source of truth, never floating/latest installs. (20260731T134913Z-standardize-ci-runs-the-same-pinned-lint-c651)
- Add dedicated [towncrier changelog](docs/towncrier.md) standard page with the
  canonical `[tool.towncrier]` config, fragment format, CI enforcement, and
  release-step rules for every Python repo.
- **Docker standard:** Added a CI integration tests section requiring every
  deployable component to build its image in CI, verify the entrypoint binary
  exists, and perform a Python import smoke test — catching the build-time
  regressions (missing binaries, broken imports, packaging errors) that the
  image scan alone doesn't catch.
- Strengthened the README standards-link requirement in the repo-baseline standard:
  new repos from the template ship the link by default, and CI verifies it on
  every PR. Added a local `readme-standards-link` job to the baseline-check
  workflow.
- Updated `docs/free-tier-only.md` audit table: `robotsix-standards` entry now lists its five CI workflows instead of the stale "(no workflows — docs repo)" claim.
- Sync `docs/prose-linting.md` vocabulary listings and `.vale.ini` example with the
  actual working config files — add missing `Vocab = robotsix`, update `accept.txt`
  from 18 to 34 terms, and correct `reject.txt` to match `config/vocabularies/robotsix/`.
- **Config ownership standard:** add the verbatim boundary rule (central-deploy retains only lifecycle and Docker-boundary config; rule of thumb: container-recreate → deploy, otherwise → component), replace incremental migration guidance with a one-time config-import adoption contract, and explicitly distinguish non-boot secrets (component-owned, masked by the component) from boot-time secrets (remain with deploy plane).
- Added **Distribution & Packaging** standard: git-based consumption is the preferred path for first-party libraries; public package indexes (npm, PyPI) are disallowed; internal registry (GitHub Packages) is the only acceptable registry alternative; every library README must document its distribution method with exact pin syntax.
- Updated `docs/pre-commit-baseline.md`: bumped example `rev` from `v5.0.0` to `v6.0.0` to match the repo's actual `.pre-commit-config.yaml`, corrected `check-added-large-files` threshold from 750 KB to 1024 KB, and documented the `args` and `exclude` pattern (`uv.lock`, `.secrets.baseline`).
- Added "Workflow permissions" rule to repo-baseline: every `.github/workflows/*.yml` must use `permissions: {}` at the workflow level with scoped per-job `permissions:` blocks (least-privilege pattern).
- Document `check-case-conflict` pre-commit hook in `docs/python.md` file-checks list, matching its presence in `.pre-commit-config.yaml`.
- Fleet-wide config-ownership audit: classify every deployable component against the [config-ownership standard](docs/config-ownership.md), file remediation tickets for `robotsix-auto-mail` and `robotsix-cost-monitor`, and list `robotsix-chat` and `robotsix-calendar-agent` as compliant.
- Add explicit "Two invariants" section to config-ownership page: deploy-plane exclusivity (only non-internalisable settings in the deploy UI) and cross-UI uniformity (every UI presents identical component-owned fields from the one committed schema).
- Re-remove docstring_coverage periodic agent (accidentally re-created after correct removal in #20260724T181101Z).  The repo declares `languages: [markdown]` and has no Python source to scan, making the agent a perpetual no-op.
- **Python practices:** add 'Cross-platform filesystem I/O' section — OS matrix CI (`ubuntu-latest`, `macos-latest`, `windows-latest` with `fail-fast: false`), code guards for POSIX-only semantics (`os.chmod`, `os.replace` retry loop, `os.fsync` fd-only, `tempfile.mkstemp` atomic writes), citing filelock, python-dotenv, tomlkit, and platformdirs as source projects.
- Add Prose linting (`prose-linting.md`) to the mkdocs.yml nav under 'Every repo'.
- pre-commit: add Vale prose-linting hooks after codespell (20260725T043020Z-add-vale-hooks-to-pre-commit-config-yaml-95fd)
- New standard page: [Prose linting](docs/prose-linting.md) — Vale prose linter for style, readability, and fleet-specific vocabulary consistency, integrated through the existing pre-commit pipeline.
- Enable survey periodic workflow (`.robotsix-mill/periodic/survey.yaml`) to discover similar open-source standards projects and propose improvements.
- Codified "no paid or licensed Marketplace Actions" rule in the free-tier-only standard, and added a 2026-07-25 fleet audit for Marketplace Action and private-repo runner violations.
- Standardize: Ruff high-signal lint rules — replace ARG, C4, PERF, PT with
  SIM, C4, LOG, G, ERA, PGH, RUF, PT as the recommended Tier 2 rule set.
  Remove ARG-specific per-file ignores; new rule families need none.
- New standard page: [Pre-commit baseline](docs/pre-commit-baseline.md) — five zero-config file-hygiene hooks (`trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-toml`, `check-added-large-files`) for every Python repo.
- Re-create `.robotsix-mill/periodic/docstring_coverage.yaml` periodic workflow that was merged but missing from the tree.
- New **[Python Makefile convention](docs/python-makefile-convention.md)** — standard
  `Makefile` targets for every Python/uv repo (`install`, `lint`, `typecheck`,
  `test`, `test-unit`, `test-integration`, `coverage`, `docs`, `lock-check`,
  `pre-commit`, `clean`, and optional `coverage-view`, `docs-serve`, `test-op`
  targets), with a self-documenting `help` target.
- **Python practices**: codified single-source version convention — `pyproject.toml [project].version` is authoritative; `__version__` MUST be derived from `importlib.metadata.version()` instead of hard-coded. Prevents silent version drift between the auto-release bumper (which updates only `pyproject.toml`) and the hand-maintained `__init__.py` literal.
- robotsix-standards: Remove `docstring_coverage` periodic agent — repo is Markdown-only and has no Python source modules to scan.
- Add `config-ownership.md` to the MkDocs navigation sidebar under "Deployable components" (it was the only docs page missing from the nav).
- Ignore `https://github.com/*` and `https://docs.github.com/*` in htmlproofer to prevent transient GitHub 504 errors from failing CI builds.
- Add Async SQLAlchemy test fixtures standard — three-layer fixture pattern (session-scoped engine, function-scoped connection with rollback, function-scoped session with savepoints) for clean database test isolation without dropping tables.
- Pre-commit CI jobs must pass `--show-diff-on-failure` via `extra_args` so that hook-modification diffs appear in CI logs (Python practices).
- Enable `completeness_check` periodic workflow for robotsix-standards
- **Pytest strictness configuration** — new standard page mandating `filterwarnings = ["error"]` and `xfail_strict = true` as baseline, with `--strict-markers` and `--strict-config` as the recommended tier, so every Python test suite fails loudly on deprecations, unregistered markers, and stale xfails.
- docs(security-posture): add Bandit to Gate 1 SAST section as complementary Python-specific SAST layer via `python-ci.yml`
- Added [default config location](docs/default-config-location.md) standard: canonical in-repo location (`config/config.json`) for the shipped default config that seeds the deploy-side config on first registration; cross-references central-deploy ticket b159 as the primary consumer.
- Standardize release-time SBOM publishing: every fleet repo MUST attach its
  CycloneDX SBOM (`sbom.cyclonedx.json`) as a GitHub Release asset, raising the
  OpenSSF Scorecard SBOM check from 5/10 to 10/10. Optional Sigstore attestation
  via `actions/attest`. Documented in security posture gate 6 and repo baseline
  releases section.
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
