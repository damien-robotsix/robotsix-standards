# Component standard

> **Scope: deployable components only** — a repository that ships a runnable
> service (a container image) and integrates with the deployment system. This is
> *in addition to* the [repo baseline](repo-baseline.md), which every repo
> follows.

A deployable component must run predictably three ways — installed from the
package, via local dev docker, and via the deployment system — and be configured
the same way in all three. This page covers the component-level packaging;
the detailed contracts are linked at the end.

## The three deploy modes

| Mode | What it is | Notes |
|---|---|---|
| **uv install** | `uv sync` from a checkout (or run the published image) | The from-checkout path; git deps resolve via `[tool.uv.sources]`. Not `pip install`. |
| **Local dev docker** | Root `docker-compose.yml` + `Dockerfile` + `entrypoint.sh` | For local development; may `build:` and bind-mount source. |
| **Deployment system** | `deploy/docker-compose.yml` consumed by central-deploy | Pre-built image, named volumes, `robotsix.deploy.*` labels. |

Configuration is identical across all three modes — see the
[config standard](config-standard.md).

## Image registry & tags

- **One registry** for all component images: **GHCR**
  (`ghcr.io/<owner>/<repo>`) — no extra registry secret is required and it
  integrates with the repo's own permissions.
- **Tag convention:**
  - `main` — current default-branch build.
  - `sha-<short>` — immutable, reproducible pin.
  - `X.Y.Z` — on version tags.
- Deploy composes pin `:main`; document `sha-<short>` as the reproducible option
  for operators who want immutability.

## The two compose files

Every component maintains two compose files with distinct jobs:

| File | Job | Deployment system |
|---|---|---|
| `docker-compose.yml` (root) | Local dev — may `build:`, bind-mount source, use dev ports | **Ignored** |
| `deploy/docker-compose.yml` | Production — pre-built image, named volumes, labels | **The contract** |

They legitimately diverge (dev builds locally and mounts source; deploy pulls a
published image). Keep the service/CLI command set consistent between them.

## Detailed contracts

- [Config standard](config-standard.md) — one config model across all deploy modes.
- [Deploy contract](deploy-contract.md) — the `deploy/docker-compose.yml` shape.
- [Entrypoint contract](entrypoint-contract.md) — container startup behavior.
- [Integrating a service](integrating-a-service.md) — the end-to-end how-to.
