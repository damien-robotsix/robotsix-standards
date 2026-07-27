# Config-ownership audit — fleet-wide classification

> **Audit date:** 2026-07-27  
> **Standard:** [Config ownership](config-ownership.md) — deploy-plane vs component-owned  
> **Scope:** Every deployable component listed in [the fleet](fleet.md)

Every deployable component's settings are classified against the two invariants
in [config-ownership.md](config-ownership.md):

1. **Deploy-plane exclusivity** — only settings the component cannot handle
   internally (image/tag, volume mounts, ports, resource limits, restart policy,
   `ROBOTSIX_CONFIG_FILE`, third-party `EnvStore` slots) belong in the deploy
   plane.
2. **Cross-UI uniformity** — every UI presents the identical set of
   component-owned fields from `config/config.schema.json`.

The classification below answers one question for every setting the component
carries in its deploy plane: *can the component apply this at runtime from its
own config file?* If yes, the setting must migrate out of the deploy plane.

## Deployable components

| Component | Config model | `config.schema.json` | Deploy-plane violations | Status |
|---|---|---|---|---|
| [robotsix-chat](https://github.com/damien-robotsix/robotsix-chat) | Pydantic (~30 top-level namespaces) | Yes | None — clean boundary. First-party secrets previously leaked into `environment:` (fixed, PR robotsix-chat#933). | ✅ Compliant |
| [robotsix-mill](https://github.com/damien-robotsix/robotsix-mill) | Pydantic (YAML cascade: `mill.defaults.yaml` → `mill.local.yaml` → `mill.production.yaml` → `MILL_*` env vars) | No (custom YAML loader) | N/A — CI/CD service, no `deploy/docker-compose.yml`. Not a deployable component per [component standard](component-standard.md). | — N/A |
| [robotsix-auto-mail](https://github.com/damien-robotsix/robotsix-auto-mail) | Pydantic (accounts, llm, langfuse blocks) | Yes | **Yes** — `command: ingest --watch --heartbeat-file /data/heartbeat` and `BOARD_PORT` env in `docker-compose.yml`. Both are component-internal operational settings (`--watch` mode, heartbeat path, board port) that belong in `config/config.json`, not the deploy plane. | ❌ Violation |
| [robotsix-calendar-agent](https://github.com/damien-robotsix/robotsix-calendar-agent) | Pydantic (`Settings` class: caldav URL/creds, sync interval, lookahead, timezone, log level) | Yes | None — only `ROBOTSIX_CONFIG_FILE` env var (allowlist) and a healthcheck. Healthcheck CLI entrypoint is acceptably component-internal. | ✅ Compliant |
| [robotsix-cost-monitor](https://github.com/damien-robotsix/robotsix-cost-monitor) | Pydantic (`BaseSettings`: langfuse keys, OpenRouter key, reconciliation interval, cost DB path, log level) | Yes | **Yes** — `command: serve --host 0.0.0.0 --port 8080` and `MONITOR_PORT` env in `docker-compose.yml`. The serve command and port binding are component-internal; the env-var port override is a non-allowlist deploy-plane escape hatch. | ❌ Violation |
| [robotsix-mill-ros2](https://github.com/damien-robotsix/robotsix-mill-ros2) | `.robotsix-mill/config.yaml` + `repos.yaml` + `devcontainer.json` | No (ROS 2 workspace skeleton) | N/A — workspace skeleton, no `deploy/docker-compose.yml`. Not a deployable component per [component standard](component-standard.md). | — N/A |
| [robotsix-central-deploy](https://github.com/damien-robotsix/robotsix-central-deploy) | Pydantic + env vars (7 `ROBOTSIX_LIFECYCLE_*` variables) | Via `robotsix-config` | **Yes** — deploy UI surfaces component-internal settings for sibling components (ticket `20260726T095134Z-remove-central-deploy-ui-machinery-that-0b7f`, in progress). Additionally: Docker socket-proxy ACL env vars, `/:/host_root:ro` host bind-mount, and custom network topology in `docker-compose.yml`. Some of these are architecturally inherent to central-deploy's role as the deploy orchestrator. | ⚠️ In remediation |

## Shared libraries & tooling (out of scope)

These repos are not deployable components — they carry no `deploy/docker-compose.yml`
and are not subject to the deploy-plane config boundary. Listed for completeness.

| Repo | What it is |
|---|---|
| [robotsix-standards](https://github.com/damien-robotsix/robotsix-standards) | This site — the fleet's shared conventions. |
| [robotsix-config](https://github.com/damien-robotsix/robotsix-config) | The shared configuration library. |
| [robotsix-llmio](https://github.com/damien-robotsix/robotsix-llmio) | LLM provider abstraction. |
| [robotsix-modules](https://github.com/damien-robotsix/robotsix-modules) | `docs/modules.yaml` tooling. |
| [robotsix-github-workflows](https://github.com/damien-robotsix/robotsix-github-workflows) | Shared reusable CI workflows. |
| [robotsix-board](https://github.com/damien-robotsix/robotsix-board) | Ticket-board UI library. |

## Remediation tickets

| Component | Ticket | Scope |
|---|---|---|
| robotsix-chat | robotsix-chat#933 (closed) | Removed first-party secrets from `environment:` in deploy plane. |
| robotsix-central-deploy | `20260726T095134Z-remove-central-deploy-ui-machinery-that-0b7f` (blocked) | Remove deploy-UI machinery that surfaces component-internal settings. |
| robotsix-auto-mail | Filed below | Migrate `command:` and `BOARD_PORT` out of `docker-compose.yml` into `config/config.json`. |
| robotsix-cost-monitor | Filed below | Migrate `command:` and `MONITOR_PORT` out of `docker-compose.yml` into `config/config.json`. |

## Migration path

Violating components follow the [migration guidance](config-ownership.md#migration-guidance)
in config-ownership.md:

1. Add the migrated key to the component's pydantic model with a safe default.
2. Deploy — the new key takes its default; old deploy-plane key still present.
3. Operator sets the new key through `PUT /config` (or the Settings panel).
4. Remove the deploy-plane key and drop the fallback read in the same deploy cycle.

The `command:` overrides in auto-mail and cost-monitor are a special case:
the entrypoint itself should bind to `0.0.0.0:$PORT` where `$PORT` is read from
the config file at startup — the deploy plane supplies only the image and port
mapping, not the internal bind address or CLI flags.
