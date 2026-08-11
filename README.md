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
| [Towncrier changelog](docs/towncrier.md) | Per-PR newsfragments in `changelog.d/`, `pyproject.toml` config, CI enforcement, and automated release compilation. *(Superseded by [release-please](docs/release-please.md).)* |
| [Free-tier only](docs/free-tier-only.md) | No paid services (LLM agent inference excepted): Actions on a free tier (public or self-hosted runner), public/self-hosted images, permissive licences. |
| [Security posture](docs/security-posture.md) | Self-enforcing security gates (SAST, dependency review, Dependabot, workflow hardening, secret protection, SBOM), auditable per repo. |
| [GitHub Actions security](docs/github-actions-security.md) | zizmor static-security auditor for GitHub Actions workflows — canonical invocation, severity policy, phased rollout. |
| [Stale bot must exempt pull requests](docs/stale-bot-must-exempt-pull-requests.md) | Every `stale.yml` must disable pull-request staling and closing with `days-before-pr-stale: -1` and `days-before-pr-close: -1` — keep issue hygiene, never auto-close PRs. |
| [Dependabot auto-merge](docs/dependabot-auto-merge.md) | Dependabot auto-merge must be gated on required CI passing (not purely actor-gated), restricted to minor/patch updates, and must exclude docker and pre-commit ecosystems. |
| [CI dependency management](docs/ci-dependency-standard.md) | Renovate over Dependabot for Python/uv lockfile updates, `uv lock --check` CI gate, and scheduled refresh for git-pinned dependencies. |
| [Changelog & releases](docs/changelog-driven-releases.md) | Towncrier fragment-driven releases, CI-enforced changelog fragments, and the shared auto-release workflow — no hand-edited changelog. *(Superseded by [release-please](docs/release-please.md).)* |
| [Release-please release automation](docs/release-please.md) | Conventional-commit-driven release PRs, automated version bump, changelog generation, git tag, and GitHub Release — the fleet-wide replacement for towncrier. |
| [CI lint tool pinning](docs/ci-lint-pinning.md) | CI lint jobs must run the same version-pinned tools as `.pre-commit-config.yaml` — no floating/latest installs, one version source. |
| [Distribution & Packaging](docs/distribution-packaging.md) | Git-based consumption of first-party libraries — no package index, no registry publish step. |
| [Python CI workflow](docs/python-ci-workflow.md) | Required `ci.yml` shape: lint → type-check → test+coverage, run on every push and PR — the enforcement mechanism for the quality gates declared in `pyproject.toml`. |
| [Python practices](docs/python.md) | uv, hatchling, `requires-python`, lint/type/security gates, test layout, pre-commit hooks. |
| [Python `__main__.py` exit-code forwarding](docs/python-main-py-forward.md) | `__main__.py` must forward `main()`'s return value to `sys.exit()` so `python -m <pkg>` reports the same exit code as the installed console script. |
| [Console-script subprocess tests](docs/console-script-subprocess-test.md) | Every `[project.scripts]` entry point must be tested as a subprocess through the installed binary, not only in-process or via `python -m`. |
| [Python Makefile convention](docs/python-makefile-convention.md) | Standard Makefile targets (install, lint, test, clean) for every Python repository using uv. |
| [Pytest practices](docs/pytest.md) | Pytest strictness configuration (`filterwarnings`, `xfail_strict`, `--strict-markers`, `--strict-config`) and optional-dependency `importorskip` guards so every test suite fails loudly on deprecations and collects cleanly without optional extras. |
| [Pytest shared state builders](docs/pytest-shared-state-builders.md) | Root `tests/conftest.py` for shared fixtures, `make_<thing>` factory fixtures for mutable state, and value fixtures as thin factory callers — reusable builders across every test package. |
| [Ruff lint rules](docs/ruff-lint-rules.md) | Tier 2 ruff rule families (SIM, C4, LOG, G, ERA, PGH, RUF, PT) with the PT006 exclusion. |
| [Mypy strictness](docs/mypy.md) | Mypy as a hard CI gate (not advisory), baseline snapshots as a bootstrapping scaffold with a defined exit, and strict-mode type-clean new code. |
| [Pyright strict mode](docs/pyright.md) | Pyright must run at `typeCheckingMode = "strict"` so it enforces the same type-safety baseline as mypy `--strict`. |
| [py.typed wheel guard](docs/py-typed-wheel-guard.md) | Automated verification that the `py.typed` marker ships in the built wheel — installed type-check + wheel-content assertion. |
| [Docstring convention](docs/docstrings.md) | Python docstring style and coverage rules for all public modules, classes, and functions. |
| [HTTP client persistence](docs/http-client-persistence.md) | One persistent `httpx.Client` (or `requests.Session`) with an explicit timeout, reused for all outbound calls — no per-call module-level convenience helpers. |
| [Library internal logging](docs/library-logging.md) | Module-level `logging.getLogger(__name__)`, a single `NullHandler` in `__init__.py`, lazy `%`-style formatting, and DEBUG-for-routine events — library logging that never prints unless the app opts in. |
| [Logging](docs/logging.md) | Structured JSON logging via structlog, stdout-only output, correlation-id middleware, and level conventions for every deployable service. |
| [Hypothesis testing](docs/hypothesis.md) | Property-based testing profiles, shared strategies module, and CI integration for repos that use Hypothesis. |
| [Markdown linting](docs/markdown-linting.md) | markdownlint-cli2 and codespell pre-commit hooks for every repo that publishes MkDocs documentation. |
| [Prose linting](docs/prose-linting.md) | Vale prose linter for style, readability, and fleet-specific vocabulary consistency — integrated through the existing pre-commit pipeline. |
| [MkDocs build integrity](docs/mkdocs-build.md) | Strict mode build gating and link-validation configuration for every MkDocs site. |
| [Module taxonomy scope](docs/module-taxonomy-scope.md) | What belongs in `docs/modules.yaml`, and the pre-commit hook that keeps the registry in sync with the tree — product code, not the repo's own build and lint scaffolding. |
| [Docs site deployment](docs/docs-site-deployment.md) | GitHub Pages contract for repos that publish: caller permissions, Pages source, concurrency ownership. A mismatch fails at startup with no logs. |
| [Contributor guide in docs nav](docs/contributing-in-nav.md) | Every MkDocs site must surface the repo's contributor guide in the docs nav so it is discoverable to readers of the published site. |
| [JavaScript practices](docs/javascript.md) | Vanilla frontend JS as static assets, lockfile discipline, vitest coverage floor, eslint/stylelint. |
| [PHP practices](docs/php.md) | Native `php -l` syntax-check over all `.php` files as a blocking CI gate — no custom scanners, no parse errors in production. |
| [Async SQLAlchemy test fixtures](docs/async-sqlalchemy-test-fixtures.md) | Three-layer database test fixture pattern — session-scoped engine, function-scoped connection with rollback, function-scoped session with savepoints — for clean isolation without dropping tables. |
| [ROS 2 practices](docs/ros2.md) | Workspace-skeleton layout, vcs2l manifest, devcontainer, colcon/rosdep build, lint gates. |
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
| [Docker build & release](docs/docker-standard.md) | One Dockerfile pattern + one shared publish workflow → GHCR, with attestation, scanning, and CI integration tests. |
| [Deploy contract](docs/deploy-contract.md) | The `deploy/docker-compose.yml` shape the deployment system consumes (canonical copy lives in [central-deploy](https://github.com/damien-robotsix/robotsix-central-deploy/blob/main/docs/DEPLOY_CONTRACT.md)). |
| [Multi-disk data handling](docs/disk-handling.md) | Disk-agnostic named volumes in component repos, deploy-time disk selection, relocatable volumes, and per-disk usage reporting. |
| [Deploy API key](docs/deploy-api-key.md) | How central-deploy auto-provisions a deploy API key into any component that opts in — opt-in mechanism, injection path, secret-handling, and lifecycle. |
| [Entrypoint contract](docs/entrypoint-contract.md) | Console script as PID 1 (exec-form `ENTRYPOINT`); `entrypoint.sh` only for genuine startup work. |
| [FastAPI Pydantic field descriptions](docs/fastapi-pydantic-field-descriptions.md) | Every public request/response Pydantic model field must carry `Field(description=...)` so the generated OpenAPI schema is self-documenting. |
| [FastAPI test isolation](docs/fastapi-test-isolation.md) | Mutable server state exposed through `Depends()` dependencies so tests can override via `app.dependency_overrides` — never import and mutate the module-level store directly. |
| [Integrating a service](docs/integrating-a-service.md) | Task-oriented how-to: zero to a one-click deploy. |
| [Chat access](docs/chat-access-standard.md) | A standard skill endpoint so the chat agent (`robotsix-chat`) can invoke operations on the component. |
| [HTTP error envelope](docs/http-error-envelope.md) | One consistent RFC 9457 `application/problem+json` envelope for every error response, registered via centralized exception handlers. |
| [HTTP security headers](docs/http-security-headers.md) | Standard OWASP security response headers (CSP, HSTS, X-Frame-Options, etc.) via a single shared `secure` middleware — no hand-rolled per-service headers. |
| [Health endpoints](docs/health-endpoints.md) | Split liveness (`/health`) vs. readiness (`/readyz`) endpoints so the orchestrator can restart dead processes without gating traffic on a dependency probe, and vice versa. |
| [OpenSSF Scorecard](docs/scorecard.md) | Independent supply-chain audit (~20 checks) producing a single numeric score; closes the gap the per-gate security stack doesn't cover. |

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
