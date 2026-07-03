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
  component's `requires-python`. Use the same base in both stages.
- **Builder stage:** bring in uv (`COPY --from=ghcr.io/astral-sh/uv:<ver> /uv /uvx /bin/`)
  and install from the **frozen lockfile** (`uv sync --frozen …` with the runtime
  extras). Never install dev/test tooling into the image.
- **Runtime stage:** copy only the installed site-packages and the console
  script from the builder — no uv, no compilers, no source-only build deps.
  A component whose *runtime* genuinely needs a system dependency (e.g.
  Node.js + the `claude` CLI for the claude-sdk subscription transport, which
  spawns the CLI as a subprocess) may install it in the runtime stage — kept
  minimal, with a comment saying why it is required, and with apt caches
  cleaned in the same layer.
- **Non-root, standardized layout:** every image runs as the same non-root
  account so mounts land in the same place in every container: user **`app`**,
  **uid/gid 1001**, home **`/home/app`**, `WORKDIR /home/app`. The uid matches
  the deploy host's operator account, so host-mounted credentials (mode-`0600`
  files such as `~/.claude`) are readable without loosening their permissions.
  Consequences of the fixed layout: the deployment system's `claude-mount`
  always binds to **`/home/app/.claude`**, and the config volume/target lives
  under **`/home/app/config/`** (`config.json` per the
  [config standard](config-standard.md)) — no per-component mount-target
  configuration exists or is needed.
- **Healthcheck:** declare a `HEALTHCHECK` hitting the service's health endpoint.
- **Entrypoint:** `ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]` — see the
  [entrypoint contract](entrypoint-contract.md). The entrypoint `exec`s the app
  so signals propagate.
- **Port:** `EXPOSE` the service port.

```dockerfile
# syntax=docker/dockerfile:1
ARG BASE_DIGEST=sha256:...        # pin the python:3.14-slim digest

FROM python:3.14-slim@${BASE_DIGEST} AS builder
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --frozen --no-dev            # + any runtime extras

FROM python:3.14-slim@${BASE_DIGEST} AS production
COPY --from=builder /usr/local/lib/python3.14/site-packages/ /usr/local/lib/python3.14/site-packages/
COPY --from=builder /usr/local/bin/robotsix-<name> /usr/local/bin/robotsix-<name>
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
# Standardized layout: app/1001, /home/app — see "Non-root, standardized layout".
RUN groupadd --gid 1001 app && useradd --create-home --uid 1001 --gid 1001 app
WORKDIR /home/app
USER app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8080/health').status==200 else 1)"
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
```

## Publish — one reusable workflow (the single method)

**Do not** hand-roll `docker/build-push-action`, `docker/metadata-action`, a
registry login, or a per-repo tag scheme. Publish by calling the shared
reusable workflow, from a `release.yml` that triggers on pushes to `main` and
`v*` tags:

```yaml
name: Release image
on:
  push:
    branches: [main]
    tags: ['v*']
  workflow_dispatch:

permissions:
  contents: read
  packages: write
  id-token: write         # provenance / SBOM attestation signing
  attestations: write
  security-events: write  # Trivy SARIF upload to Code Scanning

jobs:
  publish:
    uses: damien-robotsix/robotsix-github-workflows/.github/workflows/docker-release.yml@<pinned-sha>  # main
    permissions:
      contents: read
      packages: write
      id-token: write
      attestations: write
      security-events: write
    # with:
    #   dockerfile: ./Dockerfile   # optional; this is the default
```

The reusable workflow (single input: `dockerfile`, default `./Dockerfile`) does
all of the following, identically for every component:

- **Builds and pushes to GHCR:** `ghcr.io/<owner>/<repo>`.
- **Tags:** push to `main` → `main`, `sha-<short>`, `latest`; push of a `v*` tag
  → `X.Y.Z`, `sha-<short>`.
- **Attestations:** SBOM + build provenance (`provenance: mode=max`, `sbom: true`),
  signed via OIDC.
- **Scan:** a Trivy vulnerability scan with SARIF uploaded to Code Scanning.

## Registry & tags

- **One registry: GHCR** (`ghcr.io/<owner>/<repo>`). No component image goes to
  Docker Hub or any other registry — one registry across the stack, no per-repo
  registry secret to manage.
- **Tags** are produced by the reusable workflow above: `main` (latest
  default-branch build), `sha-<short>` (immutable/reproducible), `X.Y.Z` (on
  version tags), and `latest`.

## CI-time image scan

The release workflow's Trivy gate runs only when an image is published. To
catch vulnerable base images and dependencies **before** merge, CI also builds
the image on every PR and scans it:

- Build with `docker/build-push-action` (`push: false`, `load: true`).
  **Skip the GHA layer cache for large images**: exporting a multi-GB image's
  layers to the cache API (`cache-to`) was measured at 45-55 minutes per run
  on a robotsix image whose cold build takes ~4 minutes — the cache is a net
  loss well before the gigabyte mark. Only add `cache-from`/`cache-to` after
  timing both paths on the actual image.
- Scan with `aquasecurity/trivy-action` at `severity: CRITICAL,HIGH`, SARIF
  uploaded to Code Scanning.
- **Gate policy: block on fixable findings only** — `ignore-unfixed: true` +
  `exit-code: 1`. A red gate then always means "a fixed version exists, take
  it". Base-image CVEs with **no released fix** are unactionable by a PR
  author (the package can be neither upgraded nor removed) and must not block
  merges; they stay visible through the SARIF upload and a scheduled weekly
  rescan of the published image.
- A finding that **has** a fix but genuinely doesn't apply is suppressed via a
  **curated `.trivyignore`** — every entry carries a comment saying why it
  doesn't apply. Never blanket-ignore; the file is the audit trail.
- Complement the PR gate with a **weekly scheduled rescan** of the published
  `:main` image (report-only, SARIF to Code Scanning) — it catches CVEs
  disclosed after the image was built.

## Deploy

The deployment system (central-deploy) **pulls** the published image via the
component's `deploy/docker-compose.yml` — it never builds. Reference the GHCR
image and pin `:main` (or `sha-<short>` for a reproducible deploy). The compose
shape is the [deploy contract](deploy-contract.md); the end-to-end walkthrough
is [Integrating a service](integrating-a-service.md).

## Migrating off a hand-rolled publish

If a component currently builds/pushes its own image (custom
`build-push-action`/`metadata-action`, a non-GHCR registry, per-repo login
secrets):

1. Replace the custom workflow with the `release.yml` caller above.
2. Delete the hand-rolled build/push workflow and its registry secrets.
3. Repoint `deploy/docker-compose.yml` (and any image references) at
   `ghcr.io/<owner>/<repo>`.
4. Cut over deployments to the GHCR image.
