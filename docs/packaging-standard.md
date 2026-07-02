# Packaging standard

Conventions for how robotsix repos are packaged, versioned, and shipped, so the
three deploy modes behave predictably across the stack.

## Distribution tier is explicit

A repo is **either** a library **or** a service — decide and be consistent:

| Tier | Ships as | Example | Rules |
|---|---|---|---|
| **Library** | PyPI wheel, `py.typed`, no Docker | `robotsix-llmio`, `robotsix-config` | Genuinely `pip install`-able; deps resolvable from PyPI. |
| **Service** | Container image (not pip-installed by end users) | `robotsix-auto-mail`, `robotsix-mill` | Run the container or `uv sync` from the repo. |

**Do not advertise a pip path for a service whose deps are git-only.** Several
services list first-party deps via `[tool.uv.sources]` git URLs, which pip
ignores — so `pip install <service>` cannot work even from a built wheel.
Document "run the container or `uv sync` from the repo" instead of a broken
`pip install`.

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
