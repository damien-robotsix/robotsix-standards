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
| **Local dev docker** | Root `docker-compose.yml` + `Dockerfile` | For local development; may `build:` and bind-mount source. |
| **Deployment system** | `deploy/docker-compose.yml` consumed by central-deploy | Pre-built image, named volumes, `robotsix.deploy.*` labels. |

Configuration is identical across all three modes — see the
[config standard](config-standard.md).

## Authentication is centralized — components ship none

A deployable component implements **no user-facing authentication** of its
own: no login page, no HTTP Basic middleware, no session handling, no
`auth.*` config section. Authentication happens **once, at the deployment
system's gateway** — central-deploy validates the operator's session on every
proxied HTTP and WebSocket request before traffic reaches a component, so a
component behind the gateway only ever receives authenticated requests.
Per-component auth on top of that is a second password for the same door:
each one is an extra credential to provision, rotate, and get wrong.

Scope — what this does and doesn't cover:

- **Removed**: operator/user-facing auth — UI login walls, Basic-auth
  middleware, password/session config fields.
- **Kept**: machine-to-machine credentials a component *uses or serves* —
  broker bearer tokens, third-party API keys, webhook signatures. Those are
  secrets (see the [config standard](config-standard.md)), not an auth
  system.
- **Deployed any other way** (own reverse proxy, raw port, local dev),
  authentication is the **operator's responsibility** — e.g. auth at their
  proxy. A component must never be exposed directly to an untrusted network
  on the assumption that it protects itself; it doesn't.
- **Trust model**: the network behind the gateway is trusted; isolating
  components from each other is the deployment system's concern, not
  per-component auth.

Migration sequencing: a component that today relies on its embedded auth
(e.g. behind a plain reverse proxy) removes it **only after** it is served
exclusively through the gateway — otherwise the removal window exposes it
unauthenticated.

## Logging

- **Logs go to stdout/stderr, never to files.** The container log stream is
  the fleet's one log sink — `docker logs` and the deploy dashboard see
  everything, and rotation is the runtime's problem. A file under a volume is
  either *data* (an audit trail the app produces — then name the volume as
  data) or a mistake: file logs are invisible to the log view and grow
  without rotation.
- **Log level is a config field** — a `log_level` enum in the component's
  pydantic model (see the [config standard](config-standard.md)), not an
  environment variable.

Nothing more is standardized on purpose — no structured-JSON mandate, no
metrics/collector requirement. Either gets added deliberately when something
in the fleet needs it.

## LLM tracing

> Only for components that call LLMs — most repos never need this section.

- Tracing is **opt-in, one way**: Langfuse via `robotsix-llmio[tracing]`,
  a graceful no-op when unconfigured.
- Tracing credentials are **`SecretStr` fields in the config model**, like
  any other secret; at startup the app exports them to the `LANGFUSE_*`
  process environment the SDK expects, *before* the SDK initializes. No
  tracing credentials in compose `environment:` (see the config standard's
  [`environment:` rule](config-standard.md#4-what-environment-is-for)).

## Build & release

Every component builds and publishes its image the same way — one Dockerfile
pattern and one shared reusable publish workflow, to a single registry (GHCR),
with SBOM/provenance attestation and a vulnerability scan. No repo hand-rolls
its own build/push. Full detail: [Docker build & release](docker-standard.md).

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
- [Docker build & release](docker-standard.md) — the single build + publish method.
- [Deploy contract](deploy-contract.md) — the `deploy/docker-compose.yml` shape.
- [Entrypoint contract](entrypoint-contract.md) — container startup behavior.
- [Integrating a service](integrating-a-service.md) — the end-to-end how-to.
