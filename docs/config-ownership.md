# Config ownership — deploy-plane vs component-owned

> **Scope: deployable components.** Every deployable component carries
> configuration that must live in exactly one of two places: the
> **deploy plane** (central-deploy UI) or the **component's own config
> surface**. This page draws the hard line between them so that an operator
> never has to guess where a setting belongs — and so that no setting lives
> in both places. See the [component standard](component-standard.md) and
> [config standard](config-standard.md) for the surrounding contracts.

## The rule

One question decides:

**Can the service apply this setting at runtime from its own config file?**

If yes, it does **NOT** belong in the deploy UI. It belongs in the
component's own `config/config.json` and MUST be exposed through the
component's standard HTTP config surface. The deploy plane is for
instantiation and wiring — nothing else.

*Failure prevented:* an operator changes a feature-flag value in the deploy
UI, redeploys the container, and waits for the restart cycle when the
component could have applied the change live; or worse, the same setting
drifts between the deploy UI and the component's own config because both
channels are open.

## Deploy-plane config — explicit allowlist

Only these categories belong in the central-deploy UI. Anything not listed
here MUST live in the component's own config surface.

| Category | What it covers | Examples |
|---|---|---|
| **Image and tag** | What container image to run | `ghcr.io/org/repo:v1.2.3` |
| **Volume mounts** | Persistent storage and credential/agent mounting | Named volumes, the managed `claude-auth` volume |
| **Ports and network** | How the container is reachable | Published ports, network attachments |
| **Secret/env injection** | Credentials for third-party images injected as environment variables | `EnvStore` slots for databases, proxies — not first-party components |
| **Restart policy** | Container restart behavior | `unless-stopped`, `on-failure` |
| **`ROBOTSIX_CONFIG_FILE`** | Where the component finds its config file | Default `config/config.json`, or a custom path |
| **Resource limits** | Memory and CPU bounds | `memory: 512m`, `cpus: 1.0` |

The deploy plane MUST NOT carry any setting that the component can apply at
runtime or that could live in `config/config.json`. Feature flags, intervals,
model selection, limits, behavior toggles, log levels, timeouts, and sibling
service URLs are all component-owned — they never appear in the deploy UI.

*Failure prevented:* a component's retry interval is set in the deploy UI;
tuning it requires a full redeploy instead of a live config update. The
setting drifts between the deploy UI (stale) and what the operator believes
is active.

## Component-owned config

Everything not in the allowlist above is component-owned. These settings
live in the component's single `config/config.json`, located by
`ROBOTSIX_CONFIG_FILE`, per the [config standard](config-standard.md). The
component's pydantic model is the schema; `config/config.schema.json` is the
typed reflection the deploy UI consumes for its initial render.

Beyond the file, every component MUST expose its config through a **standard
HTTP surface** so the operator can view and edit settings at runtime without
a redeploy. Every UI-bearing component MUST additionally provide a
**Settings/Config panel** built on that surface.

### Standard HTTP config surface

Every deployable component MUST implement these endpoints on its service
port. Headless components (no browser UI) expose the HTTP surface only and
skip the panel requirement.

#### `GET /config`

Returns the effective config — the values the component is currently using.

**Response** (200):

```json
{
  "config": {
    "log_level": "info",
    "retry_interval_s": 30,
    "model_level": "level2",
    "api_key": "**********"
  },
  "schema": { "...": "JSON Schema for the config model" },
  "version": 7
}
```

- `config` — every config field with its current effective value. Secret
  fields (declared as `SecretStr` in the pydantic model) are masked as
  `"**********"` — the actual secret value is **never** returned.
- `schema` — the JSON Schema for the config model (the same
  `config/config.schema.json` the deploy UI consumes). Clients use it to
  render typed inputs.
- `version` — a monotonic integer. Increments on every successful write.

#### `PUT /config`

Accepts a partial config update. The component MUST validate the update
against its pydantic model before applying it.

**Request** (JSON body):

```json
{
  "log_level": "debug",
  "retry_interval_s": 60
}
```

- Only the keys the operator wants to change are sent — omitted keys keep
  their current values.
- Secret keys follow merge-on-write semantics per the
  [config standard](config-standard.md) §3: omitting a secret field (or
  submitting it blank) preserves the stored value. Only an explicitly
  submitted, non-blank secret key overwrites the stored secret.

**Response** (200):

```json
{
  "config": { "...": "full effective config, secrets masked" },
  "version": 8
}
```

**Error** (422):

```json
{
  "type": "urn:robotsix:error:config-validation",
  "title": "Config validation failed",
  "detail": "retry_interval_s: value must be >= 1",
  "instance": "/config"
}
```

- Validation errors use the fleet's standard
  [HTTP error envelope](http-error-envelope.md) (`application/problem+json`).
- The component MUST NOT apply a partial update that fails validation — the
  config stays at its last valid state.

#### `GET /config/versions`

Returns a list of recent config versions with timestamps.

**Response** (200):

```json
{
  "versions": [
    {"version": 7, "timestamp": "2026-07-22T14:30:00Z", "changed_keys": ["log_level"]},
    {"version": 6, "timestamp": "2026-07-22T10:15:00Z", "changed_keys": ["retry_interval_s", "model_level"]}
  ]
}
```

- `changed_keys` lists which top-level keys changed in that version.
  Secret-key changes are recorded as `"<key_name> (secret)"` — the key name
  is logged, the value is never stored in version history.
- The component SHOULD retain at least the last 20 versions. The retention
  policy is a component decision; there is no fleet-wide minimum.

#### `POST /config/rollback`

