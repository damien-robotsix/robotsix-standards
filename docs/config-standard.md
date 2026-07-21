# Config standard

> **Scope: deployable components** (and any package that reads a runtime config
> file). A library takes its configuration through its own API — constructor
> arguments or an explicit config object — not a config file. See the
> [repo baseline](repo-baseline.md) and [component standard](component-standard.md).

**One config schema per component, defined once as a pydantic model, loaded from
one JSON file, and reflected as a typed JSON Schema the deploy UI can render.**
The shared configuration library
([`robotsix-config`](https://github.com/damien-robotsix/robotsix-config))
implements it: a component defines one pydantic model and calls `load_config`.

## The rule

### 1. One file — the single source of config values

- Runtime config is a **single JSON file**, default path `config/config.json`,
  located by **one** environment variable, **`ROBOTSIX_CONFIG_FILE`**. That
  variable only *locates* the file (for a mounted deploy) — **it never carries
  config values**.
- **The file is the only source of config values.** There is **no environment
  overlay and no CLI-merge.** Config does not come from `ROBOTSIX_*` value
  variables, from `--flag` overrides, or from any second place — only the file.
  Multiple config entry points are the main source of "why is this value what it
  is" confusion and cross-mode drift; one file removes it.
- The model's own **field defaults** fill anything the file omits (a missing
  file means "all defaults"). Defaults live in the schema, not in a separate
  layer.
- The **same filename in every mode** — `config.json` in local dev *and* under
  the deployment system.

### 2. Typed schema — defined once, reflected in the deploy UI

- The schema is a **pydantic v2 model**. From it the library emits a **JSON
  Schema** (`config_schema_json`) that encodes every field's **type**, whether
  it is **required**, its **enum** values, **defaults**, and nested structure.
- The component **commits that schema as `config/config.schema.json`**. The
  deploy UI reads it and renders **typed, validated inputs** — a number field
  for an `int`, a checkbox for a `bool`, a dropdown for an enum, a masked input
  for a secret — and **rejects wrong types before deploy** instead of writing an
  untyped string blob.
- A CI check keeps `config/config.schema.json` in sync with the model
  (regenerate and diff), so the types the UI shows can never drift from the code.

### 3. One secret convention

**Model layer — component code**

- A secret field is declared with **`pydantic.SecretStr`**: **masked on read**
  (`repr`/`str` show `**********`, never the value), and rendered in the JSON
  Schema as `{"type": "string", "format": "password", "writeOnly": true}` — so
  the deploy UI knows to mask the input and never echo it back. Secrets are
  **typed**, not guessed from an empty slot.
- Secrets live in the **same `config.json`** as ordinary settings — no
  separate secrets file, no `EnvStore` or env-var injection for component
  config. The one-file rule applies to secrets too: `ROBOTSIX_CONFIG_FILE`
  only locates the file, and the file is the only source of config values.
- Any config file written with real secrets is created **`0600` in a `0700`
  directory**, enforced in shared loader code (`dump_config`) — not per-repo,
  not docstring-only. No real credentials are committed anywhere.

**Management-surface layer — central-deploy config API + Configure UI**

These rules apply to any surface that reads, writes, or displays component
config. They are **not** library concerns (`robotsix-config` does not
implement redaction or merge); they are the deploy system's responsibility.

- **Redact on read.** Any GET endpoint, config version history, audit log,
  or UI that reads component config MUST redact every field marked
  `writeOnly` in the committed `config.schema.json`. The secret value is
  never echoed — only the key name and its set/unset status may be exposed.
- **Merge on write.** Partial-update semantics: a write that omits a secret
  field (or submits it blank / with an unchanged sentinel value) MUST
  preserve the stored value. Only an explicitly submitted, non-blank,
  non-sentinel secret key overwrites the stored secret. Secret values MUST
  NOT be stored in config version history — history records that a secret
  key changed (e.g. "secret `password` updated"), never its content.
- **UI rendering.** Forms are generated from the committed
  `config.schema.json`. Every `writeOnly` field renders as a blank masked
  (password) input with a set/unset badge — the badge is the only
  indication of whether a value exists, since the value itself is never
  echoed. The operator types a new value to set or change the secret;
  leaving it blank preserves the existing value.

### 4. Advanced settings flag

A per-setting **`advanced`** annotation (boolean, default `false`) lets the
deploy UI hide rarely-changed or expert-only settings behind a "Show advanced
settings" toggle — off by default. It is **purely presentational**: marking a
field `advanced: true` does not change validation, serialization, or runtime
behavior in any way. The application never sees the flag; only the deploy UI
consumes it from the committed `config/config.schema.json`.

**Model layer — component code**

Annotate a field as advanced with pydantic's `Field(json_schema_extra=…)`:

```python
from pydantic import BaseModel, Field

class MailConfig(BaseModel):
    log_level: LogLevel = LogLevel.info
    connection_pool_size: int = Field(
        default=10,
        json_schema_extra={"advanced": True},
    )
```

The library emits this into the JSON Schema as a top-level property on the
field's schema object:

```json
{
  "properties": {
    "log_level": {"type": "string", "enum": ["info", "debug"], "default": "info"},
    "connection_pool_size": {
      "type": "integer",
      "default": 10,
      "advanced": true
    }
  }
}
```

**Deploy-UI layer — central-deploy Configure screen**

- **Hidden by default.** Every field with `"advanced": true` is hidden when the
  "Show advanced settings" toggle is off. Fields without the flag (or with
  `"advanced": false`) are always visible — schemas without the flag behave
  exactly as today (all settings visible).
- **Fully editable when revealed.** Toggling "Show advanced settings" on reveals
  the advanced fields inline with their typed inputs (number, bool, dropdown,
  etc.). There is no separate "advanced mode" form — the toggle only controls
  visibility; once visible, advanced fields are first-class settings.
- **Backward compatible.** Omitting `advanced` from a field's schema is
  equivalent to `"advanced": false`. Existing schemas require no changes and
  render identically to before.

**Classifying settings (guidance for fleet repos)**

These heuristics help decide which fields to mark `advanced: true`:

- **Rarely changed.** A setting the operator sets once at onboarding and never
  touches again (e.g. a worker thread count, a database pool size) is a good
  candidate.
- **Expert-only.** Settings whose meaning requires deep knowledge of the
  component's internals (e.g. a GC tuning knob, a buffer size in bytes).
- **Safe default exists.** If the default is sensible for nearly all deployments
  and changing it is purely an optimisation, mark it advanced. If the operator
  *must* set it for the component to work, keep it visible.
- **Conversely, keep visible:** anything the operator must set for the component
  to function (e.g. a hostname, an external URL), anything they will
  deliberately change day-to-day (e.g. a log level), and anything that is a
  security boundary (e.g. a secret field — `SecretStr` is already masked, and
  hiding it behind a second toggle risks the operator missing it).

### 5. What `environment:` is for

The one-file rule means `environment:` in a compose file is **never** a config
channel for first-party code. Three cases:

- **Allowed — infrastructure wiring.** Variables the *deploy topology* needs,
  not app settings: `ROBOTSIX_CONFIG_FILE` locating the file, `DOCKER_HOST`
  pointing a service at its socket-proxy sibling. Rule of thumb: if the value
  only makes sense inside a compose file, it's wiring.
- **Allowed — third-party images.** A sibling you don't control (a database,
  a proxy) takes its config and secrets however it takes them; the deploy
  contract's env secret slots (`KEY: ""`) exist for exactly this.
