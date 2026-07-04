# Making a repo deployable with robotsix central-deploy

> **Scope: deployable components only.** See the
> [component standard](component-standard.md).

This is the **how-to guide** for adding a service repository to the
[central-deploy](https://deploy.robotsix.net) system. It walks you from an
existing repo to a one-click deploy in the dashboard.

For the exhaustive field-by-field rules, error classification, and the
`ComponentConfig` mapping, see the authoritative reference:
[Deploy Contract](deploy-contract.md). This guide points at the relevant
contract sections (§) as it goes; when the two ever disagree, the contract
wins.

---

## Mental model (read this first)

central-deploy is **not** a builder and **not** a compose runner. It:

1. **Pulls a pre-built image** you publish (typically to GHCR). It never runs
   `docker build` — a `build:` key is a hard error (§7).
2. **Reads one file from your repo**, `deploy/docker-compose.yml`, and parses a
   restricted subset of compose into an internal `ComponentConfig`. Your repo's
   root `docker-compose.yml` is your local-dev compose and is **ignored** (§0).
3. **Manages lifecycle itself** — restart policy, networking, gateway routing,
   config injection, secrets. Many compose fields you'd normally set are
   therefore ignored on purpose (§7).

So "make my repo deployable" is really three tasks:

- **A.** Publish an image from CI.
- **B.** Write a contract-compliant `deploy/docker-compose.yml`.
- **C.** (If your app needs runtime config) add `config/config.json` +
  `config/config.schema.json` and wire them with a label.

---

## A. Publish an image from CI (prerequisite)

central-deploy pulls the `image:` ref verbatim. If CI doesn't publish it, the
deploy fails at pull time even with a perfect compose file.

- Add a `release.yml` that calls the shared `docker-release.yml` reusable
  workflow (caller template in the
  [robotsix-github-workflows](https://github.com/damien-robotsix/robotsix-github-workflows)
  README; policy in [Docker build & release](docker-standard.md)). It
  publishes `ghcr.io/damien-robotsix/<repo>:main` on every push to main —
  matching the ref in your compose.
- central-deploy **does honor** the compose `command:` (and `entrypoint:`) —
  it is parsed and applied to each container (see the
  [deploy contract](deploy-contract.md) §7). So a single image can back
  multiple services that each set their own `command:`.
- Either bake a sensible default `CMD` into the image **or** set `command:` per
  service in the deploy compose. If your image is `ENTRYPOINT`-only with no
  default `CMD`, you **must** set `command:` on each service, or the container
  starts with no subcommand.

> **Checklist:** the exact string in `image:` resolves to a real, pullable tag,
> and the container starts the service either from its default `CMD` or from the
> `command:` you set in the deploy compose.

---

## B. Write `deploy/docker-compose.yml`

Create the file at **`deploy/`**, not the repo root. First line must be the
version header exactly (§1):

```yaml
# central-deploy-contract-version: 1
```

Missing header, or a version the server doesn't recognize, is a parse error.

### Single-service skeleton (the common case)

One service is implicitly primary — no `primary` label needed (§2).

```yaml
# central-deploy-contract-version: 1
services:
  my-service:                     # service key = component id, must match ^[a-z0-9][a-z0-9-]*$
    image: ghcr.io/damien-robotsix/my-service:main
    ports:
      - "8300:8080"               # "<host>:<container>"; host port unique across all components
    volumes:
      - my-service-data:/data     # named volumes ONLY — no ./ , / , or ~ paths (§4)
volumes:
  my-service-data:                # every named volume used above must be declared here
```

> Named volumes start **empty** on first deploy; migrate data in by hand if
> needed. Backing volumes up is the **operator's responsibility** at the host
> level — the deployment system does not manage backups.

Two things deliberately absent from the skeleton:

- **No `healthcheck:`** — the image's `HEALTHCHECK` is the canonical probe
  (see [Docker build & release](docker-standard.md)) and applies
  automatically. Add a compose-level override only when the deploy context
  genuinely needs a different probe, and use only the Python stdlib (the
  image has no curl):

  ```yaml
  healthcheck:
    test: ["CMD", "python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8080/health').status==200 else 1)"]
    interval: 30s                 # Go duration strings (30s, 1m30s), converted to seconds
    timeout: 10s
    retries: 3
  ```

- **No `environment:` config or secrets** — a first-party service takes all
  settings and secrets through the config file (step C below; see the
  [config standard](config-standard.md)). `environment:` is for
  infrastructure wiring (e.g. `DOCKER_HOST` to a socket-proxy sibling) and
  for **third-party sibling images**, where an empty value (`KEY: ""`)
  declares a secret slot the operator fills in the UI and a non-empty value
  is an editable default.

### Multi-service skeleton

When you have ≥2 services, exactly one **must** carry
`robotsix.deploy.primary: "true"` (§2, §5). The primary's first port gets the
gateway route `deploy.robotsix.net/<component>/*` and its health is the
component health. Sibling container names derive as `<component>-<service-key>`.

```yaml
# central-deploy-contract-version: 1
services:
  board:                          # this key becomes the component id
    image: ghcr.io/damien-robotsix/my-app:main
    labels:
      robotsix.deploy.primary: "true"
    ports:
      - "8300:8080"
  worker:                         # sibling → container "my-app-worker" (component id is still "board"'s key — see note)
    image: ghcr.io/damien-robotsix/my-app-worker:main
    volumes:
      - my-app-data:/data
volumes:
  my-app-data:
```

> Note: the **component id** comes from the operator-supplied `name` at
> onboarding; the primary **service key** is used as the default container name.
> Keep both the primary key and every sibling key matching
> `^[a-z0-9][a-z0-9-]*$`.

### What you can set (and what you can't)

| You want to… | Do this | Contract |
|---|---|---|
| Expose a port | `ports: ["<host>:<container>"]` | §4 |
| Persist data | named volume + top-level `volumes:` entry | §4 |
| A first-party secret or setting | the config file — **not** `environment:` (see the [config standard](config-standard.md)) | §8 |
| A secret slot on a *third-party* sibling | `environment:` key with empty value (`KEY: ""`) | §4 |
| A default env value on a *third-party* sibling | `environment:` key with a value | §4 |
| A health probe | `healthcheck:` with `["CMD", …]` or `["CMD-SHELL", …]` | §4 |
| Rename a container | `container_name:` | §2 |
| **Build an image** | ❌ not allowed — publish it from CI instead | §7 (parse error) |
| **Bind-mount a host path** | ❌ never — named volumes only, no exceptions for components | §4 (parse error) |
| **Set a per-service command** | `command:` — parsed and applied at container-create time | §7 |
| **Set restart / networks / depends_on** | don't bother — silently ignored | §7 |

### Special mount labels (rare)

Both are injected at runtime by central-deploy, so do **not** list them in
`volumes:` (§5):

- `robotsix.deploy.claude-mount: "true"` — mounts the central-deploy-managed
  **`claude-auth` named volume** (rw) at **`/home/app/.claude`**, per the
  [standardized container layout](docker-standard.md). Authentication happens
  through **central-deploy's dashboard login flow**, which runs `claude login`
  into that volume — never by preparing files on the host; no host `~/.claude`
  is involved. Only for services that run Claude Code / the claude-sdk
  transport and need its session state.
- `robotsix.deploy.host-docker-sock: "true"` — mounts the host Docker socket
  (ro) into a **non-primary** service only: the **single sanctioned host
  mount**, and only on a hardened socket-proxy sibling, never on the app
  container. **Dangerous** — root-equivalent host control. (§5 has the full
  security warning.)

### Chat access label (opt-in)

If the component wants to be operable by the chat agent (`robotsix-chat`),
add the label on the primary service:

```yaml
labels:
  robotsix.deploy.chat-access: "true"
```

This hints the deployer to default the component's chat-access checkbox to
**on**. The operator checkbox in the central-deploy UI remains the actual
authorization switch. See the [chat access standard](chat-access-standard.md)
for the full contract — the component must also serve a `GET /chat-skill`
endpoint returning `text/markdown`.

---

## C. Runtime config via `config/config.json` (optional)

If your service reads a config file at runtime, don't bake it into the image and
don't ask operators to hand-edit a volume. Per the
[config standard](config-standard.md), the app loads **one JSON file** with
`robotsix_config.load_config`, and the repo commits the model's typed schema:

1. Add **`config/config.json`** at the repo root (the defaults template —
   emitted from the pydantic model) and **`config/config.schema.json`** (from
   `config_schema_json`, kept in sync by a CI drift check). The deploy UI
   renders typed inputs from the schema — numbers, booleans, enum dropdowns —
   and masks any `SecretStr` field
   (`{"type": "string", "format": "password", "writeOnly": true}`).

2. On the **primary** service in `deploy/docker-compose.yml`, add the
   `config-target` label pointing at the in-container path your app reads, and
   mount a named volume whose container path is that file's **dirname** (§5, §8).
   With the [standardized container layout](docker-standard.md) that path is
   always `/home/app/config/config.json`:

   ```yaml
   services:
     my-service:
       image: ghcr.io/damien-robotsix/my-service:main
       labels:
         robotsix.deploy.config-target: "/home/app/config/config.json"
       volumes:
         - my-service-config:/home/app/config    # dirname of config-target must match a mount
   volumes:
     my-service-config:
   ```

central-deploy merges operator edits into the template and **writes
`config.json` into that volume before the container starts**, on every config
save. Your app reads only from the mounted file. If the config template exists
but the `config-target` label is missing or its dirname doesn't match a mount,
preflight fails (§8).

### config-assist (auto-generating operator config)

If your CLI can generate a starter config (e.g. from an email address), you can
declare it so the UI offers a "generate for me" step. Two labels on the primary
service:

```yaml
labels:
  robotsix.deploy.config-assist: "detect {accounts.0.auth.username} --id {accounts.0.id} --overwrite --password {accounts.0.auth.password} --no-verify --output /home/app/config/config.json"
  robotsix.deploy.config-assist-seeds: "accounts.0.auth.username,accounts.0.auth.password"
```

- `config-assist` is a command run inside the image; `{dotted.path}`
  placeholders are filled from operator-entered seed values.
- `config-assist-seeds` lists which fields the UI collects before running it.
- Every referenced command + flag **must actually exist** in the shipped CLI —
  verify against your real entry point, or the assist step fails at deploy time.

---

## D. Onboard in the dashboard

1. In the central-deploy UI, start onboarding and point it at your repo. It
   fetches `deploy/docker-compose.yml` (and the config template if present) via
   `POST /onboard/preflight` and shows the parsed component.
2. Fill secret slots (empty-value env keys and masked config leaves).
3. Confirm optional toggles (e.g. the Claude mount) if you used those labels.
4. Deploy. central-deploy pulls the image, injects config + secrets, applies
   `restart: unless-stopped`, wires networking, and routes the primary port.

---

## E. Pre-flight checklist (avoid the common parse errors)

Run through this before onboarding — each maps to a §7 / Appendix A parse error:

- [ ] File is at `deploy/docker-compose.yml` (not repo root).
- [ ] First line is exactly `# central-deploy-contract-version: 1`.
- [ ] Every service has a non-empty `image:` that CI actually publishes.
- [ ] No `build:` key anywhere.
- [ ] ≥2 services → exactly one `robotsix.deploy.primary: "true"`.
- [ ] All service `volumes:` entries are **named** (no `.` / `/` / `~` sources).
- [ ] Every named volume used is declared in the top-level `volumes:` section.
- [ ] Any `driver:` on a volume is `local` (or omitted).
- [ ] Service keys match `^[a-z0-9][a-z0-9-]*$`.
- [ ] If the config template exists → primary has a `config-target` label whose
      dirname matches a named-volume mount.
- [ ] `host-docker-sock` (if used) is on a non-primary service only.
- [ ] Each service starts correctly — either the image has a default `CMD`, or
      you set `command:` on the service (central-deploy applies it).
- [ ] Host ports are **defaults**, not contracts: preflight checks them
      against every deployed component, auto-assigns a free port on collision,
      and files a mill ticket so the colliding default gets fixed at the
      source. Pick a sensible default anyway.
- [ ] If opting into chat access: primary service has `robotsix.deploy.chat-access: "true"`
      label, and the component serves `GET /chat-skill` returning `text/markdown`
      (see the [chat access standard](chat-access-standard.md)).

---

## F. Keeping the dev and deploy composes straight

You maintain **two** compose files with different jobs:

| File | Audience | Contains | central-deploy |
|---|---|---|---|
| `docker-compose.yml` (root) | Local dev | `build:`, host bind-mounts, dev ports, `command:` overrides | **Ignored** |
| `deploy/docker-compose.yml` | Production via central-deploy | pre-built `image:`, named volumes, secret slots, labels | **The contract** |

They will legitimately diverge (the dev compose builds locally and mounts your
source; the deploy compose pulls a published image). That's expected — just keep
the service/CLI command set consistent between them so operators aren't
surprised.

---

## Reference

- [Deploy Contract](deploy-contract.md) — authoritative spec, error table,
  `ComponentConfig` mapping, and annotated examples (Appendix A).
- [Component standard](component-standard.md) — the three deploy modes, image
  registry & tags, the two compose files.