Reverts the component's effective config to a previous version. The
component MUST validate the rolled-back config before applying it.

**Request** (JSON body):

```json
{
  "version": 6
}
```

**Response** (200):

```json
{
  "config": { "...": "full effective config after rollback, secrets masked" },
  "version": 9
}
```

- Rollback is itself a versioned write — it creates a new version (`9` in
  the example above), it does not delete the intervening versions.
- If the target version's config fails validation against the current
  pydantic model (e.g. a field was added since that version was written),
  the component MUST return `422` and MUST NOT apply the rollback.

### Standard UI affordance

Every UI-bearing component MUST provide a **Settings** or **Config** panel,
reachable from the component's primary navigation. The panel:

- **Reads from `GET /config`.** The panel renders every non-secret field
  with a typed input driven by the `schema` — a number input for an `int`,
  a checkbox for a `bool`, a dropdown for an enum, a disabled text field
  with a set/unset badge for a secret.
- **Writes through `PUT /config`.** The operator edits fields and saves;
  the panel sends only the changed keys. Validation errors from the server
  are displayed inline on the offending field.
- **Shows version history.** A "History" tab or collapsible section lists
  recent versions from `GET /config/versions` with timestamps and changed
  keys. The operator can select a previous version and trigger a rollback
  from the panel.
- **Never echoes secrets.** Secret fields are always rendered as masked
  (`**********`) with a set/unset badge. The operator cannot view existing
  secret values but can set or change them — the field follows the
  [config standard](config-standard.md) §3 merge-on-write convention
  (blank input preserves the stored value).

Headless components (no browser UI) skip the panel but MUST still implement
the full HTTP surface (`GET /config`, `PUT /config`, `GET /config/versions`,
`POST /config/rollback`).

## Secret handling

Secrets (API keys, tokens, passwords, credentials of any kind) follow the
**one-file secret convention** defined in the [config standard](config-standard.md) §3.
The config standard is the authoritative source for secret handling; this
section summarises the rules as they affect the component's HTTP surface and
the deploy-plane UI.

- **Secrets live in `config/config.json`.** Secret fields are declared with
  `pydantic.SecretStr` in the component's config model. They are stored in
  the same single JSON config file as ordinary settings — no separate
  secrets file, no `EnvStore` or env-var injection for first-party component
  secrets. (Third-party images — databases, proxies — receive secrets
  through the deploy plane's `EnvStore` slots per the
  [config standard](config-standard.md) §5; that is the only exception to
  the one-file rule.)
- **`GET /config` masks all secret fields.** The response shows
  `"**********"` for every `SecretStr` field — the actual value is never
  returned, not even to authenticated operators.
- **`PUT /config` uses merge-on-write for secrets.** Omitting a secret field
  (or submitting it blank) preserves the stored value. Only an explicitly
  submitted, non-blank secret key overwrites the stored secret. This is the
  same partial-update semantics as for all other fields, per the
  [config standard](config-standard.md) §3.
- **Version history never stores secret values.** When a secret changes, the
  version record notes that the key changed but stores nothing about the
  value.
- **The deploy-plane UI masks secrets server-side.** The central-deploy
  config form renders `writeOnly` fields as masked (password) inputs with a
  set/unset badge and never echoes stored secret values back to the browser.
  An operator can set or change a secret but cannot view an existing one.

*Failure prevented:* a secret leaks through the component's config UI
because the operator assumes the Settings panel is read-only to
non-admins — but the secret field was rendered in the JSON response. The
config standard's `SecretStr` / `writeOnly` convention (typed masking at
the schema level, redact-on-read at the surface level, merge-on-write)
prevents this without requiring a separate secret channel.

## Migration guidance

Moving a setting from the deploy UI into the component's own config surface
is a per-component, incremental migration — no big-bang, no flag day.

### Deprecation path

1. **Add the key to the component's pydantic model** with a sensible
   default. The default MUST be safe for production — the component will
   use this value until the operator explicitly sets it.

2. **Deploy.** The new key takes its default from the model. The deploy-UI
   value for the old key is still present and still applied (the component's
   startup code reads both, preferring the new config key when present).

3. **Move the value.** The operator sets the new key through the component's
   `PUT /config` endpoint (or the Settings panel). The component now uses
   the component-owned value.

4. **Remove the deploy-UI key.** Once the component-owned value is
   confirmed, the deploy-UI entry is removed. The component's startup code
   drops the fallback read of the old deploy-UI key in the same deploy.

5. **No dual-channel window.** Steps 3 and 4 SHOULD happen in the same
   deploy cycle. The operator sets the component-owned value, confirms it is
   active, then removes the deploy-UI key and redeploys. The component MUST
   NOT read the same setting from two places indefinitely — the fallback
   read exists only during the migration window.

### What not to move

Some settings are inherently deploy-plane and MUST NOT be moved:

- **Image and tag** — the component cannot change what image it runs as.
- **Volume mounts** — the component cannot remount its own filesystem.
- **Ports and network** — the component cannot rebind its own ports.
- **`ROBOTSIX_CONFIG_FILE`** — the component cannot relocate its own config
  file at runtime (it has already loaded it).
- **Resource limits** — the component cannot change its own cgroup limits.

These are the allowlist categories from the deploy-plane section above. If a
setting falls into one of those categories, it stays in the deploy UI — the
migration path does not apply.

### Per-component adoption

This standard defines the target state. Per-component adoption is filed as
follow-up tickets against each fleet repo once this standard is merged. A
component that today carries application settings in the deploy UI follows
the deprecation path above, one setting at a time, until the deploy UI
contains only allowlist categories.
