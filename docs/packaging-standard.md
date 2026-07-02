# Packaging standard

Conventions for how robotsix repos are packaged, versioned, and shipped, so the
three deploy modes behave predictably across the stack.

## Distribution tier is explicit

A repo is **either** a library **or** a service — decide and be consistent.
**uv is the standard tool** for installing and running robotsix packages
(`uv sync`, `uv add`, `uv run`, `uvx`); pip is not a supported install path.

| Tier | Ships as | Example | Install |
|---|---|---|---|
| **Library** | PyPI wheel + `py.typed` | `robotsix-llmio`, `robotsix-config` | Consumers `uv add <lib>` (published to PyPI). |
| **Service** | Container image | `robotsix-auto-mail`, `robotsix-mill` | Run the container, or `uv sync` from a checkout. |

Because uv honours `[tool.uv.sources]`, a service's first-party git deps resolve
under `uv sync`, so the from-checkout install works even when the package isn't
on PyPI. **Do not promise a `pip install <service>` path** — pip ignores
`[tool.uv.sources]` and can't resolve those git deps. The two supported answers
are "run the container" and "`uv sync` from a checkout", both uv-based.

## `requires-python`

- **Services**: standardize on `>=3.14` (the stack's runtime baseline).
- **Libraries**: target `>=3.11` so the widest set of consumers can depend on
  them — `robotsix-config` is `>=3.11` for exactly this reason.
- **Keep the README in sync.** A README claiming "Python 3.12+" while
  `pyproject.toml` pins `>=3.14,<3.15` hard-blocks users the docs invite. The
  metadata is authoritative; fix the prose.

## Console scripts

- One primary entry point per service: `robotsix-<service>` (e.g.
  `robotsix-mill`, `robotsix-auto-mail`).
- **Host-side ops tools do not belong in `[project.scripts]`.** Tools like
  `robotsix-autoupdate` (a git-pull + `docker compose up` helper) are dev/ops
  tooling, aren't even copied into the runtime image, and should live outside
  the shipped package's scripts.

## Image registry & tags

- **One registry** for all service images. Recommendation: **GHCR**
  (`ghcr.io/damien-robotsix/<repo>`) — no extra secret needed, already used by
  part of the stack. (The alternative is standardizing on Docker Hub; the point
  is *one* — today the stack is split across GHCR, Docker Hub, PyPI, and none.)
- **One tag convention**:
  - `main` — current default branch build.
  - `sha-<short>` — immutable, reproducible pin.
  - `X.Y.Z` — on version tags.
- central-deploy composes pin `:main`; document `sha-<short>` as the
  reproducible option for operators who want immutability.

## The two compose files

Every service maintains two, with distinct jobs (see the
[deploy contract](deploy-contract.md) and [integration guide](integrating-a-service.md)):

| File | Job | central-deploy |
|---|---|---|
| `docker-compose.yml` (root) | Local dev — may `build:`, bind-mount source, use dev ports | **Ignored** |
| `deploy/docker-compose.yml` | Production via central-deploy — pre-built image, named volumes, labels | **The contract** |

Keep the service/CLI command set consistent between them.
