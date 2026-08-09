# robotsix stack standards

Shared conventions for the robotsix stack, so that any repository — whoever
wrote it, whenever — is configured, packaged, tested, and (if deployable)
shipped in the same predictable way.

## Why this exists

As a stack grows, each repository tends to solve the same recurring problems —
how configuration is loaded and where it lives, how packages are installed and
versioned, how CI and security gates are wired, and how a service is deployed —
in its own slightly different way. Left unchecked, every repo becomes a small
dialect: contributors relearn the conventions each time, tooling and CI get
reinvented instead of shared, and operators face per-repo guesswork.

These standards define one way to do each of those things. The payoff is
consistency: moving between repos is cheap, tooling and workflows are shared
rather than duplicated, and a config or deploy setup learned once transfers
everywhere.

## Two scopes

### Every repository (libraries and deployable components)

- **[Repo baseline](repo-baseline.md)** — distribution tiers, changelog and
  module-registration hygiene, CI and security gates, licensing.
- **[Towncrier changelog](towncrier.md)** — per-PR newsfragments in
  `changelog.d/`, `pyproject.toml` config, CI enforcement, and automated
  release compilation — the fleet-wide changelog tool.
- **[Free-tier only](free-tier-only.md)** — no paid services (LLM agent
  inference excepted): free-tier CI (public repo or self-hosted runner),
  public/self-hosted container images, permissive licences only.
- **[Security posture](security-posture.md)** — self-enforcing security gates
  (SAST, dependency review, Dependabot, workflow hardening, secret protection,
  SBOM), auditable per repo.
- **[GitHub Actions security](github-actions-security.md)** — zizmor static-security
  auditor for GitHub Actions workflows, canonical invocation, and a
  warning-first-then-fail-closed phased rollout policy.
- **[Stale bot must exempt pull requests](stale-bot-must-exempt-pull-requests.md)** —
  every `stale.yml` must disable pull-request staling and closing with
  `days-before-pr-stale: -1` and `days-before-pr-close: -1` — keep issue
  hygiene, never auto-close PRs.
- **[Async SQLAlchemy test fixtures](async-sqlalchemy-test-fixtures.md)** — three-layer database
  test fixture pattern (session-scoped engine, function-scoped connection with
  rollback, function-scoped session with savepoints) for clean test isolation
  without dropping tables.
- **[Changelog & releases](changelog-driven-releases.md)** — towncrier fragment-driven
  releases, CI-enforced changelog fragments, and the shared auto-release
  workflow — no hand-edited changelog. *(Superseded by
  [release-please](release-please.md).)*
- **[Release-please release automation](release-please.md)** — conventional-commit-driven
  release PRs, automated version bump, changelog generation, git tag, and
  GitHub Release via `googleapis/release-please-action` — the fleet-wide
  release-automation tool replacing towncrier.
- **[CI lint tool pinning](ci-lint-pinning.md)** — CI lint jobs must run the same
  version-pinned tools as `.pre-commit-config.yaml`, not floating/latest
  sources — one version source, no skew.
- **[Dependabot auto-merge](dependabot-auto-merge.md)** — Dependabot auto-merge
  must be CI-gated (`mergeable_state == "clean"`), restricted to minor/patch
  updates, and must exclude docker and pre-commit ecosystems from the
  auto-merge group.
- **[Distribution & Packaging](distribution-packaging.md)** — git-based consumption of
  first-party libraries — no package index, no registry publish step.
- **[Docstring convention](docstrings.md)** — Python docstring style and coverage
  rules for all public modules, classes, and functions.
- **[HTTP client persistence](http-client-persistence.md)** — one persistent
  `httpx.Client` (or `requests.Session`) with an explicit timeout, reused for
  all outbound calls — no per-call module-level convenience helpers.
- **[Library internal logging](library-logging.md)** — module-level
  `logging.getLogger(__name__)`, a single `NullHandler` in `__init__.py`,
  lazy `%`-style formatting, and DEBUG-for-routine events — library logging
  that never prints unless the application opts in.
- **[Logging](logging.md)** — structured JSON logging via structlog,
  stdout-only output, correlation-id middleware, and level conventions
  for every deployable service.
- **[Hypothesis testing](hypothesis.md)** — property-based testing profiles,
  shared strategies, and CI integration for repos that use Hypothesis.
- **[Markdown linting](markdown-linting.md)** — markdownlint-cli2 and codespell
  pre-commit hooks for every repo that publishes MkDocs documentation.
