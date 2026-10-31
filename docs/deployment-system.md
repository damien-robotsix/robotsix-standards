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

Central-deploy does not sit above another central-deploy. Its **root
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
  removed. The self-updater is held to the rules in
  [Self-update path](#self-update-path): it verifies provenance before the
  swap, and its own image is pinned and maintained.

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
| Observability project credentials | The owning component's canonical `langfuse` / `openrouter` blocks (see the [component standard](component-standard.md)); the engine's own `langfuse_projects` / `openrouter_keys` config dicts are an operator override, not the primary store |
| Mutation / capability permissions | Per-component boolean flags (e.g. `chat_agent_mutatable: bool`), set at onboard time via compose labels |

### Implementation patterns

**Allowlists → permission flags.** Replace a module-level `_ALLOWED_SERVICES =
frozenset({"a", "b"})` with a boolean field on the component config model
(e.g. `chat_agent_mutatable: bool`), set via a compose label
(`robotsix.deploy.chat-agent-mutatable: "true"`) at onboard time. The engine
checks the flag on the component, not the name against a hard-coded set.

**Project aliases → the owning component's config.** Replace hard-coded
`_PROJECT_CONFIG_KEYS = {"project-a": {...}}` with a read of each component's
canonical credential blocks — the component owns its own observability
credentials, and the engine only enumerates them. Keep a
`langfuse_projects` / `openrouter_keys` dict on the engine's own config as an
**operator override**: it wins on alias collision, so an operator can pin or
rotate a key, and can bridge a component that has not migrated yet — without
that being a fallback the engine applies on its own (see
[No credential fallbacks](component-standard.md#llm-usage)).

**Credentials reach consumers through one generic endpoint.** A fleet
consumer (a cost dashboard, a trace proxy) MUST obtain another component's
observability credentials by asking the engine, never by having them copied
into its own config. The engine exposes one route that enumerates every
component with its credentials; adding a consumer, a component, or a project
requires no engine change. Failure prevented: hand-copied credentials are
exactly the per-service definition this rule exists to eliminate, and they go
stale silently.

**Operator-supplied aliases that no component claims MUST still be
surfaced**, under a synthetic entry (e.g. component id
`operator-configured`), never dropped and never attributed to a component
that did not declare them. Failure prevented: dropping them makes an
operator's bridge for an unmigrated component invisible; attributing them
makes a component look migrated when it is not — and the synthetic entry
appearing in a consumer's UI is the visible signal that a migration is
still owed.

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

## Provenance verification before rollout

The deployment system consumes every published component image, so the
provenance check before rollout is a deployment-system duty. The rule, its
command, its rationale and its current status are stated once in
[security posture — SLSA Build Track](security-posture.md#slsa-build-track).
Failure mode this prevents: an image tampered with after the build is deployed
exactly like a genuine one.

### Self-update path

central-deploy's own image is the most privileged one in the stack: it holds
the Docker socket (through the socket proxy) and a read-only bind-mount of the
host filesystem. Today it is not rolled out through the verify-then-rollout
path above. The caretaker's self-update phase (when the component's
auto-update flag is on) and the `POST /system/update` button both launch a
one-shot `containrrr/watchtower` container, which pulls `:main` and recreates
central-deploy with no provenance check. The rules for this path:

1. **Same provenance check, before the swap.** The self-updater runs the
   check from
   [security posture — SLSA Build Track](security-posture.md#slsa-build-track)
   against the new image **digest** and refuses the swap on failure. It then
   deploys that verified digest (`image@sha256:…`), never the `:main` tag
   re-resolved after the check — a tag re-pull reopens the window the check
   closed. Two shapes satisfy the rule: central-deploy (or a small updater
   script/sidecar) runs `gh attestation verify` / `cosign verify-attestation`
   and then `docker compose up -d` on the pinned digest; or auto-update is
   dropped and the update is operator-triggered, with the verify step in it.
2. **A human gate or cooldown.** An unattended self-update waits at least one
   cooldown period after the new digest is first seen (the same 3-day release
   age as [dependency updates](security-posture.md#3-automated-dependency-updates-renovate-dependabot)),
   or it waits for an operator. A bad or tampered `:main` push must not be
   live within one poll interval.
3. **The updater image is named, digest-pinned and maintained.** The updater
   talks to the Docker socket, so it is part of the host's trust base: its
   image is pinned by digest (`image:tag@sha256:…`) with Dependabot (or
   Renovate) as the bumper, and it is a project that still ships security
   fixes. `containrrr/watchtower` fails the last test — the upstream
   repository was archived on 2025-12-17, its last release (1.7.1) dates from
   November 2023, and its README does not recommend it for production. The
   fleet's `containrrr/watchtower:1.7.1` reference is tag-pinned only. Replace
   it with a maintained updater or with the verify-then-deploy script in
   rule 1 (which needs no third-party updater image).

**Status — dated accepted risk.** None of the three rules is in place yet:
the self-update path rolls out central-deploy's own image unverified, without
a cooldown, through an archived, tag-pinned Watchtower. This is a dated
**accepted risk** (accepted 2026-10-31, review 2027-01-31), aligned with the
SLSA verification accepted risk and tracked in the
[security posture Audit table](security-posture.md#audit). Until it is
lifted, operators should keep the central-deploy component's auto-update flag
off and trigger the self-update by hand after checking the new digest.

**Failure modes this prevents:** provenance verification that covers every
image except the one that controls all the others leaves the host one
tampered `:main` push away from compromise — the attacker gets the Docker
socket and the host filesystem in a single poll interval. An unpinned,
unmaintained updater with socket access is a second direct host-compromise
path: a tag re-pointed upstream, or a vulnerability that will never be
patched, runs with the same privileges.

**Alignment:** SLSA v1.x *verifying artifacts* (every rollout path), OWASP
Top 10:2025 *A08 Software or Data Integrity Failures*, OWASP CICD-SEC-3 /
CICD-SEC-9, OpenSSF Scorecard *Pinned-Dependencies* and *Maintained*.

## Rule of thumb

If central-deploy needs a capability, ask whether a component could get it
through the deploy contract instead. Only what genuinely cannot be expressed
there (self-hosting, the Docker socket, host-level introspection) belongs in
this tier — everything else follows the component standards like any other
repo.
