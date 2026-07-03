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

- A secret field is declared with **`pydantic.SecretStr`**: **masked on read**
  (`repr`/`str` show `**********`, never the value), and rendered in the JSON
  Schema as `{"type": "string", "format": "password", "writeOnly": true}` — so
  the deploy UI knows to mask the input and never echo it back. Secrets are
  **typed**, not guessed from an empty slot.
- Any config file written with real secrets is created **`0600` in a `0700`
  directory**, enforced in shared loader code (`dump_config`) — not per-repo,
  not docstring-only. No real credentials are committed anywhere.

### 4. What `environment:` is for

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
   across dev and deploy (`config.json`), and use the `0600` writer. Do the
   ones furthest from the standard first.
3. Commit `config/config.schema.json` (from `config_schema_json`) and add the
   CI drift check so the typed schema stays in sync with the model.
4. The deployment system consumes the schema: central-deploy's contract § 8
   reads `config/config.json` + `config/config.schema.json` and renders typed
   inputs (transition from the YAML empty-leaf heuristic is in progress).

Each component migrates in one step — there's no dual-config transition to
manage.