- **Forbidden — first-party app config and secrets.** Anything the
  component's own code reads as a setting or credential lives in the config
  file (`SecretStr` for secrets, masked in the deploy UI via the typed
  schema). No `API_KEY: ""`-style slots on first-party services — two open
  channels for the same value is precisely the "why is this value what it is"
  ambiguity the one-file rule exists to kill.

### 6. Calling another service: a `<name>_url` config field

A component that calls another service declares its dependency's base URL as
an **ordinary config field** — `<name>_url`, typed in the model, with a
sensible localhost default for dev — and the operator sets the real value in
the deploy UI like any other field. Credentials for that call are `SecretStr`
fields next to the URL. Explicitly **not** part of the stack, added
deliberately only if ever needed: service discovery, a registry,
central-deploy-injected addresses, DNS-name conventions. Plain config fields
are the whole mechanism.

## Using the library

Install it (`uv add robotsix-config`, SHA-pinned via `[tool.uv.sources]` per
the [repo baseline](repo-baseline.md)), define plain pydantic models, and call
`load_config`:

```python
from enum import StrEnum

from pydantic import BaseModel, SecretStr
from robotsix_config import config_schema_json, dump_config, load_config


class LogLevel(StrEnum):
    info = "info"
    debug = "debug"


class ImapConfig(BaseModel):
    host: str = "localhost"
    port: int = 993


class MailConfig(BaseModel):
    log_level: LogLevel = LogLevel.info
    password: SecretStr = SecretStr("")
    imap: ImapConfig = ImapConfig()


# The one file (ROBOTSIX_CONFIG_FILE or config/config.json) is the only source
# of values; the model's defaults fill the gaps. No env overlay, no CLI merge.
cfg = load_config(MailConfig)

# Emit the typed schema the deploy UI renders (commit as config/config.schema.json):
schema_json = config_schema_json(MailConfig)

# Persist config with 0600 perms (e.g. the deploy system writing the volume):
dump_config(cfg)
```

