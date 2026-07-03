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
  service bearer tokens, third-party API keys, webhook signatures. Those are
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

## Health endpoint

Every deployable component serves **`GET /health`** on its service port —
**200 means alive**, anything else means not. One fleet-wide path (it was a
three-way split — `/health`, `/health/live`, `/healthz` — for no reason):
the image `HEALTHCHECK` probes it, the deployment system reads the primary's
health as component health, and nothing has to guess.

- Semantics: **liveness only** — "the process is up and serving". No
  dependency checks: a service that reports unhealthy because a *sibling* is
  down turns one outage into a restart cascade. A readiness/deep-check
  endpoint can be added deliberately when something needs it.
- Response body unspecified (a small JSON status is fine; nothing parses it).

## Sibling resilience

Startup order is undefined (the deploy contract ignores `depends_on`) and
siblings routinely restart, so:

- **Start without dependencies.** A component reaches "alive, serving
  `/health` 200" with every `<name>_url` dependency unreachable — no
  import-time or startup connectivity checks.
- **Fail per-operation, not per-process.** A call to a down sibling fails
  that request or cycle (log it, return an error, skip the tick); the process
  keeps running and recovers on the next attempt. No backoff framework, no
  circuit breakers — retry-next-time matches the fleet's scale.

## Logging

- **Logs go to stdout/stderr, never to files.** The container log stream is
  the fleet's one log sink — `docker logs` and the deploy dashboard see
  everything, and rotation is configured **host-wide** (json-file
  `max-size`/`max-file` in the daemon config — see central-deploy's host
  setup docs); components never rotate their own output. A file under a volume is
  either *data* (an audit trail the app produces — then name the volume as
  data) or a mistake: file logs are invisible to the log view and grow
  without rotation.
- **All timestamps are UTC, ISO-8601 with explicit offset**
  (`2026-07-03T14:00:00Z`) — logs, stored data, API responses, filenames.
  Rendering local time is strictly a UI concern. Interleaving services'
  logs during incident reconstruction is exactly when a stray local-time
  stamp costs an hour.
- **Log level is a config field** — a `log_level` enum in the component's
  pydantic model (see the [config standard](config-standard.md)), not an
  environment variable.

Nothing more is standardized on purpose — no structured-JSON mandate, no
metrics/collector requirement. Either gets added deliberately when something
in the fleet needs it.

## LLM usage

> Only for components that call LLMs — most repos never need this section.

- LLM calls go through **robotsix-llmio**, and the consumer only ever picks
  a **capability level** — llmio's `level1`–`level4` scale (1 = cheap and
  repetitive, 2 = intermediate, 3 = high-level organisation, 4 = frontier
  reasoning). Which model/provider backs each level is llmio's tier
  configuration, not the component's business.
- **The level is a config field, always** — a typed llmio-level enum in the
  component's pydantic model (per-call-site fields where a component makes
  differently-hard calls), set in the deploy UI like any other option. Never
  hard-code a level, and never take it from env (`LLMIO_MODEL_LEVEL`-style
  variables are the pre-standard form). Operators tune capability vs. cost
  per deployment without touching code.
- **The level→model tier mapping is fleet-global**, managed through the
  deployment system: changing "level 3" from one model to another happens
  once, for every component at once — no component defines its own mapping.
  (Distribution mechanism is central-deploy's; components just call llmio.)
- Tracing is **opt-in, one way**: Langfuse via `robotsix-llmio[tracing]`,
  a graceful no-op when unconfigured.
- **One Langfuse project per repo/function.** A component's main LLM
  function traces to a project named `<repo>`; every distinct
  LLM-generating function inside a component (e.g. a memory subsystem
  making its own extraction/recall calls) traces to its **own** project,
  named `<repo>-<function>` — never funnel two functions' traffic into a
  shared project, tagged or otherwise. Failure prevented: a shared project
  breaks cost-monitor's 1:1 reconciliation model (one Langfuse project ↔
  one OpenRouter key ↔ one reconciliation row), and high-volume background
  traffic drowns the interactive function's traces and skews its
  latency/cost dashboards.
- **Each project is registered in cost-monitor's `projects.yaml`**,
  alongside the OpenRouter key that funds that function. An unregistered
  project is invisible to the cost dashboard and reconciliation — spend
  drifts unnoticed.
- Tracing credentials are **`SecretStr` fields in the config model**, like
  any other secret; at startup the app exports them to the `LANGFUSE_*`
  process environment the SDK expects, *before* the SDK initializes. No
  tracing credentials in compose `environment:` (see the config standard's
  [`environment:` rule](config-standard.md#4-what-environment-is-for)).
  A subsystem's project gets its **own** credential fields — it must not
  reuse the component's main `LANGFUSE_*` credentials, or its traffic
  lands in the main project and silently defeats the per-function split.

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
