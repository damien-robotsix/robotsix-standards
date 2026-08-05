# Docker build & release

> **Scope: deployable components only.** See the
> [component standard](component-standard.md).

Every component builds and ships its image **one way**: one Dockerfile pattern,
one publish workflow, one registry, one deploy path. No repo hand-rolls its own
`docker build`/`push` — that is how registries, tags, and attestations drift
apart across the stack.

## Build — the Dockerfile

A multi-stage Dockerfile that keeps build tooling out of the runtime image:

- **Base:** `python:3.14-slim`, **digest-pinned** (`@sha256:…`), matching the
  component's `requires-python`. Use the same base in both stages. (Dependabot's
  `docker` ecosystem bumps the digest — see
  [automated dependency updates](repo-baseline.md#automated-dependency-updates);
  an unbumped digest pin silently stops receiving base security patches.)
- **Builder stage:** bring in uv
  (`COPY --from=ghcr.io/astral-sh/uv:<x.y.z> /uv /uvx /bin/`, pinned to a
  released version), install `git` (uv needs it to clone the
  `[tool.uv.sources]` git-pinned first-party dependencies), and install the
  project **into the system interpreter** from the frozen lockfile:

  ```sh
  uv export --frozen --no-emit-project --format requirements-txt -o /tmp/requirements.txt
  uv pip install --system --no-cache -r /tmp/requirements.txt
  uv pip install --system --no-cache --no-deps .
  ```

  Do **not** use `uv sync` here: it installs into a project virtualenv
  (`/app/.venv`), so the runtime stage's `COPY --from=builder /usr/local/…`
  finds nothing and the image ships without the app (this has regressed real
  builds twice — robotsix-mill's Dockerfile carries the scar comment).
  `uv pip install --system` targets `/usr/local`, which is exactly what the
  runtime stage copies. Never install dev/test tooling into the image.
- **Runtime stage:** copy only the installed site-packages and the console
  script from the builder — no uv, no git, no compilers, no source-only build
  deps. A component whose *runtime* genuinely needs a system dependency (e.g.
  Node.js + the `claude` CLI for the claude-sdk subscription transport, which
  spawns the CLI as a subprocess) may install it in the runtime stage — kept
  minimal, with a comment saying why it is required, and with apt caches
  cleaned in the same layer.
- **Non-root, standardized layout:** every image defaults to the same non-root
  account: user **`app`**, **uid/gid 1000**, home **`/home/app`**,
  `WORKDIR /home/app`. The
  deployment system sets the container user to **the single deployment uid
  (1000) at container-create time**, so ownership inside managed volumes is
  consistent across the whole fleet regardless of what an image baked in.
  Fixed mount points, the same in every container: config at
  **`/home/app/config/`** (`config.json` per the
  [config standard](config-standard.md)), persistent data at **`/data`**, and
  — for components carrying the claude-mount label — the central-deploy-managed
  **`claude-auth` named volume** (contents owned by the deployment uid) at
  **`/home/app/.claude`**. The mount target is the container's home
  directory — there is no per-component mount-target configuration and no
  `/root/.claude` variant: every managed container runs as the deployment uid
  (1000) with home `/home/app`, so `/root` is neither accessible nor
  meaningful. **Nothing is ever bind-mounted from the host** (see the
  [deploy contract](deploy-contract.md)); the container's writable surface is
  exactly its mounted volumes — `$HOME` is otherwise read-only.
- **Healthcheck:** declare a `HEALTHCHECK` probing the service's health
  endpoint **using only the Python stdlib** — the slim image has no `curl` or
  `wget`, so a curl-based probe fails on every run. The image `HEALTHCHECK` is
  the **canonical** probe: it travels with the image and applies in every
  deploy mode. Every compose file must also declare a matching service-level
  `healthcheck:` stanza — see [Compose-level healthcheck](#compose-level-healthcheck).
- **Entrypoint:** exec-form **`ENTRYPOINT ["robotsix-<name>"]`** — the console
  script is PID 1 and receives SIGTERM directly. An `entrypoint.sh` is the
  exception for genuine startup work, not the rule — see the
  [entrypoint contract](entrypoint-contract.md).
- **Port:** `EXPOSE` the service port.

```dockerfile
# syntax=docker/dockerfile:1
ARG BASE_DIGEST=sha256:...        # pin the python:3.14-slim digest

FROM python:3.14-slim@${BASE_DIGEST} AS builder
COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /uvx /bin/
WORKDIR /app

# git: uv must clone the [tool.uv.sources] git-pinned first-party deps.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
COPY src ./src
# Install into the system interpreter (/usr/local) — NOT `uv sync`, which
# builds a venv the runtime COPY would miss. Add runtime extras via --extra.
RUN uv export --frozen --no-emit-project --format requirements-txt -o /tmp/requirements.txt \
    && uv pip install --system --no-cache -r /tmp/requirements.txt \
    && uv pip install --system --no-cache --no-deps . \
    && rm -f /tmp/requirements.txt

FROM python:3.14-slim@${BASE_DIGEST} AS production
COPY --from=builder /usr/local/lib/python3.14/site-packages/ /usr/local/lib/python3.14/site-packages/
COPY --from=builder /usr/local/bin/robotsix-<name> /usr/local/bin/robotsix-<name>
# Standardized layout: app/1000, /home/app. The deployment system sets the
# container user to the deployment uid (1000) at create time; $HOME is
# read-only — all writes go to the mounted volumes (config/, /data).
RUN groupadd --gid 1000 app \
    && useradd --create-home --uid 1000 --gid 1000 app
WORKDIR /home/app
USER app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8080/health').status==200 else 1)"
ENTRYPOINT ["robotsix-<name>"]
```

## Publish — one reusable workflow (the single method)

**Do not** hand-roll `docker/build-push-action`, `docker/metadata-action`, a
registry login, or a per-repo tag scheme. Publish by calling the shared
`docker-release.yml` reusable workflow from
[robotsix-github-workflows](https://github.com/damien-robotsix/robotsix-github-workflows),
triggered on pushes to `main` and `v*` tags. The copy-paste caller template
lives in that repo's README — standards pages deliberately do not embed
workflow YAML, so the template versions with the workflow it calls and cannot
drift from it.

The reusable workflow does all of the following, identically for every
component:

- **Builds and pushes to GHCR:** `ghcr.io/<owner>/<repo>`.
- **Tags:** push to `main` → `main`, `sha-<short>`; a `v*` tag (created by the
  shared auto-release workflow — see
  [changelog & releases](repo-baseline.md#changelog-releases)) → `X.Y.Z`,
  `sha-<short>`.
- **Attestations:** SBOM + build provenance (`provenance: mode=max`,
  `sbom: true`), signed via OIDC.
- **Scan:** a Trivy vulnerability scan with findings uploaded as a workflow artifact.

## Registry & tags

- **One registry: GHCR** (`ghcr.io/<owner>/<repo>`). No component image goes to
  Docker Hub or any other registry — one registry across the stack, no per-repo
  registry secret to manage.
- **Tags:** `main` (latest default-branch build), `sha-<short>`
  (immutable/reproducible), `X.Y.Z` (on release tags). No **`latest`
  tag** exists — it would duplicate `main` under a second name and invite
  unpinned pulls from outside the standard.

## CI-time image scan

The release workflow's Trivy gate runs only when an image is published. To
catch vulnerable base images and dependencies **before** merge, every PR also
builds the image and scans it, via the shared PR-scan reusable workflow in
robotsix-github-workflows (caller template in its README). The policy the
workflow enforces:

- Build with `docker/build-push-action` (`push: false`, `load: true`).
  **Skip the GHA layer cache for large images**: exporting a multi-GB image's
  layers to the cache API (`cache-to`) was measured at 45-55 minutes per run
  on a robotsix image whose cold build takes ~4 minutes — the cache is a net
  loss well before the gigabyte mark. Only add `cache-from`/`cache-to` after
  timing both paths on the actual image.
- **Gate policy: block on fixable findings only** (`severity: CRITICAL,HIGH`,
  `ignore-unfixed: true`, `exit-code: 1`, findings uploaded as a workflow
  artifact). A
  red gate then always means "a fixed version exists, take it". Base-image
  CVEs with **no released fix** are unactionable by a PR author (the package
  can be neither upgraded nor removed) and must not block merges; they stay
  visible through the findings artifact and the weekly rescan.
- A finding that **has** a fix but genuinely doesn't apply is suppressed via a
  **curated `.trivyignore`** — every entry carries a comment saying why it
  doesn't apply. Never blanket-ignore; the file is the audit trail.
- A **weekly scheduled rescan** of the published `:main` image (report-only,
  artifact) complements the PR gate — it catches CVEs disclosed
  after the image was built.

## CI integration tests

The PR image scan catches vulnerable dependencies; it does **not** catch
build-time packaging errors — a missing entrypoint binary, a broken Python
import, a missing `config.json` — any of which crashloops the container in
production. A Docker build can succeed (`RUN` stages pass) while the
production layer is broken, because the build never exercises the runtime
image. Every deployable component therefore runs a **Docker integration test**
on every PR, immediately after the image build.

The test does three things:

1. **Build the image.** Use the same `docker/build-push-action` call the scan
   workflow uses (`push: false`, `load: true`).
2. **Verify the entrypoint binary.** Start a short-lived container and check
   that the console script named in the Dockerfile's `ENTRYPOINT` exists at
   its expected path and is executable:

   ```sh
   docker run --rm --entrypoint /bin/sh <image> -c \
     'test -x /usr/local/bin/robotsix-<name>'
   ```

3. **Import smoke test.** In the same container, verify the service's
   top-level package imports without error:

   ```sh
   docker run --rm --entrypoint python <image> -c \
     'import robotsix_<name>'
   ```

   For non-Python services, replace with the equivalent smoke test — a
   Node.js `require`, a ROS 2 node listing, or whatever verifies the runtime
   ships intact.

The two verification steps are fast (a few seconds each) and run in the same
PR workflow as the image build and scan — after the build, before the scan.
A failure blocks the PR, catching the regression before merge.

**Failure mode prevented:** A container image that builds successfully but
whose production layer is broken — because the runtime `COPY --from=builder`
missed a binary, a `uv pip install` in the builder stage targeted a venv the
runtime stage didn't copy, or a packaging change dropped a required file.
These are the exact regressions that caused the invest service to crashloop
after a routine update (missing entrypoint binary, ModuleNotFoundError,
missing `config.json`) — all build-time defects CI didn't catch because
nothing ran the image.

A reusable workflow for this gate lives in
[robotsix-github-workflows](https://github.com/damien-robotsix/robotsix-github-workflows)
so every component calls the same integration-test step, identically.

## Compose-level healthcheck

Every deployable component's compose file **must** declare a service-level
`healthcheck:` stanza on the primary service, even when the probe is identical
to the image's `HEALTHCHECK`. The compose `healthcheck:` key
[overrides](https://docs.compose-spec.io/05-services/#healthcheck) the
Dockerfile directive at runtime and is the only health declaration that
Compose's `depends_on` with `condition: service_healthy` can gate on.

**The probe.** Use the same stdlib-only command as the image `HEALTHCHECK`
— the slim image has no `curl` or `wget`, so a curl-based probe fails on
every run:

```yaml
services:
  <svc>:
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:<port>/health')"]
      interval: 30s
      timeout: 5s
      start_period: 5s
      retries: 3
```

The `test` command, port, and timing values must match the image's
`HEALTHCHECK` directive exactly unless a per-environment override is
deliberate (a longer `start_period` under sustained load, a different
`interval` in dev). Any deviation from the image's values is a conscious
tuning decision, not accidental drift.

**Why the duplication is deliberate.** The image `HEALTHCHECK` travels with
the image and reports health in any runtime (plain `docker run`, Compose,
Kubernetes). The compose `healthcheck:` is required _in addition_ because:

- **`depends_on` gating.** Only a compose-level `healthcheck:` enables
  `depends_on: { service: { condition: service_healthy } }` — the Dockerfile
  directive alone does not make a container a usable readiness target for
  dependent services.
- **Per-environment tuning.** Compose overrides (`docker-compose.override.yml`)
  can adjust `interval`, `start_period`, and `retries` per environment without
  rebuilding the image.
- **Orchestrator visibility.** External orchestrators and proxies that read
  per-service health state from the Compose API only see the compose-level
  declaration.

**Failure modes prevented:**

- **Silent startup ordering bugs.** Without a compose-level healthcheck,
  `depends_on` with `condition: service_healthy` is a no-op — the dependent
  service starts before the dependency is ready, producing startup-time
  connection failures that are hard to diagnose because they are
  timing-dependent and vanish on restart.
- **Untunable health in production.** The image's healthcheck timings are
  baked in at build time. A service that needs a longer `start_period` under
  production load (cold cache, database migrations) requires a rebuild to
  adjust — the compose override would be ignored because no compose
  `healthcheck:` exists to override.
- **Invisible health state.** Proxies and dashboards that query the Compose
  API for per-service health see no status when only the Dockerfile
  `HEALTHCHECK` exists — the service appears permanently unmonitored even
  though the container is reporting health internally.

## Docker Compose smoke test

The image-level integration tests (entrypoint binary, import) verify the
runtime image ships intact. They do **not** verify that the compose file
which defines how the container runs — port mappings, volume mounts,
environment variables, sibling service wiring — actually brings up a working
stack. A valid image behind a broken compose file deploys a crashlooping
container just as surely as a broken image.

Every deployable component therefore runs a **Docker Compose smoke test** on
every PR, after the image build. The test uses the component's
`deploy/docker-compose.yml` — the same file central-deploy consumes — and
validates three things:

1. **Container starts.** `docker compose up --detach --wait` exits zero.
2. **Health check passes.** The container's health check (the image
   `HEALTHCHECK` or a compose-level `healthcheck`) reports healthy within a
   timeout.
3. **Core endpoint responds.** An HTTP request to the primary service's
   health endpoint (`/health`) returns 200. For non-HTTP services, replace
   with the equivalent liveness probe.

The test runs in the same PR workflow as the image build and scan — after the
build, before the scan. A failure blocks the PR, catching the regression
before merge.

**Failure mode prevented:** A compose file that references a wrong port, a
missing volume, an invalid environment variable, or a misconfigured sibling
service — any of which passes `docker compose config` validation but causes
the stack to fail at runtime. These are the exact regressions a compose
integration test catches: the compose file is structurally valid but the
stack never becomes healthy, because of a port mismatch between the service
and its health check, a volume path the image doesn't expect, or an
environment variable the service requires but the compose file omits.

A reusable workflow for this gate lives in
[robotsix-github-workflows](https://github.com/damien-robotsix/robotsix-github-workflows)
so every component calls the same compose smoke-test step, identically.

## Deploy — updates are deliberate

The deployment system (central-deploy) **pulls** the published image via the
component's `deploy/docker-compose.yml` — it never builds. Reference the GHCR
image at `:main`.

`:main` is a moving tag by design, but updates are **not** continuous:

- A component updates **only when the operator triggers Update in
  central-deploy**. No component runs its own Watchtower, registry poller, or
  auto-updater — the one sanctioned exception is central-deploy's own
  self-updater (see the [bootstrap tier](deployment-system.md)), because
  nothing sits above it to press the button.
- At every deploy/update, central-deploy **resolves the tag to its digest and
  records it** per component, so "what exactly is running" is always
  answerable and rollback targets the previously recorded digest.

Reproducibility is preserved *upstream* of the deploy boundary — SHA-pinned
first-party deps, digest-pinned bases, and the immutable `sha-<short>` tag on
every published image — while the deploy boundary itself trades
reproducibility for freshness, deliberately.

The compose shape is the [deploy contract](deploy-contract.md); the end-to-end
walkthrough is [Integrating a service](integrating-a-service.md).

## Migrating off a hand-rolled publish

If a component currently builds/pushes its own image (custom
`build-push-action`/`metadata-action`, a non-GHCR registry, per-repo login
secrets):

1. Replace the custom workflow with a caller of the shared `docker-release.yml`
   (template in the robotsix-github-workflows README).
2. Delete the hand-rolled build/push workflow and its registry secrets.
3. Repoint `deploy/docker-compose.yml` (and any image references) at
   `ghcr.io/<owner>/<repo>`.
4. Cut over deployments to the GHCR image.