- **[Prose linting](prose-linting.md)** — Vale prose linter for style,
  readability, and fleet-specific vocabulary consistency — integrated
  through the existing pre-commit pipeline.
- **[MkDocs build integrity](mkdocs-build.md)** — strict mode build gating
  and link-validation configuration for every MkDocs site.
- **[Module taxonomy scope](module-taxonomy-scope.md)** — what belongs in
  `docs/modules.yaml`: product code, not the repo's own build and lint
  scaffolding.
- **[Docs site deployment](docs-site-deployment.md)** — the GitHub Pages
  contract for repos that publish: caller permissions, Pages source, and
  concurrency ownership. A mismatch fails at startup with no logs at all.
- **[Python CI workflow](python-ci-workflow.md)** — required `ci.yml` shape:
  lint → type-check → test+coverage, run on every push and PR — the enforcement
  mechanism for the quality gates declared in `pyproject.toml`.
- **[Python practices](python.md)** — uv, hatchling, `requires-python` policy,
  lint/type/security gates, test layout, pre-commit hooks.
- **[Python `__main__.py` exit-code forwarding](python-main-py-forward.md)** —
  `__main__.py` must forward `main()`'s return value to `sys.exit()` so
  `python -m <pkg>` reports the same exit code as the installed console script.
- **[Console-script subprocess tests](console-script-subprocess-test.md)** —
  every `[project.scripts]` entry point must be tested as a subprocess through
  the installed binary — not only in-process or via `python -m`.
- **[Python Makefile convention](python-makefile-convention.md)** — standard
  `Makefile` targets for every Python/uv repo (`install`, `lint`,
  `typecheck`, `test`, `test-unit`, `test-integration`, `coverage`, `docs`,
  `lock-check`, `pre-commit`, `clean`, and optional targets).
- **[Pytest practices](pytest.md)** — `filterwarnings = ["error"]`,
  `xfail_strict = true`, `--strict-markers`/`--strict-config`, and
  optional-dependency `importorskip` guards so every test suite fails loudly on
  deprecations and collects cleanly without optional extras.
- **[Pytest shared state builders](pytest-shared-state-builders.md)** —
  root `tests/conftest.py` for shared fixtures, `make_<thing>` factory
  fixtures for mutable test state, and value fixtures as thin factory
  callers — so shared builders are reusable across every test package.
- **[Ruff lint rules](ruff-lint-rules.md)** — Tier 2 ruff rule families (SIM,
  C4, LOG, G, ERA, PGH, RUF, PT) with the PT006 exclusion.
- **[Mypy strictness](mypy.md)** — mypy as a hard CI gate (not advisory),
  baseline snapshots as a bootstrapping scaffold with a defined exit, and
  strict-mode type-clean new code.
- **[Pyright strict mode](pyright.md)** — pyright must run at
  `typeCheckingMode = "strict"` so it enforces the same type-safety baseline
  as mypy `--strict`, with per-diagnostic overrides only for proven-untyped
  third-party dependencies.
- **[py.typed wheel guard](py-typed-wheel-guard.md)** — automated verification
  that the `py.typed` marker ships in the built wheel, so a packaging
  regression cannot silently strip type information from downstream consumers.
- **[JavaScript practices](javascript.md)** — vanilla frontend JS as static
  assets, lockfile discipline, vitest coverage floor, eslint/stylelint.
- **[PHP practices](php.md)** — native `php -l` syntax-check over all `.php`
  files as a blocking CI gate — no custom scanners, no parse errors in
  production.
- **[ROS 2 practices](ros2.md)** — workspace-skeleton layout, vcs2l manifest,
  devcontainer, colcon/rosdep build, lint gates.
- **[Pre-commit baseline](pre-commit-baseline.md)** — five zero-config
  file-hygiene hooks (trailing-whitespace, end-of-file-fixer, check-yaml,
  check-toml, check-added-large-files) for every Python repo.

### Deployable components (additionally)

A *deployable component* ships a runnable service (a container image) and
integrates with the deployment system. Beyond the baseline it follows:

- **[Component standard](component-standard.md)** — the three deploy modes,
  no embedded auth (centralized at the fleet edge), image registry & tags, the
  two compose files.
- **[Config standard](config-standard.md)** — one config model that resolves the
  same way across all deploy modes.
- **[Default config location](default-config-location.md)** — canonical in-repo
  location for the shipped default config that seeds the deploy-side config on
  first registration.