The library API:

| Symbol | Purpose |
|---|---|
| `load_config(model_cls, path=None)` | Load **the one** JSON config file and validate into the model (no env, no CLI-merge). |
| `config_schema(model_cls)` | The model's typed **JSON Schema** for the deploy UI (dict). |
| `config_schema_json(model_cls)` | The same, serialized — write to `config/config.schema.json`. |
| `dump_config(model, path=None)` | Write the model to the JSON file, `0600` in a `0700` dir (secrets in cleartext, for the app to read back). |
| `resolve_config_path()` | The `ROBOTSIX_CONFIG_FILE`-or-default path (locate only). |
| `CONFIG_FILE_ENV`, `DEFAULT_CONFIG_PATH` | The standard var name and default path (`config/config.json`). |
| `ConfigError`, `MissingConfigError`, `InvalidConfigError` | Error types (bad JSON, failed validation). |

## Why one file + a typed schema

Two failure modes the old setup allowed, and how this closes them:

- **Value drift across sources.** When config can come from a file *and* env
  *and* CLI, "why is this value what it is" depends on the union of all three,
  and the answer differs between dev, a `uv` run, and the deploy system. **One
  file** makes the file the whole answer, identically in every mode.
- **Untyped deploy config.** When the deploy UI treats config as free-text
  strings, an operator can put `"yes"` in an `int` field or mistype an enum, and
  it only fails at container start. **The typed schema** lets the UI validate
  before deploy and render the right control per type — and because the schema
  is generated from the same model the app loads, the UI and the runtime can
  never disagree about the shape.

## Rollout (incremental, clean cutover)

The stack is pre-release with no external users, so migrations are a **clean
cutover** — no deprecated aliases or compatibility shims.

1. ~~Ship the schema layer in the shared config library~~ — done: the library
   is `robotsix-config` (renamed from `robotsix-yaml-config` and rewritten:
   pydantic + JSON, no YAML, no env overlay).
2. Migrate components one at a time to `robotsix_config.load_config`: move any
   non-pydantic schema to a pydantic model, load from the one file (drop every
   `ROBOTSIX_*` value variable, CLI-override path, *and* first-party env
   secret slot in the deploy compose — no aliases), align the config filename
   across dev and deploy (`config.json`), and use the `0600` writer.
   **The old YAML path is deleted in the same change** — no backward
   compatibility, no dual-config window; any data/format migration is handled
   by hand, case by case. Do the ones furthest from the standard first.
3. Commit `config/config.schema.json` (from `config_schema_json`) and add the
   CI drift check so the typed schema stays in sync with the model.
4. The deployment system consumes the schema: central-deploy's contract § 8
   reads `config/config.json` + `config/config.schema.json` and renders typed
   inputs; the old YAML empty-leaf heuristic is removed outright, not aliased.

Each component migrates in one step — there's no dual-config transition to
manage.

### Advanced-flag rollout

The `advanced` flag is backward-compatible by design — schemas without it
behave exactly as before (all fields visible). Fleet repos can adopt it
incrementally:

1. The flag is defined here and available in the library's JSON Schema
   output immediately (any `Field(json_schema_extra={"advanced": True})` on a
   pydantic model is passed through to `config.schema.json`).
2. **central-deploy** implements the toggle in its Configure screen (separate
   ticket). Until that toggle ships, `"advanced": true` annotations in
   schemas are harmless — they are an unrecognised JSON Schema keyword that
   existing deploy-UI versions ignore.
3. **Fleet repos** classify their settings per the heuristics in §4. Each
   repo adds `json_schema_extra={"advanced": True}` to the relevant fields,
   regenerates `config/config.schema.json`, and the CI drift check confirms
   the schema is in sync. This is per-repo follow-up work — the flag is
   optional and repos can adopt it on their own schedule.
4. There is no data migration, no breaking change, and no flag day. An
   unmarked field is visible; a marked field is hidden behind the toggle
   once central-deploy supports it; nothing else changes.
