# robotsix-standards

Shared conventions for the robotsix stack, so any repository — whoever wrote it,
whenever — is configured, packaged, tested, and (if deployable) shipped the same
predictable way.

This repo ([`damien-robotsix/robotsix-standards`](https://github.com/damien-robotsix/robotsix-standards))
holds **the standard** (docs under `docs/`) — the canonical target of the
standards link every fleet README and AGENT.md carries. The shared library that
implements the config standard lives in
[`robotsix-config`](https://github.com/damien-robotsix/robotsix-config)
— one pydantic model, one JSON file (`load_config`, `dump_config`,
`config_schema_json`), the `ROBOTSIX_CONFIG_FILE` convention, and the `0600`
writer. One library, not two.

Published at [damien-robotsix.github.io/robotsix-standards](https://damien-robotsix.github.io/robotsix-standards/).

## Why this exists

As a stack grows, each repository tends to solve the same recurring problems —
config loading, packaging and versioning, CI and security gates, deployment — in
its own slightly different way. Every repo becomes a small dialect: contributors
relearn conventions each time, tooling and CI get reinvented, and operators face
per-repo guesswork. These standards define one way to do each, so consistency is
the default.

## Two scopes

**Every repository** (libraries and deployable components):

| Doc | What it covers |
|---|---|
| [Repo baseline](docs/repo-baseline.md) | Distribution tiers, changelog/module hygiene, CI & security gates, license — language-agnostic. |
| [Towncrier changelog (superseded)](docs/towncrier.md) | Historical reference: the prior towncrier-based changelog mechanism. Superseded by [release-please](docs/release-please.md) + conventional commits. |
| [Free-tier only](docs/free-tier-only.md) | No paid services (LLM agent inference excepted): Actions on a free tier (public or self-hosted runner), public/self-hosted images, permissive licences. |
| [Security posture](docs/security-posture.md) | Self-enforcing security gates (SAST, dependency review, Dependabot, workflow hardening, secret protection, SBOM), auditable per repo. |
| [Secret files are never tracked](docs/secret-files-are-never-tracked.md) | The `.secrets-patterns-excluded` file that tells TruffleHog and detect-secrets which paths to skip — separate from `.gitignore`. |
| [CycloneDX SBOM via uv export](docs/sbom-cyclonedx-uv.md) | Standards-conformant CycloneDX SBOMs generated natively from `uv.lock` via `uv export` — keeps vulnerability audit output as a separate, accurately-named artifact. |
| [GitHub Actions security](docs/github-actions-security.md) | zizmor static-security auditor for GitHub Actions workflows — canonical invocation, severity policy, phased rollout. |
| [Stale bot must exempt pull requests](docs/stale-bot-must-exempt-pull-requests.md) | Every `stale.yml` must disable pull-request staling and closing with `days-before-pr-stale: -1` and `days-before-pr-close: -1` — keep issue hygiene, never auto-close PRs. |
| [Dependabot auto-merge](docs/dependabot-auto-merge.md) | Dependabot auto-merge must be gated on required CI passing (not purely actor-gated), restricted to minor/patch updates, and must exclude docker and pre-commit ecosystems. |
| [CI dependency management](docs/ci-dependency-standard.md) | Renovate over Dependabot for Python/uv lockfile updates, `uv lock --check` CI gate, scheduled refresh for git-pinned dependencies, and `--resolution lowest-direct` for minimum-dependency testing. |
| [Changelog & releases (superseded)](docs/changelog-driven-releases.md) | Historical reference: the prior towncrier fragment-driven release workflow. Superseded by [release-please](docs/release-please.md) + conventional commits. |
| [Release-please release automation](docs/release-please.md) | Conventional-commit-driven release PRs, automated version bump, changelog generation, git tag, and GitHub Release — the fleet-wide release mechanism. |
| [CI lint tool pinning](docs/ci-lint-pinning.md) | CI lint jobs must run the same version-pinned tools as `.pre-commit-config.yaml` — no floating/latest installs, one version source. |
| [Distribution & Packaging](docs/distribution-packaging.md) | Git-based consumption of first-party libraries — no package index, no registry publish step. |
| [Single-source versioning](docs/single-source-versioning.md) | One source of truth for the version string, read dynamically by the setuptools build backend — prevents `pyproject.toml` / `__init__.py` drift. |
| [Python CI workflow](docs/python-ci-workflow.md) | Required `ci.yml` shape: lint → type-check → test+coverage, run on every push and PR — the enforcement mechanism for the quality gates declared in `pyproject.toml`. |
| [Python practices](docs/python.md) | uv, hatchling, `requires-python`, lint/type/security gates, test layout, pre-commit hooks. |
| [Python `__main__.py` exit-code forwarding](docs/python-main-py-forward.md) | `__main__.py` must forward `main()`'s return value to `sys.exit()` so `python -m <pkg>` reports the same exit code as the installed console script. |
| [Console-script subprocess tests](docs/console-script-subprocess-test.md) | Every `[project.scripts]` entry point must be tested as a subprocess through the installed binary, not only in-process or via `python -m`. |
| [Python Makefile convention](docs/python-makefile-convention.md) | Standard Makefile targets (install, lint, test, clean) for every Python repository using uv. |
| [Pytest practices](docs/pytest.md) | Pytest strictness configuration (`filterwarnings`, `xfail_strict`, `--strict-markers`, `--strict-config`) and optional-dependency `importorskip` guards so every test suite fails loudly on deprecations and collects cleanly without optional extras. |
| [Doc-example testing](docs/doc-example-testing.md) | Runnable `python` code blocks in MkDocs documentation must be executed by pytest so that renaming or removing a public symbol breaks the build instead of silently leaving the docs wrong. |
| [Pytest shared state builders](docs/pytest-shared-state-builders.md) | Root `tests/conftest.py` for shared fixtures, `make_<thing>` factory fixtures for mutable state, and value fixtures as thin factory callers — reusable builders across every test package. |
| [Ruff lint rules](docs/ruff-lint-rules.md) | Tier 2 ruff rule families (SIM, C4, LOG, G, ERA, PGH, RUF, PT) with the PT006 exclusion. |
| [Mypy strictness](docs/mypy.md) | Mypy as a hard CI gate (not advisory), baseline snapshots as a bootstrapping scaffold with a defined exit, and strict-mode type-clean new code. |
| [Pyright strict mode](docs/pyright.md) | Pyright must run at `typeCheckingMode = "strict"` so it enforces the same type-safety baseline as mypy `--strict`. |
| [py.typed wheel guard](docs/py-typed-wheel-guard.md) | Automated verification that the `py.typed` marker ships in the built wheel — installed type-check + wheel-content assertion. |
| [Dependency typing metadata](docs/dependency-typing-metadata.md) | A `[tool.robotsix.typing]` table declaring which runtime dependencies are typed or untyped, so downstream consumers generate their mypy/pyright exemptions from an upstream source of truth instead of rediscovering `py.typed` by hand. |
| [Docstring convention](docs/docstrings.md) | Python docstring style and coverage rules for all public modules, classes, and functions. |
| [Deprecation lifecycle](docs/deprecation-policy.md) | Public-library deprecation policy: deprecate in version N and remove no earlier than the next major, with a runtime `DeprecationWarning`, a `.. deprecated::` docstring block, a `Deprecation:` commit footer, and a test asserting the warning. |
| [HTTP client persistence](docs/http-client-persistence.md) | One persistent `httpx.Client` (or `requests.Session`) with an explicit timeout, reused for all outbound calls — no per-call module-level convenience helpers. |
| [SSRF-hardened httpx fetchers](docs/ssrf-hardened-fetchers.md) | Tools fetching attacker-influenced URLs must validate and pin the resolved IP at the connection layer (guarded `httpcore` pool), not in a pre-flight DNS check — closes the DNS-rebinding TOCTOU gap and re-validates redirect hops. |
| [Issue and PR templates](docs/issue-pr-templates.md) | Every repo ships `.github/ISSUE_TEMPLATE/bug_report.md`, `.github/ISSUE_TEMPLATE/feature_request.md`, `.github/PULL_REQUEST_TEMPLATE.md`, and `CONTRIBUTING.md` so every contributor — human or AI agent — starts from the same structured workflow. |
| [Library internal logging](docs/library-logging.md) | Module-level `logging.getLogger(__name__)`, a single `NullHandler` in `__init__.py`, lazy `%`-style formatting, and DEBUG-for-routine events — library logging that never prints unless the app opts in. |
| [Logging](docs/logging.md) | Structured JSON logging via structlog, stdout-only output, correlation-id middleware, and level conventions for every deployable service. |
| [Hypothesis testing](docs/hypothesis.md) | Fleet-recommended property-based testing: adoption guidance, dev-dependency declaration, invariant-based tests, composite strategies, `RuleBasedStateMachine`, profiles, and CI integration. |
| [Mutation testing (mutmut)](docs/mutation-testing.md) | Advisory weekly mutmut cron for Python repos with ≥70% coverage — non-blocking by design, HTML report artifact, mutation score in the workflow summary. |
| [Markdown linting](docs/markdown-linting.md) | markdownlint-cli2 and codespell pre-commit hooks for every repo that publishes MkDocs documentation. |
| [Prose linting](docs/prose-linting.md) | Vale prose linter for style, readability, and fleet-specific vocabulary consistency — integrated through the existing pre-commit pipeline. |
| [MkDocs build integrity](docs/mkdocs-build.md) | Strict mode build gating and link-validation configuration for every MkDocs site. |
| [Module taxonomy scope](docs/module-taxonomy-scope.md) | What belongs in `docs/modules.yaml`, and the pre-commit hook that keeps the registry in sync with the tree — product code, not the repo's own build and lint scaffolding. |
| [Docs site deployment](docs/docs-site-deployment.md) | GitHub Pages contract for repos that publish: caller permissions, Pages source, concurrency ownership. A mismatch fails at startup with no logs. |
| [Contributor guide in docs nav](docs/contributing-in-nav.md) | Every MkDocs site must surface the repo's contributor guide in the docs nav so it is discoverable to readers of the published site. |
| [JavaScript practices](docs/javascript.md) | Vanilla frontend JS as static assets, lockfile discipline, vitest coverage floor, eslint/stylelint. |
| [PHP practices](docs/php.md) | Native `php -l` syntax-check over all `.php` files as a blocking CI gate — no custom scanners, no parse errors in production. |
| [Async SQLAlchemy test fixtures](docs/async-sqlalchemy-test-fixtures.md) | Three-layer database test fixture pattern — session-scoped engine, function-scoped connection with rollback, function-scoped session with savepoints — for clean isolation without dropping tables. |
| [ROS 2 practices](docs/ros2.md) | Workspace-skeleton layout, vcs2l manifest, devcontainer with ccache, colcon/rosdep build lifecycle, lint gates. |
| [Pre-commit baseline](docs/pre-commit-baseline.md) | Five zero-config file-hygiene hooks (trailing-whitespace, end-of-file-fixer, check-yaml, check-toml, check-added-large-files) for every Python repo. |

**Deployable components** (additionally):

| Doc | What it covers |
|---|---|
| [Component standard](docs/component-standard.md) | The three deploy modes, no embedded auth (centralized at the gateway), image registry & tags, the two compose files. |
| [Config standard](docs/config-standard.md) | One config model, one file (no env overlay, no CLI merge), one secret convention — the same in all three deploy modes. |
| [Default config location](docs/default-config-location.md) | Canonical in-repo location for the shipped default config (`config/config.json`) that seeds the deploy-side config on first registration. |
| [Config ownership](docs/config-ownership.md) | The hard line between deploy-plane config (central-deploy UI) and component-owned config (the component's own HTTP surface and Settings panel). |
| [Config-ownership audit](docs/config-ownership-audit.md) | Fleet-wide classification of every deployable component against the config-ownership standard, with remediation tracking. |
| [Config self-healing](docs/config-self-healing.md) | Lenient load with automatic stale-key stripping and self-heal rewrite — prevents crashloops when a config field is removed. |
| [Shared config shapes](docs/shared-config-shapes.md) | Six canonical cross-cutting config blocks (Langfuse, LLM backend, logging, HTTP bind, data dir, GitHub App) defined once for every component. |
| [Docker build & release](docs/docker-standard.md) | One Dockerfile pattern + one shared publish workflow → GHCR, with attestation, scanning, and CI integration tests. |
| [Deploy contract](docs/deploy-contract.md) | The `deploy/docker-compose.yml` shape the deployment system consumes (canonical copy lives in [central-deploy](https://github.com/damien-robotsix/robotsix-central-deploy/blob/main/docs/DEPLOY_CONTRACT.md)). |
| [Multi-disk data handling](docs/disk-handling.md) | Disk-agnostic named volumes in component repos, deploy-time disk selection, relocatable volumes, and per-disk usage reporting. |
| [Entrypoint contract](docs/entrypoint-contract.md) | Console script as PID 1 (exec-form `ENTRYPOINT`); `entrypoint.sh` only for genuine startup work. |
| [FastAPI Pydantic field descriptions](docs/fastapi-pydantic-field-descriptions.md) | Every public request/response Pydantic model field must carry `Field(description=...)` so the generated OpenAPI schema is self-documenting. |
| [FastAPI test isolation](docs/fastapi-test-isolation.md) | Mutable server state exposed through `Depends()` dependencies so tests can override via `app.dependency_overrides` — never import and mutate the module-level store directly. |
| [Integrating a service](docs/integrating-a-service.md) | Task-oriented how-to: zero to a one-click deploy. |
| [Chat access](docs/chat-access-standard.md) | A standard skill endpoint so the chat agent (`robotsix-chat`) can invoke operations on the component. |
| [HTTP error envelope](docs/http-error-envelope.md) | One consistent RFC 9457 `application/problem+json` envelope for every error response, registered via centralized exception handlers. |
| [SSE response headers](docs/sse-response-headers.md) | Every `text/event-stream` response must carry `Cache-Control: no-cache`, `Connection: keep-alive`, and `X-Accel-Buffering: no` — via one shared helper so the header set cannot drift per-endpoint. |
| [HTTP security headers](docs/http-security-headers.md) | Standard OWASP security response headers (CSP, HSTS, X-Frame-Options, etc.) via a single shared `secure` middleware — no hand-rolled per-service headers. |
| [Health endpoints](docs/health-endpoints.md) | Split liveness (`/health`) vs. readiness (`/readyz`) endpoints so the orchestrator can restart dead processes without gating traffic on a dependency probe, and vice versa. |
| [OpenSSF Scorecard (not used)](docs/scorecard.md) | Fleet-wide decision to NOT run OpenSSF Scorecard; zizmor, actionlint, the permissions audit, Dependabot/`uv audit`, and Trivy gate the same supply-chain properties. |

**The deployment system** (central-deploy only):

| Doc | What it covers |
|---|---|
| [Deployment system](docs/deployment-system.md) | The bootstrap tier: which standards central-deploy follows and which it is exempt from, and why. |

**Meta** (this repo's own operational docs):

| Doc | What it covers |
|---|---|
| [Mill agents](docs/mill-agents.md) | Bespoke periodic agents that keep the standards themselves healthy — security-posture audits, TOC-sync checks, and similar health passes. |

## The shared library

The config standard is implemented by
[`robotsix-config`](https://github.com/damien-robotsix/robotsix-config),
which every service depends on:

```python
from pydantic import BaseModel, SecretStr
from robotsix_config import config_schema_json, load_config


class MailConfig(BaseModel):
    log_level: str = "info"
    password: SecretStr = SecretStr("")


# The one file (ROBOTSIX_CONFIG_FILE, default config/config.json) is the only
# source of values; the model's defaults fill anything the file omits.
# No env overlay, no CLI merge.
cfg = load_config(MailConfig)
print(config_schema_json(MailConfig))  # -> commit as config/config.schema.json
```

The JSON file is located by one variable, `ROBOTSIX_CONFIG_FILE` (default
`config/config.json`). Secrets are `pydantic.SecretStr` (masked on read);
`robotsix_config.dump_config` persists config `0600` in a `0700`
directory. See the [config standard](docs/config-standard.md) for the full rule.

All fleet repos and their docs sites are indexed in [docs/fleet.md](docs/fleet.md).

## Building the docs

```sh
uv run --group docs mkdocs build --strict
```

## Status

Active. The standards describe the target state; migration of each service is
incremental and non-breaking (see the rollout section of the config standard).

## License

MIT — see [LICENSE](LICENSE).
