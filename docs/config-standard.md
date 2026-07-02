# Config standard

> **Scope: deployable components** (and any package that reads a runtime config
> file). A library takes its configuration through its own API — constructor
> arguments or an explicit config object — not a config file; if a library reads
> environment variables, it follows the `ROBOTSIX_<NAME>_` naming convention
> below. See the [repo baseline](repo-baseline.md) and
> [component standard](component-standard.md).

**One config schema per component, defined once, that resolves the same way in
all three deploy modes.** The shared configuration library
([`robotsix-yaml-config`](https://github.com/damien-robotsix/robotsix-yaml-config),
its `[pydantic]` extra) implements it: a component defines one pydantic model and
calls `load_config`.

## The rule

### 1. One file, one schema, one locate variable

- Runtime config is a **single YAML file**, default path `config/config.yaml`
  (matching the central-deploy contract), located by **one** environment
  variable: **`ROBOTSIX_CONFIG_FILE`**. Per-service legacy names
  (`MAIL_CONFIG_PATH`, `MILL_CONFIG_FILE`) are **removed, not aliased** — the
  stack is pre-release, so a clean break is preferred over back-compat.
- The **same filename in every mode** — `config.yaml` in dev docker *and* under
  central-deploy. (No more `mail.local.yaml` in dev but `config.yaml` in
  deploy.)
- The schema is defined once, in **pydantic v2**. Pydantic is what lets the same
  model validate the file, emit the central-deploy template, and mask secrets —
  one definition, three uses. (Non-pydantic config schemas — e.g. frozen
  dataclasses — are the outlier and should migrate.)

### 2. Fixed precedence (lowest -> highest)

```
built-in defaults  <  config.yaml  <  ROBOTSIX_ env overlay  <  explicit kwargs (CLI)
```

- **File is the base; env overlays it; the CLI wins.** This keeps the file as
  the human-readable source of truth while allowing container/operator env
  overrides — without the per-repo contradictions.
- Env overlay keys are **derived mechanically from the schema path** under a
  single prefix `ROBOTSIX_<SERVICE>_`, with `__` for nesting (e.g.
  `ROBOTSIX_MAIL_IMAP__HOST`). No hand-maintained per-variable lists. Verbatim
  third-party aliases (`OPENROUTER_API_KEY`, `LANGFUSE_*`) are the one allowed
  exception, declared in a shared list.

### 3. One secret convention

- A secret field is declared with **`pydantic.SecretStr`**. It is **masked on
  read** (`repr`/`str` show `**********`, never the value).
- In the generated template a secret is an **empty leaf** (`key: ""`) — this is
  already the central-deploy contract convention, so the deploy template *is*
  the schema template. The `SECRET` sentinel is retired.
- Any config file written with real secrets is created **`0600` in a `0700`
  directory**, enforced in shared loader code — not per-repo, not
  docstring-only. No real credentials committed anywhere, even gitignored.

## Using the library

Install the extra (`uv add "robotsix-yaml-config[pydantic]"`), define plain
pydantic models, and call `load_config`:

```python
from pydantic import BaseModel, SecretStr
from robotsix_yaml_config.schema import load_config, emit_deploy_template
from robotsix_yaml_config import write_config_file


class ImapConfig(BaseModel):
    host: str = "localhost"
    port: int = 993


class MailConfig(BaseModel):
    log_level: str = "info"
    password: SecretStr = SecretStr("")
    imap: ImapConfig = ImapConfig()


# Resolution: defaults < ROBOTSIX_CONFIG_FILE yaml < ROBOTSIX_MAIL_* env < overrides
cfg = load_config(MailConfig, env_prefix="ROBOTSIX_MAIL")

# Persist merged config with 0600 perms (e.g. central-deploy writing the volume):
write_config_file("config/config.yaml", cfg.model_dump())

# Emit the central-deploy config/config.yaml template from the schema:
print(emit_deploy_template(MailConfig))
# log_level: info
# password: ''          <- secret slot
# imap:
#   host: localhost
#   port: 993
```

The library API:

| Symbol | Purpose |
|---|---|
| `schema.load_config(model_cls, *, env_prefix, ...)` | Cascade + validate into a pydantic model (fixed precedence). |
| `resolve_config_path()` | The `ROBOTSIX_CONFIG_FILE`-or-default path. |
| `write_config_file(path, data)` | Write YAML `0600` in a `0700` dir. |
| `emit_deploy_template(model_cls)` | Generate the central-deploy config template. |
| `CONFIG_FILE_ENV`, `DEFAULT_CONFIG_PATH` | The standard var name and default. |

## Why one shared model

Without a shared model, the "same config across all three deploy modes" property
holds only by accident, and even then each component tends to pick its own
schema tool, precedence order, and config-path variable. A single shared model
makes the property hold **by construction** — the same class instance is what a
`uv`-installed run, the dev container, and the deployment system all read — and
lets the config↔deploy-template drift check be a shared CI helper instead of a
per-repo script.

## Rollout (incremental, clean cutover)

The stack is pre-release with no external users, so migrations are a **clean
cutover** — no deprecated aliases or compatibility shims.

1. Ship the schema layer in the shared config library (the `[pydantic]` extra).
2. Migrate components one at a time to `robotsix_yaml_config.schema.load_config`:
   move any non-pydantic schema to a pydantic model, align the config filename
   across dev and deploy (`config.yaml`), enforce the `0600` writer, and drop
   old per-repo env-var names (no aliases). Do the ones furthest from the
   standard first.
3. Turn the config↔deploy-template drift check into a shared CI gate so drift
   can't reappear.

Each component migrates in one step — there's no dual-config transition to
manage.