- **[Config ownership](config-ownership.md)** — the hard line between
  deploy-plane config (central-deploy UI) and component-owned config
  (the component's own HTTP surface and Settings panel).
- **[Config-ownership audit](config-ownership-audit.md)** — fleet-wide
  classification of every deployable component against the config-ownership
  standard, with remediation tracking.
- **[Docker build & release](docker-standard.md)** — one Dockerfile pattern and
  one publish workflow to a single registry, with CI image scanning and
  integration tests.
- **[Deploy contract](deploy-contract.md)** — the `deploy/docker-compose.yml`
  shape the deployment system consumes.
- **[Deploy API key provisioning](deploy-api-key.md)** — how central-deploy
  auto-provisions a deploy API key into any component that opts in — opt-in
  mechanism, injection path, secret-handling, and lifecycle.
- **[Entrypoint contract](entrypoint-contract.md)** — how a component's
  container starts up.
- **[FastAPI Pydantic field descriptions](fastapi-pydantic-field-descriptions.md)** —
  every public request/response Pydantic model field must carry
  `Field(description=...)` so the generated OpenAPI schema is
  self-documenting.
- **[FastAPI test isolation](fastapi-test-isolation.md)** — mutable server
  state exposed through `Depends()` dependencies so tests can override via
  `app.dependency_overrides`; never import and mutate the module-level store
  directly.
- **[Integrating a service](integrating-a-service.md)** — the end-to-end how-to.
- **[Chat access](chat-access-standard.md)** — a standard skill endpoint so the
  chat agent can invoke operations on the component.
- **[HTTP error envelope](http-error-envelope.md)** — one consistent RFC 9457
  `application/problem+json` envelope for every error response, registered via
  centralized exception handlers.
- **[HTTP security headers](http-security-headers.md)** — standard OWASP security
  response headers (CSP, HSTS, X-Frame-Options, etc.) via a single shared
  `secure` middleware, so no service hand-rolls its own headers.
- **[Health endpoints](health-endpoints.md)** — split liveness (`/health`) vs.
  readiness (`/readyz`) endpoints so the orchestrator can restart dead processes
  without gating traffic on a dependency probe, and vice versa.
- **[OpenSSF Scorecard](scorecard.md)** — independent supply-chain audit
  (~20 checks) producing a single numeric score; closes the gap the per-gate
  security stack doesn't cover.

### The deployment system (bootstrap tier)

One repo — `robotsix-central-deploy` — is the deployment system itself and
cannot be deployed through itself:

- **[Deployment system](deployment-system.md)** — which standards it follows
  (baseline, docker build & release, entrypoint contract) and which it is
  exempt from (deploy contract, config standard), and why.

## Which am I?

- **Library** — imported by other packages, no runnable service of its own.
  Follow the **repo baseline** only.
- **Deployable component** — ships a service/container. Follow the **repo
  baseline** *and* the **component** standards.
- **The deployment system** — central-deploy only. Follow the
  [deployment-system tier](deployment-system.md).

## The fleet

Every repo, what it is, and where its docs live: **[the fleet page](fleet.md)**.

## Reference implementation

The config standard is implemented by the shared configuration library
([`robotsix-config`](https://github.com/damien-robotsix/robotsix-config)):
`load_config` loads **the one config file** (`ROBOTSIX_CONFIG_FILE`, default
`config/config.json`) into a validated pydantic model — the file is the only
source of values, the model's defaults fill the rest; no env overlay, no CLI
merge — with secret masking (`SecretStr`), a `0600` config writer
(`dump_config`), and a JSON-Schema emitter (`config_schema_json`) for the
deploy UI. One shared library, already a stack dependency.

## Changing the standards

The standards change through the mill, like everything else:

- **File a ticket on the `robotsix-standards` board** — for a gap, a
  contradiction with fleet reality, or an incident whose post-mortem traces
  to a standards flaw (the 2026-07-03 claude-mount outage is the worked
  example: outage → standards change → fleet tickets, same day).
- The ticket follows the normal mill pipeline; **the approval gate is the
  operator's decision point**. A standard nobody approved is a suggestion.
- An accepted change lands as **one docs PR plus fleet-alignment tickets** —
  a standards change with no tickets is a wish.
- **Clean cutover is the default** for every migration: no compatibility
  shims, no aliases; data moves by hand, case by case.
- **Supersession is normal.** When reality reverses a decision, the new text
  references what it replaces — openly, not by silent rewrite.

## Mill agents

This repo carries its own [mill agents](mill-agents.md) — bespoke periodic
passes that keep the standards themselves healthy. The security-posture-audit
agent checks the security pages for completeness, consistency, currency, and
enforceability, filing draft tickets for gaps it finds.
