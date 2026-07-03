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

## Rule of thumb

If central-deploy needs a capability, ask whether a component could get it
through the deploy contract instead. Only what genuinely cannot be expressed
there (self-hosting, the Docker socket, host-level introspection) belongs in
this tier — everything else follows the component standards like any other
repo.
