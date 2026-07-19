# The deployment system (bootstrap tier)

> **Scope: [`robotsix-central-deploy`](https://github.com/damien-robotsix/robotsix-central-deploy)
> only.** Every other repo is a [library](repo-baseline.md) or a
> [deployable component](component-standard.md).

central-deploy is the deployment system itself, which makes it a third kind of
repo: it ships a runnable service like any component, but it **cannot be
deployed through itself** — someone has to start the thing that starts
everything else. Rather than leaving it silently non-conforming, this page
states exactly which standards it follows and which it is exempt from, and why.

## What it follows

- **[Repo baseline](repo-baseline.md)** and **[Python practices](python.md)** —
  fully. uv tooling, hatchling, `requires-python >= 3.14`, changelog and
  module hygiene, MIT license, the full CI gate set.
- **[Docker build & release](docker-standard.md)** — fully. Digest-pinned
  `python:3.14-slim` in both stages, uv via `COPY --from=ghcr.io/astral-sh/uv`,
  frozen-lockfile system-interpreter install, runtime image without build
  tooling, non-root user (uid 1000), `HEALTHCHECK` on `/health` (Python
  stdlib), and the shared `docker-release.yml` workflow publishing
  `ghcr.io/damien-robotsix/robotsix-central-deploy` with SBOM/provenance
  attestation and a Trivy gate.
- **[Entrypoint contract](entrypoint-contract.md)** — in its default form: no
  `entrypoint.sh`; the exec-form console script is PID 1, so SIGTERM reaches
  the server directly.

## What it is exempt from

### Deploy contract (`deploy/docker-compose.yml`)

There is no central-deploy above central-deploy. Its **root
`docker-compose.yml` is the production deploy** — the one sanctioned exception
to "the root compose is dev-only". That compose:

- pulls the published GHCR image (`docker compose pull && docker compose up -d`
  is the update path; `build: .` remains for local dev);
- runs the hardened **socket-proxy sibling**
  (`tecnativa/docker-socket-proxy` with a minimal API-scope allowlist) — the
  same pattern the deploy contract's `host-docker-sock` label mandates for
  components;
- carries the host bind-mounts no component may declare (the Docker socket on
  the proxy, read-only; the host filesystem read-only for disk reporting) —
  they are the reason this tier exists;
- runs a dedicated **self-update Watchtower**, scoped to central-deploy's own
  container — **the single sanctioned auto-updater in the stack**. Components
  update only via central-deploy's Update action (see
  [Docker build & release](docker-standard.md#deploy-updates-are-deliberate));
  central-deploy itself has no button above it, so a Watchtower presses it.
  Any other Watchtower or registry poller in the fleet is legacy and must be
  removed.

### Config standard (one JSON file)

central-deploy is configured by **`ROBOTSIX_LIFECYCLE_*` environment
variables** (pydantic-settings), injected by its own compose file. The
component that writes every other service's `config.json` takes its own
configuration from the layer below it; a config file would add a volume and a
bootstrap step to the thing that exists to remove those steps. Its env-var
table lives in its own docs, not here.

## Deployment engine code must be repo-agnostic

A deployment engine is a **generic control plane**, not a registry of
services. Its source code (`src/`) MUST NOT carry per-service or per-repo
definitions — those belong in declarative data, never in engine code.

**Rule:** The engine source code MUST NOT contain:

- Hard-coded service names (`if service == "chat"`, `frozenset({"svc1",
  "svc2"})` allowlists)
- Per-service routing, TLS, or hostname rules
- Per-service image-pull config or registry references
- Service-specific project aliases for observability backends

**Failure mode it prevents:** Hard-coding service definitions in engine code
makes the engine a bottleneck. Every new service, every renamed service, and
every changed observability project requires a code change, a PR, and a
redeploy of the engine itself — the opposite of the self-service onboarding
the engine exists to provide. Over time the engine accumulates a graveyard of
special cases, and the operator's first question becomes "which branch has the
latest service list?" rather than "what does the onboarding API show?"

### Where service definitions live

| Concern | Location |
|---|---|
| Per-service specs (name, repo URL, deploy mode, compose label flags) | Persisted component config store, populated via the onboarding API |
| Virtual component definitions | Config file (`config.json`) under a `virtual_components` key |
| Observability project credentials | Config dict (`langfuse_projects: {alias: {public_key, secret_key}}`) |
| Mutation / capability permissions | Per-component boolean flags (e.g. `chat_agent_mutatable: bool`), set at onboard time via compose labels |

### Implementation patterns

**Allowlists → permission flags.** Replace a module-level `_ALLOWED_SERVICES =
frozenset({"a", "b"})` with a boolean field on the component config model
(e.g. `chat_agent_mutatable: bool`), set via a compose label
(`robotsix.deploy.chat-agent-mutatable: "true"`) at onboard time. The engine
checks the flag on the component, not the name against a hard-coded set.

**Project aliases → config dict.** Replace hard-coded `_PROJECT_CONFIG_KEYS =
{"project-a": {...}}` with a `langfuse_projects: dict[str, {public_key,
secret_key}]` config field read from the deployment engine's own config.
Backward compatibility can be handled with a legacy fallback map that the
operator can deprecate on their own schedule.

**Default values → empty.** Config defaults that embed specific hostnames or
component ids (e.g. `langfuse_base_url = "https://langfuse.robotsix.net"`,
`mill_component_id = "mill"`) MUST be empty strings or absent — the operator
sets them per deployment. A default that names a specific fleet resource is a
hard-coded service definition by another name.

### Acceptance criteria

A deployment engine that satisfies this rule passes these checks:

- `grep` for individual service names in `src/` returns nothing except
  backward-compat fallback maps and documentation strings.
- Adding a new managed service is achievable via the onboarding API or
  declarative config — never by editing engine code.
- Every hard-coded allowlist, project alias, and named default has been
  migrated to the component config store, a config dict, or a per-component
  boolean flag.

### Reference

The `robotsix-central-deploy` repo completed this migration in
`20260719T181243Z-make-central-deploy-repo-agnostic-remove-f13a`, removing all
service-specific code in favour of the patterns above.

## Rule of thumb

If central-deploy needs a capability, ask whether a component could get it
through the deploy contract instead. Only what genuinely cannot be expressed
there (self-hosting, the Docker socket, host-level introspection) belongs in
this tier — everything else follows the component standards like any other
repo.
